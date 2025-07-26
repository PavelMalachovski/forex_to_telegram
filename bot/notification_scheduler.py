import logging
from datetime import datetime, timedelta
from typing import Optional
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.interval import IntervalTrigger
from sqlalchemy import text

from .notification_service import NotificationService
from .database_service import ForexNewsService
from .config import Config

logger = logging.getLogger(__name__)


class NotificationScheduler:
    """Scheduler for handling notification checks and sending."""

    def __init__(self, db_service: ForexNewsService, bot, config: Config):
        self.db_service = db_service
        self.bot = bot
        self.config = config
        self.notification_service = NotificationService(db_service, bot, config)
        self.scheduler = None
        self._setup_scheduler()

    def _setup_scheduler(self):
        """Set up the notification scheduler."""
        try:
            self.scheduler = BackgroundScheduler()

            # Check for notifications every 5 minutes
            self.scheduler.add_job(
                self._check_notifications,
                IntervalTrigger(minutes=5),
                id='notification_check',
                name='Check for upcoming news events'
            )

            self.scheduler.start()
            logger.info("Notification scheduler started - checking every 5 minutes")

        except Exception as e:
            logger.error(f"Error setting up notification scheduler: {e}")

    def _check_notifications(self):
        """Check for upcoming events and send notifications."""
        try:
            logger.info("Checking for upcoming news events...")

            # Check if notification columns exist
            with self.db_service.db_manager.get_session() as session:
                result = session.execute(text("""
                    SELECT column_name
                    FROM information_schema.columns
                    WHERE table_name = 'users'
                    AND column_name IN ('notifications_enabled', 'notification_minutes', 'notification_impact_levels')
                """))
                notification_columns = [row[0] for row in result]

                if len(notification_columns) < 3:
                    logger.info("Notification columns not fully available, skipping notification check")
                    return

            # Check notifications for all users
            notifications_sent = self.notification_service.check_and_send_notifications_for_all_users()

            if notifications_sent > 0:
                logger.info(f"Sent {notifications_sent} notifications")
            else:
                logger.debug("No notifications sent")

        except Exception as e:
            logger.error(f"Error checking notifications: {e}")

    def stop(self):
        """Stop the notification scheduler."""
        try:
            if self.scheduler:
                self.scheduler.shutdown()
                logger.info("Notification scheduler stopped")
        except Exception as e:
            logger.error(f"Error stopping notification scheduler: {e}")

    def is_running(self) -> bool:
        """Check if the scheduler is running."""
        return self.scheduler is not None and self.scheduler.running
