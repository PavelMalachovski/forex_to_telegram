import logging
import asyncio
from datetime import datetime, date, time
from typing import List, Optional
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger
import pytz

from .database_service import ForexNewsService
from .scraper import MessageFormatter
from .utils import send_long_message

logger = logging.getLogger(__name__)


class DailyDigestScheduler:
    """Manages daily digest scheduling and sending with timezone support."""

    def __init__(self, db_service: ForexNewsService, bot, config):
        self.db_service = db_service
        self.bot = bot
        self.config = config
        self.scheduler = BackgroundScheduler()
        self._setup_scheduler()

    def _setup_scheduler(self):
        """Setup the scheduler with timezone-aware digest jobs."""
        try:
            # Get all users with their timezone and digest time preferences
            users_with_times = self._get_users_with_digest_times()

            # Group users by timezone and digest time
            timezone_digest_groups = self._group_users_by_timezone_and_time(users_with_times)

            # Add jobs for each unique timezone and digest time combination
            for (user_timezone, digest_time), users in timezone_digest_groups.items():
                self._add_timezone_digest_job(user_timezone, digest_time, users)

            self.scheduler.start()
            logger.info(f"Daily digest scheduler started with timezone-aware scheduling")

        except Exception as e:
            logger.error(f"Error setting up daily digest scheduler: {e}")

        # Also add a channel digest at 07:00 if a channel/chat ID is configured
        try:
            if getattr(self.config, 'telegram_chat_id', None):
                from apscheduler.triggers.cron import CronTrigger
                self.scheduler.add_job(
                    func=self._send_channel_digest,
                    trigger=CronTrigger(
                        hour=7,
                        minute=0,
                        timezone=getattr(self.config, 'timezone', 'Europe/Prague')
                    ),
                    id='channel_daily_digest_07_00',
                    name='Channel Daily Digest at 07:00',
                    replace_existing=True
                )
                logger.info("Added channel daily digest at 07:00")
            else:
                logger.info("telegram_chat_id not configured; skipping channel daily digest job")
        except Exception as e:
            logger.error(f"Error adding channel daily digest job: {e}")

    def _get_users_with_digest_times(self) -> List[dict]:
        """Get all users with their digest times and timezones."""
        try:
            users = self.db_service.get_all_users()
            users_with_times = []

            for user in users:
                if user.digest_time:
                    user_timezone = getattr(user, 'timezone', 'Europe/Prague')  # Default timezone
                    users_with_times.append({
                        'user': user,
                        'digest_time': user.digest_time,
                        'timezone': user_timezone
                    })

            return users_with_times

        except Exception as e:
            logger.error(f"Error getting users with digest times: {e}")
            return []

    def _group_users_by_timezone_and_time(self, users_with_times: List[dict]) -> dict:
        """Group users by timezone and digest time."""
        groups = {}

        for user_data in users_with_times:
            timezone = user_data['timezone']
            digest_time = user_data['digest_time']
            key = (timezone, digest_time)

            if key not in groups:
                groups[key] = []
            groups[key].append(user_data['user'])

        return groups

    def _add_timezone_digest_job(self, user_timezone: str, digest_time: time, users: List):
        """Add a digest job for a specific timezone and time."""
        try:
            # Create a unique job ID that includes timezone
            timezone_safe = user_timezone.replace('/', '_').replace('-', '_')
            job_id = f"daily_digest_{timezone_safe}_{digest_time.hour:02d}_{digest_time.minute:02d}"
            job_name = f"Daily Digest at {digest_time.strftime('%H:%M')} ({user_timezone})"

            # Add the job with timezone-aware trigger
            self.scheduler.add_job(
                func=self._send_timezone_digest,
                trigger=CronTrigger(
                    hour=digest_time.hour,
                    minute=digest_time.minute,
                    timezone=user_timezone
                ),
                id=job_id,
                name=job_name,
                args=[user_timezone, digest_time, users],  # Pass timezone and users
                replace_existing=True
            )

            logger.info(f"Added timezone-aware digest job for {digest_time.strftime('%H:%M')} in {user_timezone}")

        except Exception as e:
            logger.error(f"Error adding timezone digest job for {user_timezone} at {digest_time}: {e}")

    def refresh_digest_jobs(self):
        """Refresh digest jobs based on current user preferences with timezone support."""
        try:
            # Remove existing digest jobs
            existing_jobs = [job for job in self.scheduler.get_jobs() if job.id.startswith("daily_digest_")]
            for job in existing_jobs:
                self.scheduler.remove_job(job.id)

            # Get updated user preferences
            users_with_times = self._get_users_with_digest_times()
            timezone_digest_groups = self._group_users_by_timezone_and_time(users_with_times)

            # Add new jobs based on current user preferences
            for (user_timezone, digest_time), users in timezone_digest_groups.items():
                self._add_timezone_digest_job(user_timezone, digest_time, users)

            logger.info(f"Refreshed timezone-aware digest jobs")

        except Exception as e:
            logger.error(f"Error refreshing digest jobs: {e}")

    def _send_timezone_digest(self, user_timezone: str, digest_time: time, users: List):
        """Send daily digest to users in a specific timezone at the specified time."""
        try:
            if not users:
                logger.info(f"No users scheduled for digest at {digest_time} in {user_timezone}")
                return

            logger.info(f"Sending daily digest to {len(users)} users at {digest_time} in {user_timezone}")

            # Send digest to each user in this timezone/time group
            for user in users:
                try:
                    self._send_user_digest(user, user_timezone)
                except Exception as e:
                    logger.error(f"Error sending digest to user {user.telegram_id}: {e}")

        except Exception as e:
            logger.error(f"Error in timezone digest job for {user_timezone}: {e}")

    def _send_daily_digest(self, digest_time: time = None):
        """Legacy method for backward compatibility."""
        try:
            if digest_time is None:
                digest_time = datetime.now().time()

            users = self.db_service.get_users_for_digest(digest_time)

            if not users:
                logger.info(f"No users scheduled for digest at {digest_time}")
                return

            logger.info(f"Sending daily digest to {len(users)} users at {digest_time}")

            # Send digest to each user
            for user in users:
                try:
                    user_timezone = getattr(user, 'timezone', 'Europe/Prague')
                    self._send_user_digest(user, user_timezone)
                except Exception as e:
                    logger.error(f"Error sending digest to user {user.telegram_id}: {e}")

        except Exception as e:
            logger.error(f"Error in daily digest job: {e}")

    def _send_user_digest(self, user, user_timezone: str = "Europe/Prague"):
        """Send personalized digest to a specific user with timezone support."""
        try:
            # Get user preferences
            currencies = user.get_currencies_list()
            impact_levels = user.get_impact_levels_list()
            analysis_required = user.analysis_required
            digest_time = user.digest_time

            # Get today's news
            today = date.today()
            all_news = self.db_service.get_news_for_date(today, 'all')

            if not all_news:
                # No news available, send a message
                message = f"📅 <b>Daily Digest for {today.strftime('%d.%m.%Y')}</b>\n"
                message += f"🕐 <i>Your time: {digest_time.strftime('%H:%M')} ({user_timezone})</i>\n\n"
                message += "✅ No forex news available for today.\n"
                message += "Check back later for updates!"

                self.bot.send_message(
                    user.telegram_id,
                    message,
                    parse_mode="HTML"
                )
                return

            # Filter news based on user preferences
            filtered_news = []

            for news_item in all_news:
                # Check impact level
                if news_item.get('impact') not in impact_levels:
                    continue

                # Check currency (if user has specific preferences)
                if currencies and news_item.get('currency') not in currencies:
                    continue

                filtered_news.append(news_item)

            if not filtered_news:
                # No news matching user preferences
                currency_msg = f" for currencies: {', '.join(currencies)}" if currencies else ""
                impact_msg = f" with impact: {', '.join(impact_levels)}"

                message = f"📅 <b>Daily Digest for {today.strftime('%d.%m.%Y')}</b>\n"
                message += f"🕐 <i>Your time: {digest_time.strftime('%H:%M')} ({user_timezone})</i>\n\n"
                message += f"✅ No news found{currency_msg}{impact_msg}.\n"
                message += "Try adjusting your preferences with /settings"

                self.bot.send_message(
                    user.telegram_id,
                    message,
                    parse_mode="HTML"
                )
                return

            # Format and send the digest
            target_date = datetime.combine(today, datetime.min.time())
            message = MessageFormatter.format_news_message(
                filtered_news,
                target_date,
                "all",
                analysis_required,
                currencies if currencies else None
            )

            # Add digest header with timezone info
            digest_header = f"📅 <b>Daily Digest for {today.strftime('%d.%m.%Y')}</b>\n"
            digest_header += f"🕐 <i>Your time: {digest_time.strftime('%H:%M')} ({user_timezone})</i>\n\n"
            message = digest_header + message

            # Send the message
            send_long_message(
                self.bot,
                user.telegram_id,
                message,
                parse_mode="HTML"
            )

            logger.info(f"Sent daily digest to user {user.telegram_id} with {len(filtered_news)} news items")

        except Exception as e:
            logger.error(f"Error sending user digest to {user.telegram_id}: {e}")

    def send_test_digest(self, user_id: int) -> bool:
        """Send a test digest to a specific user (for testing purposes)."""
        try:
            user = self.db_service.get_or_create_user(user_id)
            user_timezone = getattr(user, 'timezone', 'Europe/Prague')
            self._send_user_digest(user, user_timezone)
            return True
        except Exception as e:
            logger.error(f"Error sending test digest to user {user_id}: {e}")
            return False

    def _send_channel_digest(self):
        """Send a high+medium impact daily digest to the configured channel at 07:00 (local)."""
        try:
            chat_id = getattr(self.config, 'telegram_chat_id', None)
            if not chat_id:
                return

            today = date.today()
            # Fetch all for today, then filter to high+medium
            all_news = self.db_service.get_news_for_date(today, 'all')
            filtered = [n for n in all_news if n.get('impact') in ('high', 'medium')]

            # If nothing in DB yet, inform briefly
            if not filtered:
                message = (
                    f"📅 <b>Daily Digest (High+Medium) for {today.strftime('%d.%m.%Y')}</b>\n\n"
                    f"No high or medium impact events found for today."
                )
                self.bot.send_message(chat_id, message, parse_mode="HTML")
                return

            target_date = datetime.combine(today, datetime.min.time())
            # Format digest (no currency filter; include all high-impact)
            message = MessageFormatter.format_news_message(
                filtered,
                target_date,
                'all',
                analysis_required=False,
                currencies=None
            )

            header = (
                f"📅 <b>Daily Digest (High+Medium) for {today.strftime('%d.%m.%Y')}</b>\n"
                f"🕐 <i>Times shown in {getattr(self.config, 'timezone', 'Europe/Prague')}</i>\n\n"
            )
            send_long_message(self.bot, chat_id, header + message, parse_mode="HTML")
            logger.info("Sent channel daily high-impact digest")

        except Exception as e:
            logger.error(f"Error sending channel daily digest: {e}")

    def stop_scheduler(self):
        """Stop the scheduler."""
        try:
            if self.scheduler.running:
                self.scheduler.shutdown()
                logger.info("Daily digest scheduler stopped")
        except Exception as e:
            logger.error(f"Error stopping scheduler: {e}")

    def get_scheduler_status(self) -> dict:
        """Get scheduler status information."""
        try:
            jobs = []
            for job in self.scheduler.get_jobs():
                # Convert timezone object to string to make it JSON serializable
                timezone_str = 'UTC'
                if hasattr(job.trigger, 'timezone'):
                    timezone_obj = getattr(job.trigger, 'timezone')
                    if timezone_obj:
                        timezone_str = str(timezone_obj)

                jobs.append({
                    'id': job.id,
                    'name': job.name,
                    'next_run': job.next_run_time.isoformat() if job.next_run_time else None,
                    'timezone': timezone_str
                })

            return {
                'running': self.scheduler.running,
                'jobs': jobs
            }
        except Exception as e:
            logger.error(f"Error getting scheduler status: {e}")
            return {'running': False, 'jobs': []}
