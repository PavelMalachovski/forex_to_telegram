import logging
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional
from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton
from sqlalchemy import text

from .database_service import ForexNewsService
from .config import Config

logger = logging.getLogger(__name__)


class NotificationService:
    """Handles notification logic for high-impact news events."""

    def __init__(self, db_service: ForexNewsService, bot, config: Config):
        self.db_service = db_service
        self.bot = bot
        self.config = config

    def format_notification_message(self, news_item: Dict[str, Any], minutes_before: int, user_timezone: str = "Europe/Prague") -> str:
        """Format a notification message for a news event."""
        try:
            # Format time
            time_str = news_item.get('time', 'N/A')
            currency = news_item.get('currency', 'N/A')
            event = news_item.get('event', 'N/A')
            impact = news_item.get('impact', 'N/A')

            # Create impact emoji
            impact_emoji = {
                'high': '🔴',
                'medium': '🟠',
                'low': '🟡'
            }.get(impact, '⚪')

            # Format the notification message with "impact" word as requested
            message = f"⚠️ In {minutes_before} minutes: {impact} impact news!\n"
            message += f"{time_str} | {currency} | {event} | {impact_emoji} {impact.capitalize()} Impact"

            return message
        except Exception as e:
            logger.error(f"Error formatting notification message: {e}")
            return f"⚠️ News event in {minutes_before} minutes!"

    def get_upcoming_events(self, target_date: datetime, impact_levels: List[str],
                           minutes_before: int) -> List[Dict[str, Any]]:
        """Get events that are coming up within the specified time window."""
        try:
            # Get all news for the target date
            news_items = self.db_service.get_news_for_date(target_date.date(), 'all')
            if not news_items:
                return []

            upcoming_events = []
            current_time = datetime.now()

            for item in news_items:
                # Check if this item matches the impact levels we're looking for
                if item.get('impact') not in impact_levels:
                    continue

                # Parse the event time
                try:
                    time_str = item.get('time', '')
                    if not time_str or time_str == 'N/A':
                        continue

                    # Parse time string to datetime
                    event_time = self._parse_event_time(target_date, time_str)
                    if not event_time:
                        continue

                    # Calculate time difference
                    time_diff = event_time - current_time
                    minutes_diff = time_diff.total_seconds() / 60

                    # Check if event is within the notification window
                    if 0 <= minutes_diff <= minutes_before:
                        upcoming_events.append({
                            'item': item,
                            'minutes_until': int(minutes_diff),
                            'event_time': event_time
                        })

                except Exception as e:
                    logger.error(f"Error processing event time: {e}")
                    continue

            return upcoming_events

        except Exception as e:
            logger.error(f"Error getting upcoming events: {e}")
            return []

    def _parse_event_time(self, target_date: datetime, time_str: str) -> Optional[datetime]:
        """Parse event time string to datetime object."""
        try:
            # Handle various time formats
            time_str = time_str.strip().lower()

            if "am" in time_str or "pm" in time_str:
                # 12-hour format
                time_obj = datetime.strptime(time_str.replace("am", " AM").replace("pm", " PM"), "%I:%M %p")
            else:
                # 24-hour format
                time_obj = datetime.strptime(time_str, "%H:%M")

            # Combine with target date
            event_datetime = datetime.combine(target_date.date(), time_obj.time())
            return event_datetime

        except Exception as e:
            logger.error(f"Error parsing time '{time_str}': {e}")
            return None

    def send_notifications(self, user_id: int, target_date: datetime = None) -> bool:
        """Send notifications to a specific user for upcoming events."""
        try:
            if not self.bot:
                logger.error("Bot not available for notifications")
                return False

            # Get user preferences
            user = self.db_service.get_or_create_user(user_id)
            if not user.notifications_enabled:
                return True  # Notifications disabled, not an error

            if target_date is None:
                target_date = datetime.now()

            # Get upcoming events
            impact_levels = user.get_notification_impact_levels_list()
            upcoming_events = self.get_upcoming_events(
                target_date,
                impact_levels,
                user.notification_minutes
            )

            if not upcoming_events:
                return True  # No events to notify about

            # Send notifications for each upcoming event
            for event_data in upcoming_events:
                item = event_data['item']
                minutes_until = event_data['minutes_until']

                # Get user's timezone
                user_timezone = getattr(user, 'timezone', 'Europe/Prague')

                # Format notification message
                message = self.format_notification_message(item, minutes_until, user_timezone)

                # Send the notification
                try:
                    self.bot.send_message(user_id, message, parse_mode="HTML")
                    logger.info(f"Sent notification to user {user_id} for event at {item.get('time')}")
                except Exception as e:
                    logger.error(f"Error sending notification to user {user_id}: {e}")

            return True

        except Exception as e:
            logger.error(f"Error sending notifications to user {user_id}: {e}")
            return False

    def check_and_send_notifications_for_all_users(self, target_date: datetime = None) -> int:
        """Check and send notifications for all users with notifications enabled."""
        try:
            if not self.db_service:
                logger.error("Database service not available")
                return 0

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
                    logger.info("Notification columns not fully available, skipping notifications")
                    return 0

            # Get all users with notifications enabled
            users = self.db_service.get_users_with_notifications_enabled()
            if not users:
                return 0

            notifications_sent = 0
            for user in users:
                if self.send_notifications(user.telegram_id, target_date):
                    notifications_sent += 1

            logger.info(f"Sent notifications to {notifications_sent} users")
            return notifications_sent

        except Exception as e:
            logger.error(f"Error checking notifications for all users: {e}")
            return 0
