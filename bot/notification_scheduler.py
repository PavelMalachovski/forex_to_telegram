import logging
import asyncio
import subprocess
import sys
import os
from datetime import datetime, timedelta, date
from typing import Optional
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.interval import IntervalTrigger
from apscheduler.triggers.cron import CronTrigger
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

            # Check for notifications every 2 minutes for more precise timing
            self.scheduler.add_job(
                self._check_notifications,
                IntervalTrigger(minutes=2),
                id='notification_check',
                name='Check for upcoming news events'
            )

            # Schedule bulk import every day at 03:00
            self.scheduler.add_job(
                self._run_bulk_import,
                CronTrigger(hour=3, minute=0),
                id='bulk_import',
                name='Daily bulk import at 03:00'
            )

            self.scheduler.start()
            logger.info("Notification scheduler started - checking every 2 minutes")
            logger.info("Bulk import scheduled for daily at 03:00")

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
                logger.debug("No notifications sent - no events within notification windows")

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

    def _run_bulk_import(self):
        """Run bulk import for yesterday to day after tomorrow."""
        try:
            logger.info("Starting scheduled bulk import...")

            # Calculate date range: yesterday to day after tomorrow
            yesterday = date.today() - timedelta(days=1)
            day_after_tomorrow = date.today() + timedelta(days=2)

            logger.info(f"Importing data from {yesterday} to {day_after_tomorrow}")

            # Get the path to the bulk_import.py script
            script_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
            bulk_import_script = os.path.join(script_dir, 'scripts', 'bulk_import.py')

            # Prepare command arguments
            cmd = [
                sys.executable,
                bulk_import_script,
                '--start-date', yesterday.strftime('%Y-%m-%d'),
                '--end-date', day_after_tomorrow.strftime('%Y-%m-%d'),
                '--impact-level', 'all',
                '--force'  # Force rewrite to ensure fresh data
            ]

            # Run the bulk import script
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=3600  # 1 hour timeout
            )

            if result.returncode == 0:
                logger.info("Bulk import completed successfully")
                logger.info(f"Output: {result.stdout}")
            else:
                logger.error(f"Bulk import failed with return code {result.returncode}")
                logger.error(f"Error: {result.stderr}")

        except subprocess.TimeoutExpired:
            logger.error("Bulk import timed out after 1 hour")
        except Exception as e:
            logger.error(f"Error running bulk import: {e}")

    def is_running(self) -> bool:
        """Check if the scheduler is running."""
        return self.scheduler is not None and self.scheduler.running
