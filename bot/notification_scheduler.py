import logging
import asyncio
import subprocess
import sys
import os
from datetime import datetime, timedelta, date
import os
from typing import Optional
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.interval import IntervalTrigger
from apscheduler.triggers.cron import CronTrigger
from sqlalchemy import text

import pytz
from .notification_service import NotificationService, notification_deduplication
from .database_service import ForexNewsService
from .config import Config
from .chart_service import chart_service

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

        # Schedule a periodic job to send post-event charts for high impact events
        try:
            self.scheduler.add_job(
                self._send_post_event_charts,
                IntervalTrigger(minutes=10),
                id='post_event_charts',
                name='Send post-event charts for high impact events'
            )
            logger.info("Scheduled post-event chart sender every 10 minutes")
        except Exception as e:
            logger.error(f"Error adding post-event charts job: {e}")

        # Schedule channel high-impact alerts based on lead time
        try:
            self.scheduler.add_job(
                self._send_channel_high_impact_alerts,
                IntervalTrigger(minutes=1),
                id='channel_high_impact_alerts',
                name='Send channel high-impact alerts at event time'
            )
            logger.info("Scheduled channel high-impact alerts every 1 minute")
        except Exception as e:
            logger.error(f"Error adding channel high-impact alerts job: {e}")

    def _check_notifications(self):
        """Check for upcoming events and send notifications."""
        try:
            logger.info("Checking for upcoming news events...")

            # Check if notification columns exist
            with self.db_service.db_manager.get_session() as session:
                result = session.execute(text("""
                    SELECT column_name
                    FROM information_schema.columns
                    WHERE table_name = 'users' AND column_name IN ('notifications_enabled', 'notification_minutes', 'notification_impact_levels')
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

    def _send_post_event_charts(self):
        """Send charts 2 hours after high-impact events to the configured channel.

        Symbol rules:
        - USD events: USDJPY 2h before and after
        - EUR events: EURUSD 2h before and after
        - GBP events: GBPUSD 2h before and after
        - CAD events: USDCAD 2h before and after
        """
        try:
            chat_id = getattr(self.config, 'telegram_chat_id', None)
            if not chat_id:
                return

            # We will consider today's events and send charts exactly ~2 hours after event time
            today = date.today()
            # Include both high and red-AUD (AUD high-impact) events
            news_items = self.db_service.get_news_for_date(today, 'high')
            if not news_items:
                return

            # Determine current time in configured timezone
            tz_name = getattr(self.config, 'timezone', 'Europe/Prague')
            try:
                tz = pytz.timezone(tz_name)
            except Exception:
                tz = pytz.UTC
            now = datetime.now(tz)

            for item in news_items:
                time_str = item.get('time', '')
                currency = (item.get('currency') or '').upper()
                event_name = item.get('event', 'Event')
                if not time_str:
                    continue

                # Parse event time in configured timezone
                try:
                    if 'am' in time_str.lower() or 'pm' in time_str.lower():
                        event_dt = datetime.strptime(time_str.lower().replace('am', ' AM').replace('pm', ' PM'), "%I:%M %p")
                    else:
                        event_dt = datetime.strptime(time_str, "%H:%M")
                    event_dt = tz.localize(datetime.combine(today, event_dt.time()))
                except Exception:
                    continue

                minutes_after = (now - event_dt).total_seconds() / 60.0
                # Send near 2 hours after (within a window) and only once (dedup via caption hash)
                if 110 <= minutes_after <= 140:
                    # Map currency to required pair
                    pair_map = {
                        'USD': 'USDJPY=X',
                        'EUR': 'EURUSD=X',
                        'GBP': 'GBPUSD=X',
                        'CAD': 'USDCAD=X',
                        'AUD': 'USDAUD=X',
                    }
                    symbol = pair_map.get(currency)
                    if not symbol:
                        continue

                    # Build chart around event time ±2h
                    # Use chart_service to fetch data directly for the mapped symbol
                    start_time = event_dt - timedelta(hours=2)
                    end_time = event_dt + timedelta(hours=2)
                    data = chart_service.fetch_price_data(symbol, start_time, end_time)
                    if data is None or data.empty:
                        continue

                    # Use multi-currency chart to force the exact pair mapping
                    pair_to_currencies = {
                        'USDJPY=X': ('USD', 'JPY'),
                        'EURUSD=X': ('EUR', 'USD'),
                        'GBPUSD=X': ('GBP', 'USD'),
                        'USDCAD=X': ('USD', 'CAD'),
                        'USDAUD=X': ('USD', 'AUD'),
                    }
                    primary_cur, secondary_cur = pair_to_currencies[symbol]

                    # Deduplicate per event+pair to avoid multiple sends in the 30 min window
                    if not notification_deduplication.should_send_notification(
                        'post_event_chart',
                        currency=currency,
                        event=event_name,
                        event_time_iso=event_dt.isoformat(),
                        symbol=symbol
                    ):
                        continue

                    img = chart_service.create_multi_currency_chart(
                        primary_currency=primary_cur,
                        secondary_currency=secondary_cur,
                        event_time=event_dt,
                        event_name=f"{event_name} — 2h post-event",
                        impact_level='high',
                        window_hours=2,
                        before_hours=2,
                        after_hours=2
                    )
                    if not img:
                        continue

                    caption = (
                        f"📊 {currency} {event_name}\n"
                        f"Window: 2h before → 2h after\n"
                        f"Pair: {symbol.replace('=X','')}"
                    )
                    try:
                        self.bot.send_photo(chat_id, img, caption=caption)
                        logger.info(f"Sent post-event chart for {currency} {event_name}")
                    except Exception as e:
                        logger.error(f"Failed sending post-event chart: {e}")
        except Exception as e:
            logger.error(f"Error in post-event charts job: {e}")

    def _send_channel_high_impact_alerts(self):
        """Send channel notifications near the time of high-impact events.

        Lead time can be configured with env var CHANNEL_ALERT_MINUTES_BEFORE (default 30).
        A window of ±2.5 minutes is allowed to accommodate scheduler granularity.
        """
        try:
            chat_id = getattr(self.config, 'telegram_chat_id', None)
            if not chat_id:
                return

            today = date.today()
            items = self.db_service.get_news_for_date(today, 'high')
            if not items:
                return

            tz_name = getattr(self.config, 'timezone', 'Europe/Prague')
            try:
                tz = pytz.timezone(tz_name)
            except Exception:
                tz = pytz.UTC
            now = datetime.now(tz)
            try:
                minutes_before = int(os.getenv('CHANNEL_ALERT_MINUTES_BEFORE', '30'))
            except Exception:
                minutes_before = 30

            for item in items:
                t = item.get('time', '')
                if not t:
                    continue
                try:
                    if 'am' in t.lower() or 'pm' in t.lower():
                        event_dt = datetime.strptime(t.lower().replace('am', ' AM').replace('pm', ' PM'), "%I:%M %p")
                    else:
                        event_dt = datetime.strptime(t, "%H:%M")
                    event_dt = tz.localize(datetime.combine(today, event_dt.time()))
                except Exception:
                    continue

                minutes_until = (event_dt - now).total_seconds() / 60.0
                # Fire when within ±2.5 minutes of desired lead time
                if abs(minutes_until - minutes_before) <= 2.5:
                    # Dedup per event
                    if not notification_deduplication.should_send_notification(
                        'channel_high_event',
                        currency=item.get('currency'),
                        event=item.get('event'),
                        event_time_iso=event_dt.isoformat()
                    ):
                        continue

                    # Reuse NotificationService formatter for consistency
                    try:
                        msg = self.notification_service.format_notification_message(item, minutes_before=max(int(round(minutes_until)), 0), user_timezone=tz_name)
                    except Exception:
                        # Minimal fallback
                        msg = f"⚠️ Now: {item.get('currency')} | {item.get('event')} | High Impact"
                    try:
                        self.bot.send_message(chat_id, msg, parse_mode="HTML")
                        logger.info("Sent channel high-impact alert")
                        # Chain a poll after channel alert
                        try:
                            from .notification_service import NotificationService
                            # Use a lightweight temp instance that shares bot/config
                            temp_service = NotificationService(self.db_service, self.bot, self.config)
                            temp_service._send_direction_poll(chat_id, item.get('currency'), item.get('event'))
                        except Exception as pe:
                            logger.error(f"Error sending channel poll: {pe}")
                    except Exception as e:
                        logger.error(f"Failed to send channel high-impact alert: {e}")
        except Exception as e:
            logger.error(f"Error in channel high-impact alerts: {e}")

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
