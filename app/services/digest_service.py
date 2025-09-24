"""Daily digest scheduler with timezone-aware scheduling and comprehensive functionality."""

import logging
import asyncio
from datetime import datetime, date, time
from typing import List, Optional, Dict, Any
import pytz
import structlog

from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger
from apscheduler.jobstores.sqlalchemy import SQLAlchemyJobStore

from app.core.config import settings
from app.core.exceptions import DigestError
from app.services.database_service import DatabaseService
from app.services.scraping_service import ScrapingService
from app.services.notification_service import NotificationService
from app.utils.telegram_utils import send_long_message

logger = structlog.get_logger(__name__)


class DailyDigestScheduler:
    """Manages daily digest scheduling and sending with timezone support."""

    def __init__(self, db_service: DatabaseService, bot_manager, config):
        self.db_service = db_service
        self.bot_manager = bot_manager
        self.config = config
        self.scraping_service = ScrapingService()
        self.notification_service = NotificationService()

        # Setup scheduler with SQLAlchemy job store
        jobstores = {
            'default': SQLAlchemyJobStore(url=getattr(settings.database, 'url', 'sqlite:///digest_jobs.sqlite'))
        }

        self.scheduler = BackgroundScheduler(
            jobstores=jobstores,
            timezone=pytz.UTC  # Default timezone
        )

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
            logger.info("Daily digest scheduler started with timezone-aware scheduling")

        except Exception as e:
            logger.error("Error setting up daily digest scheduler", error=str(e))

        # Also add a channel digest at 07:00 if a channel/chat ID is configured
        try:
            if getattr(self.config, 'telegram_chat_id', None):
                self.scheduler.add_job(
                    func=self._send_channel_digest,
                    trigger=CronTrigger(hour=7, minute=0, timezone=pytz.timezone('Europe/Prague')),
                    id='channel_digest',
                    name='Channel Daily Digest',
                    replace_existing=True
                )
                logger.info("Channel digest job added")
        except Exception as e:
            logger.error("Error adding channel digest job", error=str(e))

    def _get_users_with_digest_times(self) -> List[Dict[str, Any]]:
        """Get all users with their digest time preferences."""
        try:
            # This would typically query the database for users with digest preferences
            # For now, we'll return a mock structure
            users = []

            # Get users from database service
            # This is a simplified version - in reality, you'd query the database
            # for users who have digest_time and timezone preferences set

            return users

        except Exception as e:
            logger.error("Failed to get users with digest times", error=str(e))
            return []

    def _group_users_by_timezone_and_time(self, users: List[Dict[str, Any]]) -> Dict[tuple, List[Dict[str, Any]]]:
        """Group users by their timezone and digest time."""
        groups = {}

        for user in users:
            timezone = user.get('timezone', 'Europe/Prague')
            digest_time = user.get('digest_time', time(8, 0))
            key = (timezone, digest_time)

            if key not in groups:
                groups[key] = []
            groups[key].append(user)

        return groups

    def _add_timezone_digest_job(self, user_timezone: str, digest_time: time, users: List[Dict[str, Any]]):
        """Add a digest job for a specific timezone and time."""
        try:
            # Convert timezone string to pytz timezone object
            tz = pytz.timezone(user_timezone)

            # Create job ID based on timezone and time
            job_id = f"digest_{user_timezone}_{digest_time.hour:02d}_{digest_time.minute:02d}"

            # Add the job
            self.scheduler.add_job(
                func=self._send_digest_to_users,
                trigger=CronTrigger(
                    hour=digest_time.hour,
                    minute=digest_time.minute,
                    timezone=tz
                ),
                args=[users, user_timezone],
                id=job_id,
                name=f'Daily Digest for {user_timezone} at {digest_time.strftime("%H:%M")}',
                replace_existing=True
            )

            logger.info("Added digest job",
                       timezone=user_timezone,
                       time=digest_time.strftime("%H:%M"),
                       users_count=len(users))

        except Exception as e:
            logger.error("Failed to add timezone digest job",
                        timezone=user_timezone,
                        time=digest_time.strftime("%H:%M"),
                        error=str(e))

    async def _send_digest_to_users(self, users: List[Dict[str, Any]], user_timezone: str):
        """Send daily digest to a group of users."""
        try:
            logger.info("Starting daily digest", timezone=user_timezone, users_count=len(users))

            # Get today's date in the user's timezone
            tz = pytz.timezone(user_timezone)
            today = datetime.now(tz).date()

            # Fetch news for today
            news_items = await self._fetch_today_news(today)

            if not news_items:
                logger.info("No news items found for digest", date=today)
                return

            # Send digest to each user
            for user in users:
                try:
                    user_id = user.get('user_id')
                    if not user_id:
                        continue

                    # Get user preferences
                    user_preferences = await self._get_user_preferences(user_id)

                    # Send digest
                    success = await self.notification_service.send_daily_digest(
                        user_id=user_id,
                        news_items=news_items,
                        target_date=datetime.combine(today, time()),
                        user_preferences=user_preferences
                    )

                    if success:
                        logger.info("Daily digest sent successfully", user_id=user_id)
                    else:
                        logger.warning("Failed to send daily digest", user_id=user_id)

                except Exception as e:
                    logger.error("Error sending digest to user", user_id=user.get('user_id'), error=str(e))
                    continue

            logger.info("Daily digest completed", timezone=user_timezone, users_processed=len(users))

        except Exception as e:
            logger.error("Failed to send digest to users", timezone=user_timezone, error=str(e))

    async def _send_channel_digest(self):
        """Send daily digest to the configured channel."""
        try:
            chat_id = getattr(self.config, 'telegram_chat_id', None)
            if not chat_id:
                logger.warning("No channel ID configured for channel digest")
                return

            logger.info("Starting channel daily digest", chat_id=chat_id)

            # Get today's date
            today = datetime.now().date()

            # Fetch news for today
            news_items = await self._fetch_today_news(today)

            if not news_items:
                logger.info("No news items found for channel digest", date=today)
                return

            # Format and send channel digest
            message = await self._format_channel_digest(news_items, today)

            success = await send_long_message(self.bot_manager, chat_id, message)

            if success:
                logger.info("Channel digest sent successfully", chat_id=chat_id)
            else:
                logger.error("Failed to send channel digest", chat_id=chat_id)

        except Exception as e:
            logger.error("Failed to send channel digest", error=str(e))

    async def _fetch_today_news(self, target_date: date) -> List[Dict[str, Any]]:
        """Fetch news items for the target date."""
        try:
            # Convert date to datetime for scraping service
            target_datetime = datetime.combine(target_date, time())

            # Use scraping service to get news
            news_items = await self.scraping_service.scrape_news(target_datetime)

            logger.info("Fetched news items", date=target_date, count=len(news_items))
            return news_items

        except Exception as e:
            logger.error("Failed to fetch today's news", date=target_date, error=str(e))
            return []

    async def _get_user_preferences(self, user_id: int) -> Dict[str, Any]:
        """Get user preferences for digest filtering."""
        try:
            user = await self.db_service.get_or_create_user(user_id)

            return {
                'preferred_currencies': user.get_currencies_list() if hasattr(user, 'get_currencies_list') else [],
                'impact_levels': user.get_impact_levels_list() if hasattr(user, 'get_impact_levels_list') else ['high', 'medium', 'low'],
                'analysis_required': getattr(user, 'analysis_required', True),
                'timezone': getattr(user, 'timezone', 'Europe/Prague')
            }

        except Exception as e:
            logger.error("Failed to get user preferences", user_id=user_id, error=str(e))
            return {}

    async def _format_channel_digest(self, news_items: List[Dict[str, Any]], target_date: date) -> str:
        """Format digest message for channel."""
        try:
            date_str = target_date.strftime("%d.%m.%Y")

            if not news_items:
                return f"📅 Daily Digest for {date_str}\n\n✅ No news events today."

            # Group by currency
            grouped = {}
            for item in news_items:
                currency = item.get('currency', 'Unknown')
                if currency not in grouped:
                    grouped[currency] = []
                grouped[currency].append(item)

            # Format message
            message_parts = [f"📅 Daily Digest for {date_str}\n"]

            for currency, items in sorted(grouped.items()):
                message_parts.append(f"\n💎 {currency}")

                for item in items:
                    impact_emoji = {
                        'high': '🔴',
                        'medium': '🟠',
                        'low': '🟡',
                        'tentative': '⏳',
                        'none': '⚪️',
                        'unknown': '❓',
                    }.get(item.get('impact', 'unknown'), '❓')

                    event = str(item.get('event', 'N/A')).replace('\\', '')
                    time_str = item.get('time', 'N/A')

                    message_parts.append(f"⏰ {time_str} {impact_emoji} {event}")

            return "".join(message_parts)

        except Exception as e:
            logger.error("Failed to format channel digest", error=str(e))
            return f"📅 Daily Digest for {target_date.strftime('%d.%m.%Y')}\n\n❌ Error formatting digest."

    def add_user_digest_job(self, user_id: int, timezone: str, digest_time: time):
        """Add or update digest job for a specific user."""
        try:
            # Remove existing job if it exists
            self.remove_user_digest_job(user_id)

            # Get timezone object
            tz = pytz.timezone(timezone)

            # Create job ID
            job_id = f"user_digest_{user_id}"

            # Add the job
            self.scheduler.add_job(
                func=self._send_user_digest,
                trigger=CronTrigger(
                    hour=digest_time.hour,
                    minute=digest_time.minute,
                    timezone=tz
                ),
                args=[user_id, timezone],
                id=job_id,
                name=f'Daily Digest for User {user_id}',
                replace_existing=True
            )

            logger.info("Added user digest job", user_id=user_id, timezone=timezone, time=digest_time.strftime("%H:%M"))

        except Exception as e:
            logger.error("Failed to add user digest job", user_id=user_id, error=str(e))
            raise DigestError(f"Failed to add user digest job: {e}")

    def remove_user_digest_job(self, user_id: int):
        """Remove digest job for a specific user."""
        try:
            job_id = f"user_digest_{user_id}"

            if self.scheduler.get_job(job_id):
                self.scheduler.remove_job(job_id)
                logger.info("Removed user digest job", user_id=user_id)

        except Exception as e:
            logger.error("Failed to remove user digest job", user_id=user_id, error=str(e))

    async def _send_user_digest(self, user_id: int, timezone: str):
        """Send daily digest to a specific user."""
        try:
            logger.info("Starting user daily digest", user_id=user_id, timezone=timezone)

            # Get today's date in the user's timezone
            tz = pytz.timezone(timezone)
            today = datetime.now(tz).date()

            # Fetch news for today
            news_items = await self._fetch_today_news(today)

            if not news_items:
                logger.info("No news items found for user digest", user_id=user_id, date=today)
                return

            # Get user preferences
            user_preferences = await self._get_user_preferences(user_id)

            # Send digest
            success = await self.notification_service.send_daily_digest(
                user_id=user_id,
                news_items=news_items,
                target_date=datetime.combine(today, time()),
                user_preferences=user_preferences
            )

            if success:
                logger.info("User daily digest sent successfully", user_id=user_id)
            else:
                logger.error("Failed to send user daily digest", user_id=user_id)

        except Exception as e:
            logger.error("Failed to send user digest", user_id=user_id, error=str(e))

    def get_scheduled_jobs(self) -> List[Dict[str, Any]]:
        """Get list of all scheduled digest jobs."""
        try:
            jobs = []
            for job in self.scheduler.get_jobs():
                jobs.append({
                    'id': job.id,
                    'name': job.name,
                    'next_run_time': job.next_run_time.isoformat() if job.next_run_time else None,
                    'trigger': str(job.trigger)
                })
            return jobs

        except Exception as e:
            logger.error("Failed to get scheduled jobs", error=str(e))
            return []

    def health_check(self) -> Dict[str, Any]:
        """Check the health of the digest scheduler."""
        try:
            return {
                "status": "healthy",
                "scheduler_running": self.scheduler.running,
                "scheduled_jobs": len(self.scheduler.get_jobs()),
                "jobstore_configured": bool(self.scheduler.jobstores),
                "timezone_support": True
            }

        except Exception as e:
            logger.error("Digest scheduler health check failed", error=str(e))
            return {
                "status": "unhealthy",
                "error": str(e)
            }

    def shutdown(self):
        """Shutdown the digest scheduler."""
        try:
            if self.scheduler.running:
                self.scheduler.shutdown()
                logger.info("Digest scheduler shutdown completed")

        except Exception as e:
            logger.error("Failed to shutdown digest scheduler", error=str(e))
