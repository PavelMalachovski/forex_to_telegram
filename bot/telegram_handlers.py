import logging
import asyncio
import time
import threading
from datetime import datetime, timedelta, date
from typing import Callable

import telebot
from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton, CallbackQuery

from .config import Config
from .database import get_db_manager
from .scraper import scrape_and_send_forex_data

logger = logging.getLogger(__name__)


class TelegramBotManager:
    """Manages Telegram bot initialization and webhook setup."""

    def __init__(self, config: Config):
        self.config = config
        self.bot = None
        self._initialize_bot()

    def _initialize_bot(self):
        if not self.config.telegram_bot_token:
            logger.error("TELEGRAM_BOT_TOKEN is not set. Bot functionality will be disabled.")
            return
        try:
            self.bot = telebot.TeleBot(self.config.telegram_bot_token)
            logger.info("Telegram bot initialized successfully")
        except Exception as e:
            logger.error("Failed to initialize Telegram bot: %s", e)

    def setup_webhook(self, max_retries: int = 5, initial_delay: int = 10):
        if not self.bot:
            logger.warning("Cannot set webhook: Bot not initialized")
            return False
        if not self.config.render_hostname:
            logger.warning("Cannot set webhook: RENDER_EXTERNAL_HOSTNAME not set")
            return False
        webhook_url = f"https://{self.config.render_hostname}/webhook"
        for attempt in range(max_retries):
            try:
                logger.info("Setting webhook attempt %s/%s to %s", attempt + 1, max_retries, webhook_url)
                self.bot.remove_webhook()
                time.sleep(2)
                result = self.bot.set_webhook(url=webhook_url)
                if result:
                    logger.info("Webhook successfully configured")
                    return True
                logger.warning("Webhook setup returned False on attempt %s", attempt + 1)
            except Exception as e:
                logger.error("Failed to set webhook on attempt %s: %s", attempt + 1, e)
                if attempt < max_retries - 1:
                    delay = initial_delay * (2 ** attempt)
                    logger.info("Retrying webhook setup in %s seconds...", delay)
                    time.sleep(delay)
                else:
                    logger.error("All webhook setup attempts failed")
        return False

    def setup_webhook_async(self):
        def delayed_webhook_setup():
            # Reduced delay for faster deployment readiness
            time.sleep(10)
            self.setup_webhook()
        threading.Thread(target=delayed_webhook_setup, daemon=True).start()
        logger.info("Webhook setup scheduled for 10 seconds after startup")


class RenderKeepAlive:
    """Manages self-ping functionality to prevent Render.com app from sleeping."""

    def __init__(self, config: Config):
        self.config = config
        self.scheduler = None
        self._setup_scheduler()

    def _setup_scheduler(self):
        from apscheduler.schedulers.background import BackgroundScheduler

        if not self.config.render_hostname:
            logger.warning("RENDER_EXTERNAL_HOSTNAME not set, skipping self-ping")
            return
        self.scheduler = BackgroundScheduler()
        self.scheduler.add_job(self._ping_self, 'interval', minutes=5)
        self.scheduler.start()
        logger.info("Started APScheduler for self-ping every 5 minutes")

    def _ping_self(self):
        import requests

        try:
            ping_url = f"https://{self.config.render_hostname}/ping"
            response = requests.get(ping_url, timeout=10)
            if response.status_code == 200:
                logger.info("Ping successful: %s", ping_url)
            else:
                logger.error("Ping failed: %s status code: %s", ping_url, response.status_code)
        except Exception as e:
            logger.error("Ping error: %s", e)


class TelegramHandlers:
    """Utility methods for Telegram calendar markup."""

    @staticmethod
    def generate_calendar(year: int, month: int) -> InlineKeyboardMarkup:
        markup = InlineKeyboardMarkup(row_width=7)
        weekdays = ["Mo", "Tu", "We", "Th", "Fr", "Sa", "Su"]
        markup.add(*[InlineKeyboardButton(d, callback_data="IGNORE") for d in weekdays])
        first_day = datetime(year, month, 1)
        start_day = first_day.weekday()
        days = []
        for _ in range(start_day):
            days.append(InlineKeyboardButton(" ", callback_data="IGNORE"))
        next_month = first_day.replace(day=28) + timedelta(days=4)
        days_in_month = (next_month - timedelta(days=next_month.day)).day
        for day in range(1, days_in_month + 1):
            date_str = f"{year}-{month:02d}-{day:02d}"
            days.append(InlineKeyboardButton(str(day), callback_data=f"DAY_{date_str}"))
        while len(days) % 7 != 0:
            days.append(InlineKeyboardButton(" ", callback_data="IGNORE"))
        for i in range(0, len(days), 7):
            markup.row(*days[i:i+7])
        nav_buttons = [
            InlineKeyboardButton("<", callback_data=f"PREV_{year}-{month}"),
            InlineKeyboardButton(f"{first_day.strftime('%B')} {year}", callback_data="IGNORE"),
            InlineKeyboardButton(">", callback_data=f"NEXT_{year}-{month}")
        ]
        markup.row(*nav_buttons)
        today_str = datetime.today().strftime('%Y-%m-%d')
        tomorrow_str = (datetime.today() + timedelta(days=1)).strftime('%Y-%m-%d')
        markup.add(
            InlineKeyboardButton("📍 Today", callback_data=f"DAY_{today_str}"),
            InlineKeyboardButton("🔜 Tomorrow", callback_data=f"DAY_{tomorrow_str}")
        )
        return markup


user_selected_date = {}
user_selected_impact = {}


def register_handlers(bot, process_news: Callable, config: Config):
    @bot.message_handler(commands=["calendar"])
    def show_calendar(message):
        try:
            today = datetime.today()
            markup = TelegramHandlers.generate_calendar(today.year, today.month)
            bot.send_message(message.chat.id, "📅 Select a date for forex news:", reply_markup=markup)
        except Exception as e:
            logger.error("Error showing calendar: %s", e)
            bot.send_message(message.chat.id, "❌ Error showing calendar. Please try again.")

    @bot.message_handler(commands=["impact"])
    def select_impact(message):
        try:
            markup = InlineKeyboardMarkup()
            markup.add(
                InlineKeyboardButton("🔴 High Impact", callback_data="IMPACT_high"),
                InlineKeyboardButton("🟠 Medium+ Impact", callback_data="IMPACT_medium"),
            )
            markup.add(
                InlineKeyboardButton("🟡 Low Impact", callback_data="IMPACT_low"),
                InlineKeyboardButton("🌈 All Impact", callback_data="IMPACT_all"),
            )
            bot.send_message(message.chat.id, "📊 Select impact level for news filtering:", reply_markup=markup)
        except Exception as e:
            logger.error("Error showing impact selection: %s", e)
            bot.send_message(message.chat.id, "❌ Error showing impact selection. Please try again.")

    @bot.message_handler(commands=["today"])
    def get_today_news(message):
        try:
            bot.send_message(message.chat.id, "🔄 Fetching today's forex news...")

            def fetch_and_send():
                try:
                    today = date.today()
                    scrape_and_send_forex_data(today, today)
                except Exception as e:
                    logger.error("Error fetching today's news: %s", e)
                    bot.send_message(message.chat.id, "❌ Error fetching news. Please try again.")

            threading.Thread(target=fetch_and_send, daemon=True).start()
        except Exception as e:
            logger.error("Error in today command: %s", e)
            bot.send_message(message.chat.id, "❌ Error processing request. Please try again.")

    @bot.message_handler(commands=["tomorrow"])
    def get_tomorrow_news(message):
        try:
            bot.send_message(message.chat.id, "🔄 Fetching tomorrow's forex news...")

            def fetch_and_send():
                try:
                    tomorrow = date.today() + timedelta(days=1)
                    scrape_and_send_forex_data(tomorrow, tomorrow)
                except Exception as e:
                    logger.error("Error fetching tomorrow's news: %s", e)
                    bot.send_message(message.chat.id, "❌ Error fetching news. Please try again.")

            threading.Thread(target=fetch_and_send, daemon=True).start()
        except Exception as e:
            logger.error("Error in tomorrow command: %s", e)
            bot.send_message(message.chat.id, "❌ Error processing request. Please try again.")

    @bot.message_handler(commands=["help", "start"])
    def show_help(message):
        help_text = (
            "🤖 **Forex News Bot Commands:**\n\n"
            "📅 /calendar - Select a specific date for news\n"
            "📊 /impact - Choose impact level (High/Medium+/Low/All)\n"
            "📰 /today - Get today's forex news\n"
            "🔜 /tomorrow - Get tomorrow's forex news\n"
            "❓ /help - Show this help message\n\n"
            "**How to use:**\n"
            "1. Use /impact to set your preferred news impact level\n"
            "2. Use /calendar to select a specific date, /today for current news, or /tomorrow for next day\n"
            "3. The bot will fetch and analyze forex news from ForexFactory\n\n"
            "**Impact Levels:**\n"
            "🔴 High - Only high-impact news\n"
            "🟠 Medium+ - Medium and high-impact news\n"
            "🟡 Low - Only low-impact news\n"
            "🌈 All - All impact levels\n\n"
            "**Note:** News analysis is powered by ChatGPT for market insights."
        )
        try:
            bot.send_message(message.chat.id, help_text, parse_mode='Markdown')
        except Exception as e:
            logger.error("Error sending help message: %s", e)
            plain_help = help_text.replace('*', '').replace('`', '')
            bot.send_message(message.chat.id, plain_help)

    @bot.callback_query_handler(func=lambda call: True)
    def handle_callback(call: CallbackQuery):
        try:
            user_id = call.from_user.id
            data = call.data
            if data == "IGNORE":
                bot.answer_callback_query(call.id)
                return
            if data.startswith("DAY_"):
                date_str = data[4:]
                user_selected_date[user_id] = date_str
                bot.edit_message_text(
                    f"🔄 Fetching forex news for {date_str}...",
                    call.message.chat.id,
                    call.message.message_id,
                )

                def fetch_and_send():
                    try:
                        target_date = datetime.strptime(date_str, "%Y-%m-%d").date()
                        scrape_and_send_forex_data(target_date, target_date)
                    except Exception as e:
                        logger.error("Error fetching news for %s: %s", date_str, e)
                        bot.send_message(call.message.chat.id, "❌ Error fetching news. Please try again.")

                threading.Thread(target=fetch_and_send, daemon=True).start()
            elif data.startswith("IMPACT_"):
                impact_level = data[7:]
                user_selected_impact[user_id] = impact_level
                impact_text_map = {
                    "high": "🔴 High Impact",
                    "medium": "🟠 Medium+ Impact", 
                    "low": "🟡 Low Impact",
                    "all": "🌈 All Impact"
                }
                impact_text = impact_text_map.get(impact_level, "🔴 High Impact")
                bot.edit_message_text(
                    f"✅ Impact level set to: {impact_text}\n\nUse /calendar to select a date, /today for current news, or /tomorrow for next day.",
                    call.message.chat.id,
                    call.message.message_id,
                )
            elif data.startswith("PREV_") or data.startswith("NEXT_"):
                direction, date_part = data.split("_", 1)
                year, month = map(int, date_part.split("-"))
                if direction == "PREV":
                    if month == 1:
                        year -= 1
                        month = 12
                    else:
                        month -= 1
                else:
                    if month == 12:
                        year += 1
                        month = 1
                    else:
                        month += 1
                markup = TelegramHandlers.generate_calendar(year, month)
                bot.edit_message_reply_markup(
                    call.message.chat.id,
                    call.message.message_id,
                    reply_markup=markup,
                )
            bot.answer_callback_query(call.id)
        except Exception as e:
            logger.error("Error handling callback %s: %s", call.data, e)
            bot.answer_callback_query(call.id)


# Global bot instance
_bot_instance = None

def get_bot():
    """Get the global bot instance"""
    global _bot_instance
    if _bot_instance is None:
        config = Config()
        bot_manager = TelegramBotManager(config)
        _bot_instance = bot_manager.bot
    return _bot_instance

def initialize_bot_with_scheduler():
    """Initialize bot and start scheduler"""
    from .scheduler import start_scheduler
    
    config = Config()
    bot_manager = TelegramBotManager(config)
    
    if bot_manager.bot:
        # Register handlers with the new database-integrated functions
        register_handlers(bot_manager.bot, None, config)  # process_news not needed anymore
        
        # Start the scheduler for daily scraping
        start_scheduler()
        
        # Setup webhook
        bot_manager.setup_webhook_async()
        
        # Setup keep-alive
        keep_alive = RenderKeepAlive(config)
        
        global _bot_instance
        _bot_instance = bot_manager.bot
        
        return bot_manager.bot
    else:
        logger.error("Failed to initialize bot")
        return None
