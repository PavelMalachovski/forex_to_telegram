
"""
Notification service for sending Telegram notifications.
"""

from typing import List
from datetime import datetime, timedelta
from pytz import timezone
import telebot
from sqlalchemy.orm import Session

from app.config import config
from app.services.news_service import NewsService
from app.services.user_service import UserService
from app.services.analysis_service import AnalysisService
from app.utils.text_utils import escape_markdown
import logging

logger = logging.getLogger(__name__)

class NotificationService:
    """Service for handling Telegram notifications."""
    
    def __init__(self, db: Session, bot: telebot.TeleBot):
        self.db = db
        self.bot = bot
        self.news_service = NewsService(db)
        self.user_service = UserService(db)
        self.analysis_service = AnalysisService()
        self.timezone = timezone(config.TIMEZONE)
    
    def check_and_send_notifications(self) -> None:
        """Check and send notifications for upcoming high-impact events."""
        if not self.bot or not config.TELEGRAM_CHAT_ID:
            logger.error("Cannot send notifications: Bot or CHAT_ID not configured")
            return
        
        try:
            now = datetime.now(self.timezone)
            start_date = now.date()
            end_date = (now + timedelta(days=3)).date()
            
            # Get high-impact news items
            news_items = self.news_service.get_news_by_date_range(
                start_date=start_date,
                end_date=end_date,
                impact_levels=["HIGH"]
            )
            
            if not news_items:
                logger.info("No high-impact news items to notify about.")
                return
            
            # Group events by currency and time
            grouped_events = self.news_service.group_events_by_time_and_currency(news_items)
            
            for (event_date, event_time, currency), events in grouped_events.items():
                try:
                    event_datetime = self.timezone.localize(
                        datetime.strptime(f"{event_date} {event_time}", "%Y-%m-%d %H:%M")
                    )
                    time_diff = (event_datetime - now).total_seconds() / 60
                except ValueError as e:
                    logger.warning(f"Could not parse event time: {event_time} for date {event_date}, error: {e}")
                    continue
                
                # Send notification 20 minutes before the event
                if 19 <= time_diff <= 21:
                    self._send_event_notification(events, currency)
        
        except Exception as e:
            logger.error(f"Error in notification check: {e}")
    
    def _send_event_notification(self, events: List, currency: str) -> None:
        """Send notification for a group of events."""
        try:
            # Prepare event data for analysis
            event_data = []
            for event in events:
                event_data.append({
                    'currency': currency,
                    'event_name': event.event_name,
                    'forecast': event.forecast or 'N/A',
                    'previous_value': event.previous_value or 'N/A',
                    'actual_value': event.actual_value or 'N/A'
                })
            
            # Get combined analysis
            combined_analysis = self.analysis_service.analyze_combined_events(event_data)
            
            # Build notification message
            event_names = [event.event_name for event in events]
            forecasts = [event.forecast or 'N/A' for event in events]
            previous_values = [event.previous_value or 'N/A' for event in events]
            actual_values = [event.actual_value or 'N/A' for event in events]
            event_time = events[0].event_time.strftime('%H:%M')
            
            message = (
                f"⏰ Reminder: In 20 minutes, there will be a news event!\n"
                f"💱 Currency: {escape_markdown(currency)}\n"
                f"📰 Events: {escape_markdown(' & '.join(event_names))}\n"
                f"📈 Forecast: {escape_markdown(' & '.join(forecasts))}\n"
                f"📊 Previous: {escape_markdown(' & '.join(previous_values))}\n"
                f"🎯 Actual: {escape_markdown(' & '.join(actual_values))}\n"
                f"🔍 Combined ChatGPT Analysis: {escape_markdown(combined_analysis)}\n"
                f"📅 Time: {escape_markdown(event_time)}"
            )
            
            # Send to users with currency preference
            users_with_preference = self.user_service.get_all_users_with_currency_preference(currency)
            
            for user in users_with_preference:
                try:
                    self.bot.send_message(
                        user.telegram_user_id, 
                        message, 
                        parse_mode='MarkdownV2', 
                        disable_web_page_preview=True
                    )
                    logger.info(f"Sent notification to user {user.telegram_user_id} for {currency} events")
                except Exception as e:
                    logger.error(f"Failed to send notification to user {user.telegram_user_id}: {e}")
            
            # Also send to main chat if configured
            if config.TELEGRAM_CHAT_ID:
                try:
                    self.bot.send_message(
                        config.TELEGRAM_CHAT_ID,
                        message,
                        parse_mode='MarkdownV2',
                        disable_web_page_preview=True
                    )
                    logger.info(f"Sent notification to main chat for {currency} events")
                except Exception as e:
                    logger.error(f"Failed to send notification to main chat: {e}")
        
        except Exception as e:
            logger.error(f"Error sending event notification: {e}")
    
    def send_long_message(self, chat_id: int, text: str) -> None:
        """Send long message, splitting if necessary."""
        text = text.strip()
        if not text:
            logger.error("Attempted to send empty message")
            return
        
        while text:
            if len(text) <= 4096:
                part = text
                text = ""
            else:
                # Find a good place to split (preferably at a newline)
                cut = text[:4096].rfind('\n') if '\n' in text[:4096] else 4096
                part = text[:cut].strip()
                text = text[cut:].strip()
            
            if part:
                try:
                    self.bot.send_message(
                        chat_id, 
                        part, 
                        parse_mode='MarkdownV2', 
                        disable_web_page_preview=True
                    )
                except telebot.apihelper.ApiTelegramException as e:
                    logger.error(f"MarkdownV2 send failed: {e}. Falling back to plain text.")
                    # Remove markdown formatting and try again
                    plain_text = part.replace('\\', '')
                    self.bot.send_message(chat_id, plain_text)
