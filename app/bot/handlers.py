
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
from app.utils.text_utils import escape_markdown, format_news_event_message
from app.utils.timezone_utils import get_current_time
from app.bot.utils.calendar import create_calendar, process_calendar_callback

logger = logging.getLogger(__name__)

class BotHandlers:
    """Telegram bot handlers."""
    
    def __init__(self, bot: telebot.TeleBot, db_session_factory):
        self.bot = bot
        self.db_session_factory = db_session_factory
        self._register_handlers()
    
    def _get_db_session(self):
        """Get database session with proper error handling."""
        try:
            if not self.db_session_factory:
                logger.warning("Database session factory not available")
                return None
            return self.db_session_factory()
        except Exception as e:
            logger.error(f"Failed to create database session: {e}")
            return None
    
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
        try:
            db = self._get_db_session()
            if db is None:
                # Database unavailable - send basic welcome message
                welcome_text = (
                    f"👋 Welcome to Forex News Bot, {escape_markdown(message.from_user.first_name or 'User')}\\!\n\n"
                    f"⚠️ *Database temporarily unavailable*\n"
                    f"Some features may be limited\\.\n\n"
                    f"🔹 Get the latest forex news and economic events\n"
                    f"🔹 Filter by impact level and currency\n\n"
                    f"Use /help to see all available commands\\."
                )
                
                self.bot.send_message(
                    message.chat.id,
                    welcome_text,
                    parse_mode='MarkdownV2'
                )
                return
            
            try:
                user_service = UserService(db)
                
                # Create or get user
                user = user_service.create_or_get_user(
                    telegram_user_id=message.from_user.id,
                    username=message.from_user.username,
                    first_name=message.from_user.first_name,
                    last_name=message.from_user.last_name
                )
                
                if not user:
                    raise Exception("Failed to create or get user")
                
                welcome_text = (
                    f"👋 Welcome to Forex News Bot, {escape_markdown(user.first_name or 'User')}\\!\n\n"
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
            finally:
                if db:
                    db.close()
                
        except Exception as e:
            logger.error(f"Error in start command: {e}")
            self.bot.send_message(
                message.chat.id,
                "❌ Произошла ошибка при инициализации. Попробуйте позже или обратитесь к администратору."
            )
    
    def help_command(self, message):
        """Handle /help command."""
        try:
            help_text = escape_markdown(
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
        
        db = self._get_db_session()
        if db is None:
            self.bot.send_message(
                message.chat.id,
                "❌ База данных временно недоступна. Попробуйте позже."
            )
            return
        
        try:
            # Parse command arguments
            args = message.text.split()[1:] if len(message.text.split()) > 1 else []
            
            if not args:
                # Show impact level selection
                markup = types.InlineKeyboardMarkup(row_width=3)
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
                text=f"🔄 Fetching Forex news for *{escape_markdown(date_str)}*\nImpact: *{escape_markdown(impact_level)}*",
                parse_mode='MarkdownV2'
            )
            
            news_service = NewsService(db)
            
            # Check if data exists, if not - trigger auto-scraping
            if not news_service.has_data_for_date(target_date):
                # Update loading message to indicate scraping
                self.bot.edit_message_text(
                    f"🔄 No data found for *{escape_markdown(date_str)}*\\.\n🌐 Scraping data from ForexFactory\\.\\.\\.\n⏳ This may take a moment\\.",
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
            try:
                self.bot.delete_message(message.chat.id, loading_msg.message_id)
            except:
                pass
            
            if news_events:
                # Format and send message
                formatted_message = format_news_event_message(news_events, date_str, impact_level)
                
                # Add scraping notification if data was scraped
                if was_scraped:
                    scraping_notice = "🌐 *Data scraped from ForexFactory*\n\n"
                    formatted_message = scraping_notice + formatted_message
                
                # Send message using notification service for long messages
                try:
                    from app.services.notification_service import NotificationService
                    notification_service = NotificationService(db, self.bot)
                    if notification_service:
                        notification_service.send_long_message(message.chat.id, formatted_message)
                    else:
                        # Fallback to direct bot message
                        self.bot.send_message(message.chat.id, formatted_message, parse_mode='MarkdownV2')
                except Exception as e:
                    logger.error(f"Error sending message via notification service: {e}")
                    # Fallback to direct bot message
                    self.bot.send_message(message.chat.id, formatted_message, parse_mode='MarkdownV2')
            else:
                scraping_status = "scraped from ForexFactory" if was_scraped else "found in database"
                self.bot.send_message(
                    message.chat.id,
                    f"✅ No news {scraping_status} for {escape_markdown(date_str)} with impact: {escape_markdown(impact_level)}\\.\nPlease check the website for updates\\.",
                    parse_mode='MarkdownV2'
                )
            
        except Exception as e:
            logger.error(f"Error in news command: {e}")
            self.bot.send_message(
                message.chat.id,
                "❌ An error occurred while fetching news. Please try again later."
            )
        finally:
            if db:
                db.close()
    
    def today_command(self, message):
        """Handle /today command."""
        import asyncio
        
        db = self._get_db_session()
        if db is None:
            self.bot.send_message(
                message.chat.id,
                "❌ База данных временно недоступна. Попробуйте позже."
            )
            return
        
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
            try:
                self.bot.delete_message(message.chat.id, loading_msg.message_id)
            except:
                pass
            
            if news_events:
                # Format and send message
                formatted_message = format_news_event_message(news_events, today.strftime('%Y-%m-%d'))
                
                # Add scraping notification if data was scraped
                if was_scraped:
                    scraping_notice = "🌐 *Data scraped from ForexFactory*\n\n"
                    formatted_message = scraping_notice + formatted_message
                
                # Send message using notification service for long messages
                try:
                    from app.services.notification_service import NotificationService
                    notification_service = NotificationService(db, self.bot)
                    if notification_service:
                        notification_service.send_long_message(message.chat.id, formatted_message)
                    else:
                        # Fallback to direct bot message
                        self.bot.send_message(message.chat.id, formatted_message, parse_mode='MarkdownV2')
                except Exception as e:
                    logger.error(f"Error sending message via notification service: {e}")
                    # Fallback to direct bot message
                    self.bot.send_message(message.chat.id, formatted_message, parse_mode='MarkdownV2')
            else:
                scraping_status = "scraped from ForexFactory" if was_scraped else "found in database"
                self.bot.send_message(
                    message.chat.id,
                    f"✅ No high\\-impact news {scraping_status} for today \\({escape_markdown(today.strftime('%d.%m.%Y'))}\\)\\.\nPlease check the website for updates\\.",
                    parse_mode='MarkdownV2'
                )
            
        except Exception as e:
            logger.error(f"Error in today command: {e}")
            self.bot.send_message(
                message.chat.id,
                "❌ Произошла ошибка при получении новостей на сегодня. Попробуйте позже."
            )
        finally:
            if db:
                db.close()
    
    def tomorrow_command(self, message):
        """Handle /tomorrow command."""
        import asyncio
        
        db = self._get_db_session()
        if db is None:
            self.bot.send_message(
                message.chat.id,
                "❌ База данных временно недоступна. Попробуйте позже."
            )
            return
        
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
            try:
                self.bot.delete_message(message.chat.id, loading_msg.message_id)
            except:
                pass
            
            if news_events:
                # Format and send message
                formatted_message = format_news_event_message(news_events, tomorrow.strftime('%Y-%m-%d'))
                
                # Add scraping notification if data was scraped
                if was_scraped:
                    scraping_notice = "🌐 *Data scraped from ForexFactory*\n\n"
                    formatted_message = scraping_notice + formatted_message
                
                # Send message using notification service for long messages
                try:
                    from app.services.notification_service import NotificationService
                    notification_service = NotificationService(db, self.bot)
                    if notification_service:
                        notification_service.send_long_message(message.chat.id, formatted_message)
                    else:
                        # Fallback to direct bot message
                        self.bot.send_message(message.chat.id, formatted_message, parse_mode='MarkdownV2')
                except Exception as e:
                    logger.error(f"Error sending message via notification service: {e}")
                    # Fallback to direct bot message
                    self.bot.send_message(message.chat.id, formatted_message, parse_mode='MarkdownV2')
            else:
                scraping_status = "scraped from ForexFactory" if was_scraped else "found in database"
                self.bot.send_message(
                    message.chat.id,
                    f"✅ No high\\-impact news {scraping_status} for tomorrow \\({escape_markdown(tomorrow.strftime('%d.%m.%Y'))}\\)\\.\nPlease check the website for updates\\.",
                    parse_mode='MarkdownV2'
                )
            
        except Exception as e:
            logger.error(f"Error in tomorrow command: {e}")
            self.bot.send_message(
                message.chat.id,
                "❌ Произошла ошибка при получении новостей на завтра. Попробуйте позже."
            )
        finally:
            if db:
                db.close()
    
    def week_command(self, message):
        """Handle /week command."""
        db = self._get_db_session()
        if db is None:
            self.bot.send_message(
                message.chat.id,
                "❌ База данных временно недоступна. Попробуйте позже."
            )
            return
        
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
                    formatted_message = format_news_event_message(events, date_str)
                    
                    # Send message using notification service for long messages
                    try:
                        from app.services.notification_service import NotificationService
                        notification_service = NotificationService(db, self.bot)
                        if notification_service:
                            notification_service.send_long_message(message.chat.id, formatted_message)
                        else:
                            # Fallback to direct bot message
                            self.bot.send_message(message.chat.id, formatted_message, parse_mode='MarkdownV2')
                    except Exception as e:
                        logger.error(f"Error sending message via notification service: {e}")
                        # Fallback to direct bot message
                        self.bot.send_message(message.chat.id, formatted_message, parse_mode='MarkdownV2')
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
                "❌ Произошла ошибка при получении новостей на неделю. Попробуйте позже."
            )
        finally:
            if db:
                db.close()
    
    def preferences_command(self, message):
        """Handle /preferences command."""
        db = self._get_db_session()
        if db is None:
            self.bot.send_message(
                message.chat.id,
                "❌ База данных временно недоступна. Настройки недоступны."
            )
            return
        
        try:
            user_service = UserService(db)
            # Создаем пользователя если он не существует
            user = user_service.create_or_get_user(
                telegram_user_id=message.from_user.id,
                username=message.from_user.username,
                first_name=message.from_user.first_name,
                last_name=message.from_user.last_name
            )
            
            if not user:
                raise Exception("Failed to create or get user")
        
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
                f"💱 Currency preferences: {escape_markdown(currency_display)}\n\n"
                f"Choose options to modify:"
            )
            
            markup = types.InlineKeyboardMarkup(row_width=2)
            markup.add(
                types.InlineKeyboardButton("🔔 15 min", callback_data="notify_15"),
                types.InlineKeyboardButton("🔔 30 min", callback_data="notify_30"),
                types.InlineKeyboardButton("🔔 60 min", callback_data="notify_60")
            )
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
                "❌ Произошла ошибка при загрузке настроек. Попробуйте позже."
            )
        finally:
            if db:
                db.close()
    
    def status_command(self, message):
        """Handle /status command."""
        db = self._get_db_session()
        if db is None:
            self.bot.send_message(
                message.chat.id,
                "❌ База данных временно недоступна. Статус недоступен."
            )
            return
        
        try:
            user_service = UserService(db)
            # Создаем пользователя если он не существует
            user = user_service.create_or_get_user(
                telegram_user_id=message.from_user.id,
                username=message.from_user.username,
                first_name=message.from_user.first_name,
                last_name=message.from_user.last_name
            )
            
            if not user:
                raise Exception("Failed to create or get user")
        
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
                f"🆔 ID: {escape_markdown(str(user.telegram_user_id))}\n"
                f"👤 Name: {escape_markdown(user.first_name or 'N/A')}\n"
                f"🏷️ Username: {escape_markdown(user.telegram_username or 'N/A')}\n"
                f"🌐 Language: {escape_markdown(user.language_code or 'N/A')}\n"
                f"✅ Active: {'Yes' if user.is_active else 'No'}\n"
                f"📅 Registered: {escape_markdown(user.created_at.strftime('%d.%m.%Y %H:%M'))}\n"
                f"🕐 Last Activity: {escape_markdown(user.last_activity.strftime('%d.%m.%Y %H:%M') if user.last_activity else 'N/A')}\n\n"
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
                "❌ Произошла ошибка при получении статуса. Попробуйте позже."
            )
        finally:
            if db:
                db.close()
    
    def calendar_command(self, message):
        """Handle /calendar command."""
        try:
            # Create calendar markup
            markup = create_calendar()
            
            self.bot.send_message(
                message.chat.id,
                "📅 Select a date:",
                reply_markup=markup
            )
            
        except Exception as e:
            logger.error(f"Error in calendar command: {e}")
            self.bot.send_message(
                message.chat.id,
                "❌ An error occurred while creating calendar. Please try again later."
            )
    
    # Callback handlers with proper error handling
    def handle_impact_selection(self, call):
        """Handle impact level selection."""
        import asyncio
        
        # Validate callback query first
        if not self._safe_answer_callback_query(call):
            return
        
        db = self._get_db_session()
        if db is None:
            self.bot.send_message(
                call.message.chat.id,
                "❌ База данных временно недоступна. Попробуйте позже."
            )
            return
        
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
            try:
                self.bot.delete_message(call.message.chat.id, call.message.message_id)
            except:
                pass
            
            if news_events:
                # Format and send message
                formatted_message = format_news_event_message(news_events, today.strftime('%Y-%m-%d'), impact_level)
                
                # Add scraping notification if data was scraped
                if was_scraped:
                    scraping_notice = "🌐 *Data scraped from ForexFactory*\n\n"
                    formatted_message = scraping_notice + formatted_message
                
                # Send message using notification service for long messages
                try:
                    from app.services.notification_service import NotificationService
                    notification_service = NotificationService(db, self.bot)
                    if notification_service:
                        notification_service.send_long_message(call.message.chat.id, formatted_message)
                    else:
                        # Fallback to direct bot message
                        self.bot.send_message(call.message.chat.id, formatted_message, parse_mode='MarkdownV2')
                except Exception as e:
                    logger.error(f"Error sending message via notification service: {e}")
                    # Fallback to direct bot message
                    self.bot.send_message(call.message.chat.id, formatted_message, parse_mode='MarkdownV2')
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
        finally:
            if db:
                db.close()
    
    def handle_currency_selection(self, call):
        """Handle currency selection with multiple selection support."""
        # Validate callback query first
        if not self._safe_answer_callback_query(call):
            return
        
        db = self._get_db_session()
        if db is None:
            self.bot.send_message(
                call.message.chat.id,
                "❌ База данных временно недоступна. Попробуйте позже."
            )
            return
            
        try:
            user_service = UserService(db)
            
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
                try:
                    from app.bot.keyboards import BotKeyboards
                    new_markup = BotKeyboards.generate_currency_selection(current_preferences)
                    
                    self.bot.edit_message_reply_markup(
                        call.message.chat.id,
                        call.message.message_id,
                        reply_markup=new_markup
                    )
                except ImportError:
                    # Fallback if keyboards module not available
                    self.bot.send_message(
                        call.message.chat.id,
                        f"Currency preference updated: {currency_code}"
                    )
                
            elif call.data == 'currency_select_all':
                # Select all currencies
                try:
                    from app.config import config
                    available_currencies = getattr(config, 'AVAILABLE_CURRENCIES', ['USD', 'EUR', 'GBP', 'JPY', 'AUD', 'CAD', 'CHF', 'NZD'])
                    user_service.set_user_currency_preferences(call.from_user.id, available_currencies)
                    
                    from app.bot.keyboards import BotKeyboards
                    new_markup = BotKeyboards.generate_currency_selection(available_currencies)
                    
                    self.bot.edit_message_reply_markup(
                        call.message.chat.id,
                        call.message.message_id,
                        reply_markup=new_markup
                    )
                except ImportError:
                    # Fallback if config or keyboards module not available
                    self.bot.send_message(
                        call.message.chat.id,
                        "All currencies selected"
                    )
                
            elif call.data == 'currency_clear_all':
                # Clear all currencies
                user_service.set_user_currency_preferences(call.from_user.id, [])
                
                try:
                    from app.bot.keyboards import BotKeyboards
                    new_markup = BotKeyboards.generate_currency_selection([])
                    
                    self.bot.edit_message_reply_markup(
                        call.message.chat.id,
                        call.message.message_id,
                        reply_markup=new_markup
                    )
                except ImportError:
                    # Fallback if keyboards module not available
                    self.bot.send_message(
                        call.message.chat.id,
                        "All currency preferences cleared"
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
        finally:
            if db:
                db.close()
    
    def handle_preference_selection(self, call):
        """Handle preference selection."""
        # Validate callback query first
        if not self._safe_answer_callback_query(call):
            return
        
        # Implementation for preference selection
        self.bot.send_message(
            call.message.chat.id,
            "Preference selection feature coming soon!"
        )
    
    def handle_calendar_callback(self, call):
        """Handle calendar callback."""
        # Validate callback query first
        if not self._safe_answer_callback_query(call):
            return
        
        try:
            logger.info(f"Processing calendar callback: {call.data}")
            result = process_calendar_callback(call.data)
            logger.info(f"Calendar callback result: {result}")
            
            if result and len(result) >= 2:
                action, selected_date, nav_data = result
                
                if action == "select" and selected_date:
                    # Handle the selected date
                    self.bot.send_message(
                        call.message.chat.id,
                        f"You selected: {selected_date}"
                    )
                elif action == "navigate" and nav_data:
                    # Handle navigation - recreate calendar for new month
                    from app.bot.utils.calendar import create_calendar
                    new_calendar = create_calendar(nav_data['year'], nav_data['month'])
                    self.bot.edit_message_reply_markup(
                        chat_id=call.message.chat.id,
                        message_id=call.message.message_id,
                        reply_markup=new_calendar
                    )
                # Ignore other actions
            else:
                logger.warning(f"Invalid calendar callback result: {result}")
                
        except Exception as e:
            logger.error(f"Error in calendar callback: {e}", exc_info=True)
            self.bot.send_message(
                call.message.chat.id,
                "❌ An error occurred while processing calendar selection."
            )
    
    def handle_date_impact_selection(self, call):
        """Handle date impact selection."""
        # Validate callback query first
        if not self._safe_answer_callback_query(call):
            return
        
        # Implementation for date impact selection
        self.bot.send_message(
            call.message.chat.id,
            "Date impact selection feature coming soon!"
        )
    
    def handle_notification_setting(self, call):
        """Handle notification setting."""
        # Validate callback query first
        if not self._safe_answer_callback_query(call):
            return
        
        db = self._get_db_session()
        if db is None:
            self.bot.send_message(
                call.message.chat.id,
                "❌ База данных временно недоступна. Попробуйте позже."
            )
            return
        
        try:
            user_service = UserService(db)
            
            # Create or get user
            user = user_service.create_or_get_user(
                telegram_user_id=call.from_user.id,
                username=call.from_user.username,
                first_name=call.from_user.first_name,
                last_name=call.from_user.last_name
            )
            
            if not user:
                raise Exception("Failed to create or get user")
            
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
            
            # Update settings based on callback data
            if call.data == 'notify_15':
                notification_settings.notify_15_minutes = not notification_settings.notify_15_minutes
                status = "enabled" if notification_settings.notify_15_minutes else "disabled"
                message = f"✅ 15-minute notifications {status}"
            elif call.data == 'notify_30':
                notification_settings.notify_30_minutes = not notification_settings.notify_30_minutes
                status = "enabled" if notification_settings.notify_30_minutes else "disabled"
                message = f"✅ 30-minute notifications {status}"
            elif call.data == 'notify_60':
                notification_settings.notify_60_minutes = not notification_settings.notify_60_minutes
                status = "enabled" if notification_settings.notify_60_minutes else "disabled"
                message = f"✅ 60-minute notifications {status}"
            else:
                message = "❌ Unknown notification setting"
            
            db.commit()
            
            self.bot.edit_message_text(
                message,
                call.message.chat.id,
                call.message.message_id
            )
            
        except Exception as e:
            logger.error(f"Error in notification setting: {e}")
            self.bot.send_message(
                call.message.chat.id,
                "❌ An error occurred while updating notification settings."
            )
        finally:
            if db:
                db.close()
    
    def handle_show_preferences(self, call):
        """Handle show preferences."""
        # Validate callback query first
        if not self._safe_answer_callback_query(call):
            return
        
        # Redirect to preferences command
        self.preferences_command(call.message)
    
    def handle_select_currencies(self, call):
        """Handle select currencies."""
        # Validate callback query first
        if not self._safe_answer_callback_query(call):
            return
        
        db = self._get_db_session()
        if db is None:
            self.bot.send_message(
                call.message.chat.id,
                "❌ База данных временно недоступна. Попробуйте позже."
            )
            return
        
        try:
            user_service = UserService(db)
            current_preferences = user_service.get_user_currency_preferences(call.from_user.id)
            
            # Create currency selection keyboard
            try:
                from app.bot.keyboards import BotKeyboards
                markup = BotKeyboards.generate_currency_selection(current_preferences)
                
                self.bot.edit_message_text(
                    "💱 Select your preferred currencies:",
                    call.message.chat.id,
                    call.message.message_id,
                    reply_markup=markup
                )
            except ImportError:
                # Fallback if keyboards module not available
                self.bot.edit_message_text(
                    "Currency selection feature is temporarily unavailable.",
                    call.message.chat.id,
                    call.message.message_id
                )
            
        except Exception as e:
            logger.error(f"Error in select currencies: {e}")
            self.bot.send_message(
                call.message.chat.id,
                "❌ An error occurred while loading currency selection."
            )
        finally:
            if db:
                db.close()
