import logging
import asyncio
from datetime import datetime, date, time
from typing import List, Optional
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger

from .database_service import ForexNewsService
from .scraper import MessageFormatter
from .utils import send_long_message

logger = logging.getLogger(__name__)


class DailyDigestScheduler:
    """Manages daily digest scheduling and sending."""

    def __init__(self, db_service: ForexNewsService, bot, config):
        self.db_service = db_service
        self.bot = bot
        self.config = config
        self.scheduler = BackgroundScheduler()
        self._setup_scheduler()

    def _setup_scheduler(self):
        """Setup the scheduler with dynamic digest jobs."""
        try:
            # Get all unique digest times from users
            unique_times = self._get_unique_digest_times()

            # Add jobs for each unique digest time
            for digest_time in unique_times:
                self._add_digest_job(digest_time)

            self.scheduler.start()
            logger.info(f"Daily digest scheduler started with {len(unique_times)} unique times")

        except Exception as e:
            logger.error(f"Error setting up daily digest scheduler: {e}")

    def _get_unique_digest_times(self) -> List[time]:
        """Get all unique digest times from users."""
        try:
            users = self.db_service.get_all_users()
            unique_times = set()

            for user in users:
                if user.digest_time:
                    unique_times.add(user.digest_time)

            # If no users have digest times, add default
            if not unique_times:
                unique_times.add(time(8, 0))

            return list(unique_times)

        except Exception as e:
            logger.error(f"Error getting unique digest times: {e}")
            return [time(8, 0)]  # Default fallback

    def _add_digest_job(self, digest_time: time):
        """Add a digest job for a specific time."""
        try:
            job_id = f"daily_digest_{digest_time.hour:02d}_{digest_time.minute:02d}"
            job_name = f"Daily Digest at {digest_time.strftime('%H:%M')}"

            self.scheduler.add_job(
                func=self._send_daily_digest,
                trigger=CronTrigger(hour=digest_time.hour, minute=digest_time.minute),
                id=job_id,
                name=job_name,
                args=[digest_time],  # Pass the specific time
                replace_existing=True
            )

            logger.info(f"Added digest job for {digest_time.strftime('%H:%M')}")

        except Exception as e:
            logger.error(f"Error adding digest job for {digest_time}: {e}")

    def refresh_digest_jobs(self):
        """Refresh digest jobs based on current user preferences."""
        try:
            # Remove existing digest jobs
            existing_jobs = [job for job in self.scheduler.get_jobs() if job.id.startswith("daily_digest_")]
            for job in existing_jobs:
                self.scheduler.remove_job(job.id)

            # Add new jobs based on current user preferences
            unique_times = self._get_unique_digest_times()
            for digest_time in unique_times:
                self._add_digest_job(digest_time)

            logger.info(f"Refreshed digest jobs with {len(unique_times)} unique times")

        except Exception as e:
            logger.error(f"Error refreshing digest jobs: {e}")

    def _send_daily_digest(self, digest_time: time = None):
        """Send daily digest to all users at the specified time."""
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
                    self._send_user_digest(user)
                except Exception as e:
                    logger.error(f"Error sending digest to user {user.telegram_id}: {e}")

        except Exception as e:
            logger.error(f"Error in daily digest job: {e}")

    def _send_user_digest(self, user):
        """Send personalized digest to a specific user."""
        try:
            # Get user preferences
            currencies = user.get_currencies_list()
            impact_levels = user.get_impact_levels_list()
            analysis_required = user.analysis_required

            # Get today's news
            today = date.today()
            all_news = self.db_service.get_news_for_date(today, 'all')

            if not all_news:
                # No news available, send a message
                message = f"📅 <b>Daily Digest for {today.strftime('%d.%m.%Y')}</b>\n\n"
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

                message = f"📅 <b>Daily Digest for {today.strftime('%d.%m.%Y')}</b>\n\n"
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

            # Add digest header
            digest_header = f"📅 <b>Daily Digest for {today.strftime('%d.%m.%Y')}</b>\n\n"
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
            self._send_user_digest(user)
            return True
        except Exception as e:
            logger.error(f"Error sending test digest to user {user_id}: {e}")
            return False

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
                jobs.append({
                    'id': job.id,
                    'name': job.name,
                    'next_run': job.next_run_time.isoformat() if job.next_run_time else None
                })

            return {
                'running': self.scheduler.running,
                'jobs': jobs
            }
        except Exception as e:
            logger.error(f"Error getting scheduler status: {e}")
            return {'running': False, 'jobs': []}
