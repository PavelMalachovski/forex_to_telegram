

"""
Telegram bot handlers for user interactions.
"""

import logging
from datetime import datetime, timedelta

import telebot
from telebot import types
from telebot.apihelper import ApiTelegramException

from app.services.news_service import NewsService
from app.services.user_service import UserService
from app.utils.text_utils import escape_markdown_v2, format_news_message
from app.utils.timezone_utils import get_current_time
from app.bot.utils.calendar import create_calendar_markup, process_calendar_callback, get_date_selection_message

logger = logging.getLogger(__name__)

class BotHandlers:
    """Telegram bot handlers."""
    
    def __init__(self, bot: telebot.TeleBot, db_session_factory):
        self.bot = bot
        self.db_session_factory = db_session_factory
        self._register_handlers()
    
    def _safe_answer_callback_query(self, call, text: str = None, show_alert: bool = False):
        """Safely answer callback query with proper error handling."""
        try:
            # Validate callback query
            if not call or not call.data:
                logger.warning("Invalid callback query: missing call or data")
                return False
            
            # Check if callback query is not too old (older than 1 hour is considered stale)
            if hasattr(call, 'message') and call.message:
                # Создаем aware datetime из timestamp
                import pytz
                message_time = datetime.fromtimestamp(call.message.date, tz=pytz.UTC)
                current_time = get_current_time()
                
                # Конвертируем в одинаковый часовой пояс для корректного сравнения
                if current_time.tzinfo != message_time.tzinfo:
                    message_time = message_time.astimezone(current_time.tzinfo)
                
                time_diff = current_time - message_time
                
                if time_diff.total_seconds() > 3600:  # 1 hour
                    logger.warning(f"Callback query is too old: {time_diff.total_seconds()} seconds")
                    return False
            
            self.bot.answer_callback_query(call.id, text, show_alert)
            return True
            
        except ApiTelegramException as e:
            if "query is too old" in str(e).lower() or "query id is invalid" in str(e).lower():
                logger.warning(f"Callback query expired or invalid: {e}")
                return False
            else:
                logger.error(f"Telegram API error in callback query: {e}")
                return False
        except Exception as e:
            logger.error(f"Unexpected error in callback query handling: {e}")
            return False
    
    def _register_handlers(self):
        """Register all bot handlers."""
        self.bot.message_handler(commands=['start'])(self.start_command)
        self.bot.message_handler(commands=['help'])(self.help_command)
        self.bot.message_handler(commands=['news'])(self.news_command)
        self.bot.message_handler(commands=['today'])(self.today_command)
        self.bot.message_handler(commands=['tomorrow'])(self.tomorrow_command)
        self.bot.message_handler(commands=['week'])(self.week_command)
        self.bot.message_handler(commands=['preferences'])(self.preferences_command)
        self.bot.message_handler(commands=['status'])(self.status_command)
        self.bot.message_handler(commands=['calendar', 'choose_date'])(self.calendar_command)
        
        # Callback query handlers
        self.bot.callback_query_handler(func=lambda call: call.data.startswith('impact_'))(self.handle_impact_selection)
        self.bot.callback_query_handler(func=lambda call: call.data.startswith('currency_toggle_') or call.data in ['currency_select_all', 'currency_clear_all', 'currency_done'])(self.handle_currency_selection)
        self.bot.callback_query_handler(func=lambda call: call.data.startswith('pref_'))(self.handle_preference_selection)
        self.bot.callback_query_handler(func=lambda call: call.data.startswith('calendar_'))(self.handle_calendar_callback)
        self.bot.callback_query_handler(func=lambda call: call.data.startswith('date_impact_'))(self.handle_date_impact_selection)
        self.bot.callback_query_handler(func=lambda call: call.data.startswith('notify_'))(self.handle_notification_setting)
        self.bot.callback_query_handler(func=lambda call: call.data == 'show_preferences')(self.handle_show_preferences)
        self.bot.callback_query_handler(func=lambda call: call.data == 'select_currencies')(self.handle_select_currencies)
    
    def start_command(self, message):
        """Handle /start command."""
        with self.db_session_factory() as db:
            try:
                user_service = UserService(db)
                
                # Create or get user
                user = user_service.create_or_get_user(
                    telegram_user_id=message.from_user.id,
                    username=message.from_user.username,
                    first_name=message.from_user.first_name,
                    last_name=message.from_user.last_name
                )
                
                welcome_text = (
                    f"👋 Welcome to Forex News Bot, {escape_markdown_v2(user.first_name or 'User')}\\!\n\n"
                    f"🔹 Get the latest forex news and economic events\n"
                    f"🔹 Filter by impact level and currency\n"
                    f"🔹 Set your preferences for personalized notifications\n\n"
                    f"Use /help to see all available commands\\."
                )
                
                # Create notification settings menu
                markup = types.InlineKeyboardMarkup(row_width=2)
                markup.add(
                    types.InlineKeyboardButton("🔔 15 min", callback_data="notify_15"),
                    types.InlineKeyboardButton("🔔 30 min", callback_data="notify_30"),
                    types.InlineKeyboardButton("🔔 60 min", callback_data="notify_60")
                )
                markup.add(types.InlineKeyboardButton("⚙️ Preferences", callback_data="show_preferences"))
                
                self.bot.send_message(
                    message.chat.id,
                    welcome_text,
                    parse_mode='MarkdownV2'
                )
                
                self.bot.send_message(
                    message.chat.id,
                    "🔔 *Notification Settings*\n\nChoose when you want to be notified before high\\-impact events:",
                    parse_mode='MarkdownV2',
                    reply_markup=markup
                )
                
            except Exception as e:
                logger.error(f"Error in start command: {e}")
                self.bot.send_message(
                    message.chat.id,
                    "❌ An error occurred. Please try again later."
                )
    
    def help_command(self, message):
        """Handle /help command."""
        try:
            help_text = escape_markdown_v2(
                "📋 Available Commands:\n\n"
                "/start - Start the bot and register\n"
                "/help - Show this help message\n"
                "/news - Get news for a specific date\n"
                "/calendar - Choose date using calendar interface\n"
                "/today - Get today's high-impact news\n"
                "/tomorrow - Get tomorrow's high-impact news\n"
                "/week - Get this week's high-impact news\n"
                "/preferences - Set your currency preferences\n"
                "/status - Check your current settings\n\n"
                "💡 Tips:\n"
                "• Use /news followed by date (YYYY-MM-DD) for specific dates\n"
                "• Use /calendar for easy date selection with visual calendar\n"
                "• Set preferences to get personalized notifications\n"
                "• All times are shown in CET timezone"
            )
            
            self.bot.send_message(
                message.chat.id,
                help_text,
                parse_mode='MarkdownV2'
            )
            
        except Exception as e:
            logger.error(f"Error in help command: {e}")
            self.bot.send_message(
                message.chat.id,
                "❌ An error occurred. Please try again later."
            )
    
    def news_command(self, message):
        """Handle /news command with optional date and impact level."""
        import asyncio
        
        with self.db_session_factory() as db:
            try:
                # Parse command arguments
                args = message.text.split()[1:] if len(message.text.split()) > 1 else []
                
                if not args:
                    # Show impact level selection
                    markup = types.InlineKeyboardMarkup(row_width=3)
                    # ИСПРАВЛЕНИЕ 2: Изменить цвета кнопок
                    markup.add(
                        types.InlineKeyboardButton("🔴 HIGH", callback_data="impact_HIGH"),
                        types.InlineKeyboardButton("🟠 MEDIUM", callback_data="impact_MEDIUM"),
                        types.InlineKeyboardButton("🟡 LOW", callback_data="impact_LOW")
                    )
                    markup.add(types.InlineKeyboardButton("📊 ALL", callback_data="impact_ALL"))
                    
                    self.bot.send_message(
                        message.chat.id,
                        "📊 Select impact level for today's news:",
                        reply_markup=markup
                    )
                    return
                
                date_str = args[0]
                impact_level = args[1].upper() if len(args) > 1 else "HIGH"
                
                # Validate date format
                try:
                    target_date = datetime.strptime(date_str, '%Y-%m-%d').date()
                except ValueError:
                    self.bot.send_message(
                        message.chat.id,
                        "❌ Invalid date format. Please use YYYY-MM-DD format."
                    )
                    return
                
                # Show loading message
                loading_msg = self.bot.send_message(
                    message.chat.id,
                    text=f"🔄 Fetching Forex news for *{escape_markdown_v2(date_str)}*\nImpact: *{escape_markdown_v2(impact_level)}*",
                    parse_mode='MarkdownV2'
                )
                
                news_service = NewsService(db)
                
                # Check if data exists, if not - trigger auto-scraping
                if not news_service.has_data_for_date(target_date):
                    # Update loading message to indicate scraping
                    self.bot.edit_message_text(
                        f"🔄 No data found for *{escape_markdown_v2(date_str)}*\\.\n🌐 Scraping data from ForexFactory\\.\\.\\.\n⏳ This may take a moment\\.",
                        loading_msg.chat.id,
                        loading_msg.message_id,
                        parse_mode='MarkdownV2'
                    )
                
                # Get news events with auto-scraping
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
                try:
                    news_events, was_scraped = loop.run_until_complete(
                        news_service.get_or_scrape_news_by_date(target_date, impact_level)
                    )
                finally:
                    loop.close()
                
                # Delete loading message
                self.bot.delete_message(message.chat.id, loading_msg.message_id)
                
                if news_events:
                    # Format and send message
                    formatted_message = format_news_message(news_events, date_str, impact_level)
                    
                    # Add scraping notification if data was scraped
                    if was_scraped:
                        scraping_notice = "🌐 *Data scraped from ForexFactory*\n\n"
                        formatted_message = scraping_notice + formatted_message
                    
                    # Send message using notification service for long messages
                    from app.services.notification_service import NotificationService
                    notification_service = NotificationService(db, self.bot)
                    notification_service.send_long_message(message.chat.id, formatted_message)
                else:
                    scraping_status = "scraped from ForexFactory" if was_scraped else "found in database"
                    self.bot.send_message(
                        message.chat.id,
                        f"✅ No news {scraping_status} for {escape_markdown_v2(date_str)} with impact: {escape_markdown_v2(impact_level)}\\.\nPlease check the website for updates\\.",
                        parse_mode='MarkdownV2'
                    )
                
            except Exception as e:
                logger.error(f"Error in news command: {e}")
                self.bot.send_message(
                    message.chat.id,
                    "❌ An error occurred while fetching news. Please try again later."
                )
    
    def today_command(self, message):
        """Handle /today command."""
        import asyncio
        
        with self.db_session_factory() as db:
            try:
                today = get_current_time().date()
                news_service = NewsService(db)
                
                # Show loading message
                loading_msg = self.bot.send_message(
                    message.chat.id,
                    "🔄 Fetching today's high\\-impact Forex news\\.\\.\\.",
                    parse_mode='MarkdownV2'
                )
                
                # Check if data exists, if not - trigger auto-scraping
                if not news_service.has_data_for_date(today):
                    # Update loading message to indicate scraping
                    self.bot.edit_message_text(
                        "🔄 No data found for today\\.\n🌐 Scraping data from ForexFactory\\.\\.\\.\n⏳ This may take a moment\\.",
                        loading_msg.chat.id,
                        loading_msg.message_id,
                        parse_mode='MarkdownV2'
                    )
                
                # Get high-impact news for today with auto-scraping
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
                try:
                    news_events, was_scraped = loop.run_until_complete(
                        news_service.get_or_scrape_news_by_date(today, "HIGH")
                    )
                finally:
                    loop.close()
                
                # Delete loading message
                self.bot.delete_message(message.chat.id, loading_msg.message_id)
                
                if news_events:
                    # Format and send message
                    formatted_message = format_news_message(news_events, today.strftime('%Y-%m-%d'))
                    
                    # Add scraping notification if data was scraped
                    if was_scraped:
                        scraping_notice = "🌐 *Data scraped from ForexFactory*\n\n"
                        formatted_message = scraping_notice + formatted_message
                    
                    # Send message using notification service for long messages
                    from app.services.notification_service import NotificationService
                    notification_service = NotificationService(db, self.bot)
                    notification_service.send_long_message(message.chat.id, formatted_message)
                else:
                    scraping_status = "scraped from ForexFactory" if was_scraped else "found in database"
                    self.bot.send_message(
                        message.chat.id,
                        f"✅ No high\\-impact news {scraping_status} for today \\({escape_markdown_v2(today.strftime('%d.%m.%Y'))}\\)\\.\nPlease check the website for updates\\.",
                        parse_mode='MarkdownV2'
                    )
                
            except Exception as e:
                logger.error(f"Error in today command: {e}")
                self.bot.send_message(
                    message.chat.id,
                    "❌ An error occurred while fetching today's news. Please try again later."
                )
    
    def tomorrow_command(self, message):
        """Handle /tomorrow command."""
        import asyncio
        
        with self.db_session_factory() as db:
            try:
                tomorrow = get_current_time().date() + timedelta(days=1)
                news_service = NewsService(db)
                
                # Show loading message
                loading_msg = self.bot.send_message(
                    message.chat.id,
                    "🔄 Fetching tomorrow's high\\-impact Forex news\\.\\.\\.",
                    parse_mode='MarkdownV2'
                )
                
                # Check if data exists, if not - trigger auto-scraping
                if not news_service.has_data_for_date(tomorrow):
                    # Update loading message to indicate scraping
                    self.bot.edit_message_text(
                        "🔄 No data found for tomorrow\\.\n🌐 Scraping data from ForexFactory\\.\\.\\.\n⏳ This may take a moment\\.",
                        loading_msg.chat.id,
                        loading_msg.message_id,
                        parse_mode='MarkdownV2'
                    )
                
                # Get high-impact news for tomorrow with auto-scraping
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
                try:
                    news_events, was_scraped = loop.run_until_complete(
                        news_service.get_or_scrape_news_by_date(tomorrow, "HIGH")
                    )
                finally:
                    loop.close()
                
                # Delete loading message
                self.bot.delete_message(message.chat.id, loading_msg.message_id)
                
                if news_events:
                    # Format and send message
                    formatted_message = format_news_message(news_events, tomorrow.strftime('%Y-%m-%d'))
                    
                    # Add scraping notification if data was scraped
                    if was_scraped:
                        scraping_notice = "🌐 *Data scraped from ForexFactory*\n\n"
                        formatted_message = scraping_notice + formatted_message
                    
                    # Send message using notification service for long messages
                    from app.services.notification_service import NotificationService
                    notification_service = NotificationService(db, self.bot)
                    notification_service.send_long_message(message.chat.id, formatted_message)
                else:
                    scraping_status = "scraped from ForexFactory" if was_scraped else "found in database"
                    self.bot.send_message(
                        message.chat.id,
                        f"✅ No high\\-impact news {scraping_status} for tomorrow \\({escape_markdown_v2(tomorrow.strftime('%d.%m.%Y'))}\\)\\.\nPlease check the website for updates\\.",
                        parse_mode='MarkdownV2'
                    )
                
            except Exception as e:
                logger.error(f"Error in tomorrow command: {e}")
                self.bot.send_message(
                    message.chat.id,
                    "❌ An error occurred while fetching tomorrow's news. Please try again later."
                )
    
    def week_command(self, message):
        """Handle /week command."""
        with self.db_session_factory() as db:
            try:
                today = get_current_time().date()
                week_end = today + timedelta(days=7)
                
                news_service = NewsService(db)
                news_events = news_service.get_news_by_date_range(
                    start_date=today,
                    end_date=week_end,
                    impact_levels=["HIGH"]
                )
                
                if news_events:
                    # Group events by date
                    events_by_date = {}
                    for event in news_events:
                        date_key = event.event_date.strftime('%Y-%m-%d')
                        if date_key not in events_by_date:
                            events_by_date[date_key] = []
                        events_by_date[date_key].append(event)
                    
                    # Send message for each date
                    for date_str, events in sorted(events_by_date.items()):
                        formatted_message = format_news_message(events, date_str)
                        
                        # Send message using notification service for long messages
                        from app.services.notification_service import NotificationService
                        notification_service = NotificationService(db, self.bot)
                        notification_service.send_long_message(message.chat.id, formatted_message)
                else:
                    self.bot.send_message(
                        message.chat.id,
                        "✅ No high\\-impact news found for this week\\.\nPlease check the website for updates\\.",
                        parse_mode='MarkdownV2'
                    )
                
            except Exception as e:
                logger.error(f"Error in week command: {e}")
                self.bot.send_message(
                    message.chat.id,
                    "❌ An error occurred while fetching this week's news. Please try again later."
                )
    
    def preferences_command(self, message):
        """Handle /preferences command."""
        with self.db_session_factory() as db:
            try:
                from app.services.user_service import UserService
                user_service = UserService(db)
                # Создаем пользователя если он не существует
                user = user_service.create_or_get_user(
                    telegram_user_id=message.from_user.id,
                    username=message.from_user.username,
                    first_name=message.from_user.first_name,
                    last_name=message.from_user.last_name
                )
                
                # Get notification settings
                notification_settings = user.notification_settings
                if not notification_settings:
                    # Create default settings
                    from app.database.models import UserNotificationSettings
                    notification_settings = UserNotificationSettings(
                        user_id=user.id,
                        notifications_enabled=True,
                        notify_15_minutes=False,
                        notify_30_minutes=False,
                        notify_60_minutes=False
                    )
                    db.add(notification_settings)
                    db.commit()
                
                # Get current currency preferences
                current_currencies = user_service.get_user_currency_preferences(message.from_user.id)
                currency_display = ", ".join(current_currencies) if current_currencies else "All currencies"
                
                # Show current settings
                settings_text = (
                    f"⚙️ *Current Settings*\n\n"
                    f"🔔 Notifications: {'✅ Enabled' if notification_settings.notifications_enabled else '❌ Disabled'}\n"
                    f"⏰ 15 min alerts: {'✅' if notification_settings.notify_15_minutes else '❌'}\n"
                    f"⏰ 30 min alerts: {'✅' if notification_settings.notify_30_minutes else '❌'}\n"
                    f"⏰ 60 min alerts: {'✅' if notification_settings.notify_60_minutes else '❌'}\n"
                    f"💱 Currency preferences: {escape_markdown_v2(currency_display)}\n\n"
                    f"Choose options to modify:"
                )
                
                markup = types.InlineKeyboardMarkup(row_width=2)
                markup.add(
                    types.InlineKeyboardButton("🔔 15 min", callback_data="notify_15"),
                    types.InlineKeyboardButton("🔔 30 min", callback_data="notify_30"),
                    types.InlineKeyboardButton("🔔 60 min", callback_data="notify_60")
                )
                # ИСПРАВЛЕНИЕ 4: Добавить кнопку для множественного выбора валют
                markup.add(types.InlineKeyboardButton("💱 Select Currencies", callback_data="select_currencies"))
                
                self.bot.send_message(
                    message.chat.id,
                    settings_text,
                    parse_mode='MarkdownV2',
                    reply_markup=markup
                )
                
            except Exception as e:
                logger.error(f"Error in preferences command: {e}")
                self.bot.send_message(
                    message.chat.id,
                    "❌ An error occurred while loading preferences. Please try again later."
                )
    
    def status_command(self, message):
        """Handle /status command."""
        with self.db_session_factory() as db:
            try:
                user_service = UserService(db)
                # Создаем пользователя если он не существует
                user = user_service.create_or_get_user(
                    telegram_user_id=message.from_user.id,
                    username=message.from_user.username,
                    first_name=message.from_user.first_name,
                    last_name=message.from_user.last_name
                )
                
                # Get notification settings
                notification_settings = user.notification_settings
                if notification_settings:
                    notifications_status = (
                        f"🔔 Notifications: {'✅ Enabled' if notification_settings.notifications_enabled else '❌ Disabled'}\n"
                        f"⏰ 15 min alerts: {'✅' if notification_settings.notify_15_minutes else '❌'}\n"
                        f"⏰ 30 min alerts: {'✅' if notification_settings.notify_30_minutes else '❌'}\n"
                        f"⏰ 60 min alerts: {'✅' if notification_settings.notify_60_minutes else '❌'}\n"
                    )
                else:
                    notifications_status = "🔔 Notifications: ❌ Not configured\n"
                
                status_text = (
                    f"👤 User Status:\n\n"
                    f"🆔 ID: {escape_markdown_v2(str(user.telegram_user_id))}\n"
                    f"👤 Name: {escape_markdown_v2(user.first_name or 'N/A')}\n"
                    f"🏷️ Username: {escape_markdown_v2(user.telegram_username or 'N/A')}\n"
                    f"🌐 Language: {escape_markdown_v2(user.language_code or 'N/A')}\n"
                    f"✅ Active: {'Yes' if user.is_active else 'No'}\n"
                    f"📅 Registered: {escape_markdown_v2(user.created_at.strftime('%d.%m.%Y %H:%M'))}\n"
                    f"🕐 Last Activity: {escape_markdown_v2(user.last_activity.strftime('%d.%m.%Y %H:%M') if user.last_activity else 'N/A')}\n\n"
                    f"{notifications_status}"
                )
                
                self.bot.send_message(
                    message.chat.id,
                    status_text,
                    parse_mode='MarkdownV2'
                )
                
            except Exception as e:
                logger.error(f"Error in status command: {e}")
                self.bot.send_message(
                    message.chat.id,
                    "❌ An error occurred. Please try again later."
                )
    
    def handle_impact_selection(self, call):
        """Handle impact level selection."""
        import asyncio
        
        # Validate callback query first
        if not self._safe_answer_callback_query(call):
            return
        
        with self.db_session_factory() as db:
            try:
                impact_level = call.data.replace('impact_', '')
                today = get_current_time().date()
                
                # Edit message to show loading
                self.bot.edit_message_text(
                    f"🔄 Fetching {impact_level} impact news for today...",
                    call.message.chat.id,
                    call.message.message_id
                )
                
                news_service = NewsService(db)
                
                # Check if data exists, if not - trigger auto-scraping
                if not news_service.has_data_for_date(today):
                    # Update loading message to indicate scraping
                    self.bot.edit_message_text(
                        f"🔄 No data found for today\\.\n🌐 Scraping {impact_level} impact news from ForexFactory\\.\\.\\.\n⏳ This may take a moment\\.",
                        call.message.chat.id,
                        call.message.message_id,
                        parse_mode='MarkdownV2'
                    )
                
                # Get news events with auto-scraping
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
                try:
                    news_events, was_scraped = loop.run_until_complete(
                        news_service.get_or_scrape_news_by_date(today, impact_level)
                    )
                finally:
                    loop.close()
                
                # Delete the loading message
                self.bot.delete_message(call.message.chat.id, call.message.message_id)
                
                if news_events:
                    # Format and send message
                    formatted_message = format_news_message(news_events, today.strftime('%Y-%m-%d'), impact_level)
                    
                    # Add scraping notification if data was scraped
                    if was_scraped:
                        scraping_notice = "🌐 *Data scraped from ForexFactory*\n\n"
                        formatted_message = scraping_notice + formatted_message
                    
                    # Send message using notification service for long messages
                    from app.services.notification_service import NotificationService
                    notification_service = NotificationService(db, self.bot)
                    notification_service.send_long_message(call.message.chat.id, formatted_message)
                else:
                    scraping_status = "scraped from ForexFactory" if was_scraped else "found in database"
                    self.bot.send_message(
                        call.message.chat.id,
                        f"✅ No {impact_level.lower()}\\-impact news {scraping_status} for today\\.\nPlease check the website for updates\\.",
                        parse_mode='MarkdownV2'
                    )
                
            except Exception as e:
                logger.error(f"Error in impact selection: {e}")
                self.bot.send_message(
                    call.message.chat.id,
                    "❌ An error occurred. Please try again later."
                )
    
    def handle_currency_selection(self, call):
        """Handle currency selection with multiple selection support."""
        # Validate callback query first
        if not self._safe_answer_callback_query(call):
            return
            
        with self.db_session_factory() as db:
            try:
                user_service = UserService(db)
                
                # ИСПРАВЛЕНИЕ 4: Реализовать множественный выбор валют для уведомлений
                if call.data.startswith('currency_toggle_'):
                    # Toggle individual currency
                    currency_code = call.data.replace('currency_toggle_', '')
                    current_preferences = user_service.get_user_currency_preferences(call.from_user.id)
                    
                    if currency_code in current_preferences:
                        # Remove currency
                        user_service.remove_user_currency_preference(call.from_user.id, currency_code)
                        current_preferences.remove(currency_code)
                    else:
                        # Add currency
                        user_service.add_user_currency_preference(call.from_user.id, currency_code)
                        current_preferences.append(currency_code)
                    
                    # Update keyboard with new selection
                    from app.bot.keyboards import BotKeyboards
                    new_markup = BotKeyboards.generate_currency_selection(current_preferences)
                    
                    self.bot.edit_message_reply_markup(
                        call.message.chat.id,
                        call.message.message_id,
                        reply_markup=new_markup
                    )
                    
                elif call.data == 'currency_select_all':
                    # Select all currencies
                    from app.config import config
                    user_service.set_user_currency_preferences(call.from_user.id, config.AVAILABLE_CURRENCIES)
                    
                    from app.bot.keyboards import BotKeyboards
                    new_markup = BotKeyboards.generate_currency_selection(config.AVAILABLE_CURRENCIES)
                    
                    self.bot.edit_message_reply_markup(
                        call.message.chat.id,
                        call.message.message_id,
                        reply_markup=new_markup
                    )
                    
                elif call.data == 'currency_clear_all':
                    # Clear all currencies
                    user_service.set_user_currency_preferences(call.from_user.id, [])
                    
                    from app.bot.keyboards import BotKeyboards
                    new_markup = BotKeyboards.generate_currency_selection([])
                    
                    self.bot.edit_message_reply_markup(
                        call.message.chat.id,
                        call.message.message_id,
                        reply_markup=new_markup
                    )
                    
                elif call.data == 'currency_done':
                    # Finish currency selection
                    current_preferences = user_service.get_user_currency_preferences(call.from_user.id)
                    
                    if current_preferences:
                        currency_display = ", ".join(current_preferences)
                        message_text = f"✅ Currency preferences updated!\n💱 Selected currencies: {currency_display}"
                    else:
                        message_text = "✅ Currency preferences cleared!\n💱 You will receive notifications for all currencies."
                    
                    self.bot.edit_message_text(
                        message_text,
                        call.message.chat.id,
                        call.message.message_id
                    )
                
            except Exception as e:
                logger.error(f"Error in currency selection: {e}")
                self.bot.send_message(
                    call.message.chat.id,
                    "❌ An error occurred while updating currency preferences."
                )
    
    def handle_preference_selection(self, call):
        """Handle preference selection."""
        # Validate callback query first
        if not self._safe_answer_callback_query(call):
            return
            
        with self.db_session_factory() as db:
            try:
                currency = call.data.replace('pref_', '')
                user_service = UserService(db)
                
                # Update user preferences
                user = user_service.update_user_preferences(
                    telegram_user_id=call.from_user.id,
                    currency_preference=currency if currency != "ALL" else None,
                    notifications_enabled=True
                )
                
                if user:
                    currency_display = currency if currency != "ALL" else "All currencies"
                    self.bot.edit_message_text(
                        f"✅ Preferences updated!\n💱 Currency: {currency_display}\n🔔 Notifications: Enabled",
                        call.message.chat.id,
                        call.message.message_id
                    )
                else:
                    self.bot.edit_message_text(
                        "❌ Failed to update preferences. Please try /start first.",
                        call.message.chat.id,
                        call.message.message_id
                    )
                
            except Exception as e:
                logger.error(f"Error in preference selection: {e}")
                self.bot.edit_message_text(
                    "❌ An error occurred. Please try again later.",
                    call.message.chat.id,
                    call.message.message_id
                )
    
    def calendar_command(self, message):
        """Handle /calendar and /choose_date commands."""
        try:
            calendar_markup = create_calendar_markup()
            message_text = get_date_selection_message()
            
            self.bot.send_message(
                message.chat.id,
                message_text,
                reply_markup=calendar_markup
            )
            
        except Exception as e:
            logger.error(f"Error in calendar command: {e}")
            self.bot.send_message(
                message.chat.id,
                "❌ An error occurred while creating calendar. Please try again later."
            )
    
    def handle_calendar_callback(self, call):
        """Handle calendar callback queries."""
        # Validate callback query first
        if not self._safe_answer_callback_query(call):
            return
            
        with self.db_session_factory():
            try:
                action, selected_date, navigation_data = process_calendar_callback(call.data)
                
                if action == "ignore":
                    # Do nothing for ignored buttons
                    return
                
                elif action == "close":
                    # Close calendar
                    self.bot.delete_message(call.message.chat.id, call.message.message_id)
                    return
                
                elif action == "prev" or action == "next":
                    # Navigate to different month
                    year, month = navigation_data
                    new_markup = create_calendar_markup(year, month)
                    
                    self.bot.edit_message_reply_markup(
                        call.message.chat.id,
                        call.message.message_id,
                        reply_markup=new_markup
                    )
                    return
                
                elif action == "today":
                    # Select today's date
                    selected_date = get_current_time().date()
                
                elif action == "select":
                    # Date was selected
                    pass
                
                # If we reach here, a date was selected
                if selected_date:
                    # Delete calendar message
                    self.bot.delete_message(call.message.chat.id, call.message.message_id)
                    
                    # Show impact level selection for the selected date
                    markup = types.InlineKeyboardMarkup(row_width=3)
                    # ИСПРАВЛЕНИЕ 2: Изменить цвета кнопок в календаре
                    markup.add(
                        types.InlineKeyboardButton("🔴 HIGH", callback_data=f"date_impact_HIGH_{selected_date.strftime('%Y-%m-%d')}"),
                        types.InlineKeyboardButton("🟠 MEDIUM", callback_data=f"date_impact_MEDIUM_{selected_date.strftime('%Y-%m-%d')}"),
                        types.InlineKeyboardButton("🟡 LOW", callback_data=f"date_impact_LOW_{selected_date.strftime('%Y-%m-%d')}")
                    )
                    markup.add(types.InlineKeyboardButton("📊 ALL", callback_data=f"date_impact_ALL_{selected_date.strftime('%Y-%m-%d')}"))
                    
                    date_formatted = selected_date.strftime('%d.%m.%Y')
                    self.bot.send_message(
                        call.message.chat.id,
                        f"📅 Выбрана дата: *{escape_markdown_v2(date_formatted)}*\n\n📊 Выберите уровень важности новостей:",
                        parse_mode='MarkdownV2',
                        reply_markup=markup
                    )
                
            except Exception as e:
                logger.error(f"Error in calendar callback: {e}")
                self.bot.send_message(
                    call.message.chat.id,
                    "❌ Произошла ошибка при обработке календаря."
                )
    
    def handle_date_impact_selection(self, call):
        """Handle date and impact level selection from calendar."""
        import asyncio
        
        # Validate callback query first
        if not self._safe_answer_callback_query(call):
            return
        
        with self.db_session_factory() as db:
            try:
                # Parse callback data: date_impact_LEVEL_YYYY-MM-DD
                parts = call.data.split('_')
                impact_level = parts[2]
                date_str = parts[3]
                
                # Validate date format
                try:
                    selected_date = datetime.strptime(date_str, '%Y-%m-%d').date()
                except ValueError:
                    self.bot.send_message(
                        call.message.chat.id,
                        "❌ Неверный формат даты"
                    )
                    return
                
                # Edit message to show loading
                self.bot.edit_message_text(
                    f"🔄 Загружаем новости за {escape_markdown_v2(selected_date.strftime('%d.%m.%Y'))} с уровнем важности: {impact_level}...",
                    call.message.chat.id,
                    call.message.message_id
                )
                
                news_service = NewsService(db)
                
                # Check if data exists, if not - trigger auto-scraping
                if not news_service.has_data_for_date(selected_date):
                    # Update loading message to indicate scraping
                    self.bot.edit_message_text(
                        f"🔄 Данные за {escape_markdown_v2(selected_date.strftime('%d.%m.%Y'))} не найдены\\.\n🌐 Загружаем данные с ForexFactory\\.\\.\\.\n⏳ Это может занять некоторое время\\.",
                        call.message.chat.id,
                        call.message.message_id,
                        parse_mode='MarkdownV2'
                    )
                
                # Get news events with auto-scraping
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
                try:
                    news_events, was_scraped = loop.run_until_complete(
                        news_service.get_or_scrape_news_by_date(selected_date, impact_level)
                    )
                finally:
                    loop.close()
                
                # Delete the loading message
                self.bot.delete_message(call.message.chat.id, call.message.message_id)
                
                if news_events:
                    # Format and send message
                    formatted_message = format_news_message(news_events, date_str, impact_level)
                    
                    # Add scraping notification if data was scraped
                    if was_scraped:
                        scraping_notice = "🌐 *Данные загружены с ForexFactory*\n\n"
                        formatted_message = scraping_notice + formatted_message
                    
                    # Send message using notification service for long messages
                    from app.services.notification_service import NotificationService
                    notification_service = NotificationService(db, self.bot)
                    notification_service.send_long_message(call.message.chat.id, formatted_message)
                else:
                    date_formatted = selected_date.strftime('%d.%m.%Y')
                    scraping_status = "загружены с ForexFactory" if was_scraped else "найдены в базе данных"
                    self.bot.send_message(
                        call.message.chat.id,
                        f"✅ Новости не {scraping_status} за {escape_markdown_v2(date_formatted)} с уровнем важности: {escape_markdown_v2(impact_level)}\\.\nПроверьте сайт для обновлений\\.",
                        parse_mode='MarkdownV2'
                    )
                
                self._safe_answer_callback_query(call)
                
            except Exception as e:
                logger.error(f"Error in date impact selection: {e}")
                self._safe_answer_callback_query(call, "❌ Произошла ошибка")
                self.bot.send_message(
                    call.message.chat.id,
                    "❌ An error occurred while fetching news. Please try again later."
                )
    
    def handle_notification_setting(self, call):
        """Handle notification setting toggle."""
        # Validate callback query first
        if not self._safe_answer_callback_query(call):
            return
            
        with self.db_session_factory() as db:
            try:
                from app.services.user_service import UserService
                user_service = UserService(db)
                # Создаем пользователя если он не существует
                user = user_service.create_or_get_user(
                    telegram_user_id=call.from_user.id,
                    username=call.from_user.username,
                    first_name=call.from_user.first_name,
                    last_name=call.from_user.last_name
                )
                
                # Get or create notification settings
                notification_settings = user.notification_settings
                if not notification_settings:
                    from app.database.models import UserNotificationSettings
                    notification_settings = UserNotificationSettings(
                        user_id=user.id,
                        notifications_enabled=True,
                        notify_15_minutes=False,
                        notify_30_minutes=False,
                        notify_60_minutes=False
                    )
                    db.add(notification_settings)
                    db.flush()
                
                # Toggle the appropriate setting
                if call.data == "notify_15":
                    notification_settings.notify_15_minutes = not notification_settings.notify_15_minutes
                    status = "включены" if notification_settings.notify_15_minutes else "отключены"
                    self.bot.send_message(call.message.chat.id, f"🔔 Уведомления за 15 минут {status}")
                elif call.data == "notify_30":
                    notification_settings.notify_30_minutes = not notification_settings.notify_30_minutes
                    status = "включены" if notification_settings.notify_30_minutes else "отключены"
                    self.bot.send_message(call.message.chat.id, f"🔔 Уведомления за 30 минут {status}")
                elif call.data == "notify_60":
                    notification_settings.notify_60_minutes = not notification_settings.notify_60_minutes
                    status = "включены" if notification_settings.notify_60_minutes else "отключены"
                    self.bot.send_message(call.message.chat.id, f"🔔 Уведомления за 60 минут {status}")
                
                db.commit()
                
                # Update the message with new settings
                settings_text = (
                    f"⚙️ *Current Settings*\n\n"
                    f"🔔 Notifications: {'✅ Enabled' if notification_settings.notifications_enabled else '❌ Disabled'}\n"
                    f"⏰ 15 min alerts: {'✅' if notification_settings.notify_15_minutes else '❌'}\n"
                    f"⏰ 30 min alerts: {'✅' if notification_settings.notify_30_minutes else '❌'}\n"
                    f"⏰ 60 min alerts: {'✅' if notification_settings.notify_60_minutes else '❌'}\n\n"
                    f"Choose options to modify:"
                )
                
                markup = types.InlineKeyboardMarkup(row_width=2)
                markup.add(
                    types.InlineKeyboardButton("🔔 15 min", callback_data="notify_15"),
                    types.InlineKeyboardButton("🔔 30 min", callback_data="notify_30"),
                    types.InlineKeyboardButton("🔔 60 min", callback_data="notify_60")
                )
                markup.add(
                    types.InlineKeyboardButton("🇺🇸 USD", callback_data="pref_USD"),
                    types.InlineKeyboardButton("🇪🇺 EUR", callback_data="pref_EUR")
                )
                markup.add(
                    types.InlineKeyboardButton("🇬🇧 GBP", callback_data="pref_GBP"),
                    types.InlineKeyboardButton("🇯🇵 JPY", callback_data="pref_JPY")
                )
                markup.add(
                    types.InlineKeyboardButton("🇨🇭 CHF", callback_data="pref_CHF"),
                    types.InlineKeyboardButton("🇦🇺 AUD", callback_data="pref_AUD")
                )
                markup.add(
                    types.InlineKeyboardButton("🇨🇦 CAD", callback_data="pref_CAD"),
                    types.InlineKeyboardButton("🇳🇿 NZD", callback_data="pref_NZD")
                )
                markup.add(types.InlineKeyboardButton("🌍 ALL", callback_data="pref_ALL"))
                
                self.bot.edit_message_text(
                    settings_text,
                    call.message.chat.id,
                    call.message.message_id,
                    parse_mode='MarkdownV2',
                    reply_markup=markup
                )
                
            except Exception as e:
                logger.error(f"Error in notification setting: {e}")
                self.bot.send_message(
                    call.message.chat.id,
                    "❌ Произошла ошибка при изменении настроек уведомлений."
                )
    
    def handle_show_preferences(self, call):
        """Handle show preferences callback."""
        # Validate callback query first
        if not self._safe_answer_callback_query(call):
            return
            
        # Redirect to preferences command
        self.preferences_command(call.message)
    
    def handle_select_currencies(self, call):
        """Handle select currencies callback."""
        # Validate callback query first
        if not self._safe_answer_callback_query(call):
            return
            
        with self.db_session_factory() as db:
            try:
                from app.services.user_service import UserService
                user_service = UserService(db)
                
                # Get current currency preferences
                current_preferences = user_service.get_user_currency_preferences(call.from_user.id)
                
                # Create currency selection keyboard
                from app.bot.keyboards import BotKeyboards
                markup = BotKeyboards.generate_currency_selection(current_preferences)
                
                # Send currency selection message
                self.bot.edit_message_text(
                    "💱 *Select Currency Preferences*\n\nChoose currencies for notifications:\n\n"
                    "✅ = Selected\n"
                    "Click currencies to toggle selection",
                    call.message.chat.id,
                    call.message.message_id,
                    parse_mode='MarkdownV2',
                    reply_markup=markup
                )
                
            except Exception as e:
                logger.error(f"Error in select currencies: {e}")
                self.bot.send_message(
                    call.message.chat.id,
                    "❌ An error occurred while loading currency selection. Please try again later."
                )
