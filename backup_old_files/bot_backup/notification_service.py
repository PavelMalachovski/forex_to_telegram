import logging
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional, Set
from io import BytesIO
import hashlib
import threading
import html

from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton
from sqlalchemy import text
import pytz

from .database_service import ForexNewsService
from .config import Config
from .chart_service import chart_service

logger = logging.getLogger(__name__)


class NotificationDeduplicationService:
    """Service to handle notification deduplication and tracking."""

    def __init__(self):
        self.sent_notifications: Dict[str, datetime] = {}
        # Track group notifications with timestamps for cleanup
        self.group_notifications: Dict[str, datetime] = {}
        # Track last chart sent per target (user/channel) to rate-limit charts
        self.last_chart_sent: Dict[str, datetime] = {}
        self.cleanup_interval = timedelta(hours=24)  # Clean up old notifications every 24 hours
        self.last_cleanup = datetime.now()
        self._lock = threading.Lock()

    def _generate_notification_id(self, event_type: str, **kwargs) -> str:
        """Generate a unique ID for a notification based on its parameters."""
        # Create a string representation of the notification parameters
        params_str = f"{event_type}:{':'.join(f'{k}={v}' for k, v in sorted(kwargs.items()))}"
        return hashlib.md5(params_str.encode()).hexdigest()

    def _cleanup_old_notifications(self):
        """Remove notifications older than the cleanup interval."""
        now = datetime.now()
        if now - self.last_cleanup > self.cleanup_interval:
            cutoff_time = now - self.cleanup_interval
            old_notifications = [
                notification_id for notification_id, timestamp in self.sent_notifications.items()
                if timestamp < cutoff_time
            ]
            for notification_id in old_notifications:
                del self.sent_notifications[notification_id]

            old_group = [key for key, ts in self.group_notifications.items() if ts < cutoff_time]
            for key in old_group:
                del self.group_notifications[key]

            # Cleanup old chart rate-limit records (older than 12 hours)
            chart_cutoff = now - timedelta(hours=12)
            old_charts = [key for key, ts in self.last_chart_sent.items() if ts < chart_cutoff]
            for key in old_charts:
                del self.last_chart_sent[key]

            self.last_cleanup = now
            logger.info(f"Cleaned up {len(old_notifications)} old notifications and {len(old_group)} old group notifications")

    def should_send_notification(self, event_type: str, **kwargs) -> bool:
        """Check if a notification should be sent (prevents duplicates)."""
        with self._lock:
            self._cleanup_old_notifications()

            notification_id = self._generate_notification_id(event_type, **kwargs)

            if notification_id in self.sent_notifications:
                logger.info(f"Notification already sent for {event_type} with params {kwargs}")
                return False

            # Mark as sent
            self.sent_notifications[notification_id] = datetime.now()
            logger.info(f"New notification approved for {event_type} with params {kwargs}")
            return True

    def should_send_group_notification(self, group_id: str, user_id: str, message_hash: str) -> bool:
        """Check if a group notification should be sent (prevents spam)."""
        group_key = f"{group_id}:{user_id}:{message_hash}"

        with self._lock:
            if group_key in self.group_notifications:
                logger.info(f"Group notification already sent for {group_key}")
                return False

            # Mark as sent with timestamp
            self.group_notifications[group_key] = datetime.now()
            logger.info(f"New group notification approved for {group_key}")
            return True

    def get_notification_stats(self) -> Dict:
        """Get notification statistics."""
        with self._lock:
            return {
                "active_notifications": len(self.sent_notifications),
                "group_notifications": len(self.group_notifications),
                "chart_rate_limits": len(self.last_chart_sent),
                "last_cleanup": self.last_cleanup.isoformat()
            }

    def can_send_chart(self, target_id: str, min_minutes: int = 120) -> bool:
        """Return True if we can send a chart to this target based on cooldown."""
        with self._lock:
            last = self.last_chart_sent.get(str(target_id))
            if not last:
                return True
            return (datetime.now() - last) >= timedelta(minutes=min_minutes)

    def mark_chart_sent(self, target_id: str):
        with self._lock:
            self.last_chart_sent[str(target_id)] = datetime.now()


# Global notification deduplication service instance
notification_deduplication = NotificationDeduplicationService()


class NotificationService:
    """Handles notification logic for high-impact news events."""

    def __init__(self, db_service: ForexNewsService, bot, config: Config):
        self.db_service = db_service
        self.bot = bot
        self.config = config
        self.deduplication = notification_deduplication

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

            # Format the notification message (escape for HTML)
            message = f"⚠️ In {minutes_before} minutes: {html.escape(str(impact))} news!\n"
            message += f"{html.escape(str(time_str))} | {html.escape(str(currency))} | {html.escape(str(event))} | {impact_emoji} {html.escape(str(impact).capitalize())} Impact"

            return message
        except Exception as e:
            logger.error(f"Error formatting notification message: {e}")
            return f"⚠️ News event in {minutes_before} minutes!"

    def format_group_notification_message(self, events: List[Dict[str, Any]], minutes_before: int, user_timezone: str = "Europe/Prague") -> str:
        """Format a notification message for multiple events happening at the same time."""
        try:
            if not events:
                return "⚠️ Multiple news events coming up!"

            # Group events by impact level
            high_impact = []
            medium_impact = []
            low_impact = []

            for event_data in events:
                item = event_data['item']
                impact = item.get('impact', 'low')
                if impact == 'high':
                    high_impact.append(item)
                elif impact == 'medium':
                    medium_impact.append(item)
                else:
                    low_impact.append(item)

            # Create the main message
            message = f"⚠️ In {minutes_before} minutes: Multiple news events!\n\n"

            # Add events by impact level (high first, then medium, then low)
            for impact_level, items, emoji in [('high', high_impact, '🔴'), ('medium', medium_impact, '🟠'), ('low', low_impact, '🟡')]:
                if items:
                    message += f"{emoji} {html.escape(impact_level.capitalize())} Impact:\n"
                    for item in items:
                        time_str = item.get('time', 'N/A')
                        currency = item.get('currency', 'N/A')
                        event = item.get('event', 'N/A')
                        message += f"• {html.escape(str(time_str))} | {html.escape(str(currency))} | {html.escape(str(event))}\n"
                    message += "\n"

            return message.strip()

        except Exception as e:
            logger.error(f"Error formatting group notification message: {e}")
            return f"⚠️ Multiple news events in {minutes_before} minutes!"

    def _send_direction_poll(self, chat_id: int, currency: str, event_name: str) -> bool:
        """Send a direction poll for the given currency/event with two options (down/up)."""
        try:
            if not self.bot:
                return False

            currency = (currency or '').upper()
            pair_map = {
                'USD': 'USDJPY',
                'EUR': 'EURUSD',
                'GBP': 'GBPUSD',
                'CAD': 'USDCAD',
            }
            pair = pair_map.get(currency, currency)
            question = f"Do you think {pair} will go down or up?"
            options = ["⬇️ Down", "⬆️ Up"]
            # Use anonymous poll with single choice, no callbacks
            self.bot.send_poll(chat_id, question, options, is_anonymous=True, allows_multiple_answers=False)
            logger.info(f"Sent direction poll for {pair} to {chat_id}")
            return True
        except Exception as e:
            logger.error(f"Failed to send direction poll: {e}")
            return False

    def get_upcoming_events(self, target_date: datetime, impact_levels: List[str],
                           minutes_before: int, user_timezone: str = "Europe/Prague") -> List[Dict[str, Any]]:
        """Get events that are coming up within the specified time window."""
        try:
            # Get all news for the target date
            news_items = self.db_service.get_news_for_date(target_date.date(), 'all')
            if not news_items:
                return []

            upcoming_events = []

            # Get current time in user's timezone
            try:
                user_tz = pytz.timezone(user_timezone)
                current_time = datetime.now(user_tz)
            except Exception as e:
                logger.error(f"Error getting user timezone {user_timezone}: {e}")
                # Fallback to UTC
                current_time = datetime.now(pytz.UTC)

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
                    event_time = self._parse_event_time(target_date, time_str, user_timezone)
                    if not event_time:
                        continue

                    # Calculate time difference
                    time_diff = event_time - current_time
                    minutes_diff = time_diff.total_seconds() / 60

                    # Check if event is within the notification window (exactly at the notification time)
                    # Only send notification when we're exactly at the notification time (e.g., 30 minutes before)
                    if abs(minutes_diff - minutes_before) <= 2.5:  # Allow 2.5 minute window for scheduling
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

    def _parse_event_time(self, target_date: datetime, time_str: str, user_timezone: str = "Europe/Prague") -> Optional[datetime]:
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

            # Convert to user's timezone
            try:
                user_tz = pytz.timezone(user_timezone)
                event_datetime = user_tz.localize(event_datetime)
            except Exception as e:
                logger.error(f"Error localizing event time to {user_timezone}: {e}")
                # Fallback to UTC
                event_datetime = pytz.UTC.localize(event_datetime)

            return event_datetime

        except Exception as e:
            logger.error(f"Error parsing time '{time_str}': {e}")
            return None

    def _group_events_by_time(self, events: List[Dict[str, Any]]) -> Dict[str, List[Dict[str, Any]]]:
        """Group events by their time to identify events happening at the same time."""
        grouped_events = {}

        for event_data in events:
            item = event_data['item']
            time_str = item.get('time', '')

            # Use time as the grouping key
            if time_str not in grouped_events:
                grouped_events[time_str] = []
            grouped_events[time_str].append(event_data)

        return grouped_events

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
            user_timezone = user.get_timezone()
            upcoming_events = self.get_upcoming_events(
                target_date,
                impact_levels,
                user.notification_minutes,
                user_timezone
            )

            if not upcoming_events:
                return True  # No events to notify about

            # Group events by time
            grouped_events = self._group_events_by_time(upcoming_events)

            # Send notifications for each group of events
            for time_str, events in grouped_events.items():
                if len(events) == 1:
                    # Single event - send individual notification
                    event_data = events[0]
                    item = event_data['item']
                    minutes_until = event_data['minutes_until']

                    # Check if we should send this notification (deduplication)
                    if not self.deduplication.should_send_notification("news_event",
                                                                      event_id=item.get('id', 'unknown'),
                                                                      user_id=user_id,
                                                                      notification_minutes=user.notification_minutes):
                        logger.info(f"Skipping duplicate notification for event {item.get('id')} to user {user_id}")
                        continue

                    # Format notification message
                    message = self.format_notification_message(item, minutes_until, user_timezone)

                    # Send the notification
                    try:
                        # Check if user has charts enabled
                        if getattr(user, 'charts_enabled', False):
                            chart_buffer = self._generate_event_chart(item, user)
                            if chart_buffer and self.deduplication.can_send_chart(user_id):
                                # Send message with chart
                                self.bot.send_photo(user_id, chart_buffer, caption=message, parse_mode="HTML")
                                logger.info(f"Sent notification with chart to user {user_id} for event at {item.get('time')}")
                                # Mark chart sent for rate limit
                                try:
                                    self.deduplication.mark_chart_sent(user_id)
                                except Exception:
                                    pass
                            else:
                                # Fallback to text-only if chart generation fails
                                self.bot.send_message(user_id, message, parse_mode="HTML")
                                logger.info(f"Sent text-only notification to user {user_id} for event at {item.get('time')} (chart generation failed)")
                        else:
                            # Send text-only notification
                            self.bot.send_message(user_id, message, parse_mode="HTML")
                            logger.info(f"Sent notification to user {user_id} for event at {item.get('time')}")
                        # Send a follow-up poll for direction
                        try:
                            self._send_direction_poll(user_id, item.get('currency'), item.get('event'))
                        except Exception as e:
                            logger.error(f"Error sending poll to user {user_id}: {e}")
                    except Exception as e:
                        logger.error(f"Error sending notification to user {user_id}: {e}")

                else:
                    # Multiple events at the same time - send group notification
                    minutes_until = events[0]['minutes_until']

                    # Create a hash of the events for deduplication
                    event_ids = sorted([e['item'].get('id', '') for e in events])
                    events_hash = hashlib.md5(str(event_ids).encode()).hexdigest()

                    # Check if we should send this group notification (deduplication)
                    if not self.deduplication.should_send_notification("group_news_event",
                                                                      user_id=user_id,
                                                                      events_hash=events_hash,
                                                                      notification_minutes=user.notification_minutes):
                        logger.info(f"Skipping duplicate group notification for events at {time_str} to user {user_id}")
                        continue

                    # Format group notification message
                    message = self.format_group_notification_message(events, minutes_until, user_timezone)

                    # Send the group notification
                    try:
                        # Check if user has charts enabled
                        if getattr(user, 'charts_enabled', False):
                            # Use the first event as the canonical event for chart generation
                            main_event = events[0]['item']
                            chart_buffer = self._generate_event_chart(main_event, user)
                            if chart_buffer and self.deduplication.can_send_chart(user_id):
                                # Send message with chart
                                self.bot.send_photo(user_id, chart_buffer, caption=message, parse_mode="HTML")
                                logger.info(f"Sent group notification with chart to user {user_id} for {len(events)} events at {time_str}")
                                # Mark chart sent for rate limit
                                try:
                                    self.deduplication.mark_chart_sent(user_id)
                                except Exception:
                                    pass
                            else:
                                # Fallback to text-only if chart generation fails
                                self.bot.send_message(user_id, message, parse_mode="HTML")
                                logger.info(f"Sent text-only group notification to user {user_id} for {len(events)} events at {time_str} (chart generation failed)")
                        else:
                            # Send text-only notification
                            self.bot.send_message(user_id, message, parse_mode="HTML")
                            logger.info(f"Sent group notification to user {user_id} for {len(events)} events at {time_str}")
                        
                        # Send only ONE poll for the group using the first event
                        main_event = events[0]['item']
                        try:
                            self._send_direction_poll(user_id, main_event.get('currency'), main_event.get('event'))
                        except Exception as e:
                            logger.error(f"Error sending group poll to user {user_id}: {e}")
                    except Exception as e:
                        logger.error(f"Error sending group notification to user {user_id}: {e}")

            return True

        except Exception as e:
            logger.error(f"Error sending notifications to user {user_id}: {e}")
            return False

    def _generate_event_chart(self, news_item: Dict[str, Any], user) -> Optional[BytesIO]:
        """Generate a chart for a news event based on user preferences."""
        try:
            currency = news_item.get('currency', 'USD')
            event_name = news_item.get('event', 'Unknown Event')
            impact_level = news_item.get('impact_level', 'medium')

            # Parse event time
            event_time = self._parse_event_time(
                datetime.now(),
                news_item.get('time', ''),
                user.get_timezone()
            )

            if not event_time:
                logger.warning(f"Could not parse event time for chart generation: {news_item.get('time')}")
                return None

            # Get user chart preferences
            chart_type = getattr(user, 'chart_type', 'single')
            window_hours = getattr(user, 'chart_window_hours', 2)

            # Generate chart based on user preference
            if chart_type == 'multi':
                chart_buffer = chart_service.create_multi_pair_chart(
                    currency=currency,
                    event_time=event_time,
                    event_name=event_name,
                    impact_level=impact_level,
                    window_hours=window_hours
                )
            else:  # Default to single chart
                chart_buffer = chart_service.create_event_chart(
                    currency=currency,
                    event_time=event_time,
                    event_name=event_name,
                    impact_level=impact_level,
                    window_hours=window_hours
                )

            return chart_buffer

        except Exception as e:
            logger.error(f"Error generating chart for event {news_item.get('id')}: {e}")
            return None

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
                    WHERE table_name = 'users' AND column_name IN ('notifications_enabled', 'notification_minutes', 'notification_impact_levels')
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
