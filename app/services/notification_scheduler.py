
"""
Notification scheduler service for sending alerts before high-impact events.
"""

import logging
from datetime import datetime, timedelta
from typing import List, Set

# Optional APScheduler import with fallback
try:
    from apscheduler.schedulers.background import BackgroundScheduler
    from apscheduler.triggers.date import DateTrigger
    APSCHEDULER_AVAILABLE = True
except ImportError:
    APSCHEDULER_AVAILABLE = False
    logger = logging.getLogger(__name__)
    logger.warning("APScheduler not available. Notification scheduling will be disabled.")

from app.database.models import NewsEvent, BotUser, UserNotificationSettings
from app.utils.timezone_utils import get_current_time, get_local_timezone
from app.utils.text_utils import escape_markdown_v2

logger = logging.getLogger(__name__)

class DummyScheduler:
    """Dummy scheduler for when APScheduler is not available."""
    
    def __init__(self):
        self.running = False
    
    def start(self):
        self.running = True
        logger.info("Dummy scheduler started (APScheduler not available)")
    
    def add_job(self, *args, **kwargs):
        logger.debug("Dummy scheduler: job scheduling skipped (APScheduler not available)")
    
    def get_jobs(self):
        """Return empty list of jobs for compatibility."""
        return []
    
    def shutdown(self):
        self.running = False
        logger.info("Dummy scheduler stopped")

class NotificationScheduler:
    """Service for scheduling and sending notifications."""
    
    def __init__(self, bot, db_session_factory):
        self.bot = bot
        self.db_session_factory = db_session_factory
        self.scheduled_events: Set[str] = set()  # Отслеживание запланированных событий
        
        # Initialize scheduler based on availability
        if APSCHEDULER_AVAILABLE:
            self.scheduler = BackgroundScheduler()
            self.scheduler.start()
            logger.info("Notification scheduler started with APScheduler")
        else:
            self.scheduler = DummyScheduler()
            self.scheduler.start()
            logger.warning("Notification scheduler started with dummy scheduler (APScheduler not available)")
    
    def schedule_notifications_for_events(self, events: List[NewsEvent]):
        """
        Schedule notifications for a list of events.
        
        Args:
            events: List of NewsEvent objects to schedule notifications for
        """
        with self.db_session_factory() as db:
            # Get all users with notification settings
            users_with_notifications = db.query(BotUser).join(
                UserNotificationSettings
            ).filter(
                UserNotificationSettings.notifications_enabled
            ).all()
            
            for event in events:
                # Only schedule for HIGH impact events
                if not event.impact_level or event.impact_level.code != "HIGH":
                    continue
                
                # Создаем уникальный ключ для события
                event_key = f"{event.event_date}_{event.event_time}_{event.id}"
                
                # Проверяем, не запланировано ли уже это событие
                if event_key in self.scheduled_events:
                    logger.debug(f"Event {event.event_name} already scheduled, skipping")
                    continue
                
                # Create timezone-aware datetime
                local_tz = get_local_timezone()
                naive_datetime = datetime.combine(event.event_date, event.event_time)
                event_datetime = local_tz.localize(naive_datetime)
                notifications_scheduled = False
                
                for user in users_with_notifications:
                    settings = user.notification_settings
                    if not settings:
                        continue
                    
                    # Schedule 15-minute notification
                    if settings.notify_15_minutes:
                        notify_time = event_datetime - timedelta(minutes=15)
                        if notify_time > get_current_time():
                            self._schedule_single_notification(
                                user.telegram_user_id,
                                event,
                                notify_time,
                                "15 minutes"
                            )
                            notifications_scheduled = True
                    
                    # Schedule 30-minute notification
                    if settings.notify_30_minutes:
                        notify_time = event_datetime - timedelta(minutes=30)
                        if notify_time > get_current_time():
                            self._schedule_single_notification(
                                user.telegram_user_id,
                                event,
                                notify_time,
                                "30 minutes"
                            )
                            notifications_scheduled = True
                    
                    # Schedule 60-minute notification
                    if settings.notify_60_minutes:
                        notify_time = event_datetime - timedelta(minutes=60)
                        if notify_time > get_current_time():
                            self._schedule_single_notification(
                                user.telegram_user_id,
                                event,
                                notify_time,
                                "60 minutes"
                            )
                            notifications_scheduled = True
                
                # Отмечаем событие как запланированное
                if notifications_scheduled:
                    self.scheduled_events.add(event_key)
                    logger.info(f"Scheduled notifications for event: {event.event_name} at {event_datetime}")
    
    def _schedule_single_notification(self, user_id: int, event: NewsEvent, notify_time: datetime, time_before: str):
        """
        Schedule a single notification.
        
        Args:
            user_id: Telegram user ID
            event: NewsEvent object
            notify_time: When to send the notification
            time_before: Human-readable time before event (e.g., "15 minutes")
        """
        job_id = f"notify_{user_id}_{event.id}_{time_before.replace(' ', '_')}"
        
        try:
            if APSCHEDULER_AVAILABLE:
                self.scheduler.add_job(
                    func=self._send_notification,
                    trigger=DateTrigger(run_date=notify_time),
                    args=[user_id, event, time_before],
                    id=job_id,
                    replace_existing=True
                )
                logger.info(f"Scheduled notification for user {user_id} at {notify_time} for event {event.event_name}")
            else:
                self.scheduler.add_job()  # Dummy call
                logger.debug(f"Notification scheduling skipped for user {user_id} (APScheduler not available)")
        except Exception as e:
            logger.error(f"Failed to schedule notification: {e}")
    
    def _send_notification(self, user_id: int, event: NewsEvent, time_before: str):
        """
        Send a notification to a user.
        
        Args:
            user_id: Telegram user ID
            event: NewsEvent object
            time_before: Human-readable time before event
        """
        try:
            currency_symbol = self._get_currency_symbol(event.currency.code)
            impact_emoji = self._get_impact_emoji(event.impact_level.code)
            
            message = (
                f"🚨 *HIGH IMPACT EVENT ALERT* 🚨\n\n"
                f"{impact_emoji} *{escape_markdown_v2(event.impact_level.code)}* impact in *{time_before}*\n\n"
                f"⏰ Time: {event.event_time.strftime('%H:%M')} CET\n"
                f"💱 Currency: {currency_symbol} {event.currency.code}\n"
                f"📰 Event: {escape_markdown_v2(event.event_name)}\n"
                f"📈 Forecast: {escape_markdown_v2(event.forecast or 'N/A')}\n"
                f"📊 Previous: {escape_markdown_v2(event.previous_value or 'N/A')}\n\n"
                f"🔍 Analysis: {escape_markdown_v2(event.analysis or 'No analysis available')}\n\n"
                f"💡 *Prepare for potential market volatility\\!*"
            )
            
            self.bot.send_message(
                user_id,
                message,
                parse_mode='MarkdownV2'
            )
            
            logger.info(f"Sent notification to user {user_id} for event {event.event_name}")
            
        except Exception as e:
            logger.error(f"Failed to send notification to user {user_id}: {e}")
    
    def _get_currency_symbol(self, currency_code: str) -> str:
        """Get currency symbol from code."""
        from app.utils.text_utils import get_currency_symbol
        return get_currency_symbol(currency_code)
    
    def _get_impact_emoji(self, impact_code: str) -> str:
        """Get impact emoji from code."""
        from app.utils.text_utils import get_impact_emoji_and_color
        emoji, _ = get_impact_emoji_and_color(impact_code)
        return emoji
    
    def cleanup_old_events(self):
        """Очистка устаревших событий из отслеживания."""
        current_time = get_current_time()
        events_to_remove = set()
        
        for event_key in self.scheduled_events:
            # Парсим дату из ключа события
            try:
                date_part = event_key.split('_')[0]
                event_date = datetime.strptime(date_part, '%Y-%m-%d').date()
                
                # Удаляем события старше текущей даты
                if event_date < current_time.date():
                    events_to_remove.add(event_key)
            except (ValueError, IndexError):
                # Если не можем распарсить, удаляем для безопасности
                events_to_remove.add(event_key)
        
        for event_key in events_to_remove:
            self.scheduled_events.discard(event_key)
        
        if events_to_remove:
            logger.info(f"Cleaned up {len(events_to_remove)} old events from tracking")
    
    def stop(self):
        """Stop the scheduler."""
        if self.scheduler.running:
            self.scheduler.shutdown()
            logger.info("Notification scheduler stopped")
