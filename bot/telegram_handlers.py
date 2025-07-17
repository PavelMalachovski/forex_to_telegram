import logging
import asyncio
import time
import threading
from datetime import datetime, timedelta
from typing import Callable

import telebot
from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton, CallbackQuery

from .config import Config

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
            time.sleep(30)
            self.setup_webhook()
        threading.Thread(target=delayed_webhook_setup, daemon=True).start()
        logger.info("Webhook setup scheduled for 30 seconds after startup")


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
        markup.add(InlineKeyboardButton("📍 Today", callback_data=f"DAY_{today_str}"))
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
            bot.send_message(message.chat.id, "📊 Select impact level for news filtering:", reply_markup=markup)
        except Exception as e:
            logger.error("Error showing impact selection: %s", e)
            bot.send_message(message.chat.id, "❌ Error showing impact selection. Please try again.")

    @bot.message_handler(commands=["today"])
    def get_today_news(message):
        try:
            user_id = message.from_user.id
            impact_level = user_selected_impact.get(user_id, "high")
            bot.send_message(message.chat.id, "🔄 Fetching today's forex news...")

            def fetch_and_send():
                try:
                    asyncio.run(process_news(None, impact_level, False))
                except Exception as e:
                    logger.error("Error fetching today's news: %s", e)
                    bot.send_message(message.chat.id, "❌ Error fetching news. Please try again.")

            threading.Thread(target=fetch_and_send, daemon=True).start()
        except Exception as e:
            logger.error("Error in today command: %s", e)
            bot.send_message(message.chat.id, "❌ Error processing request. Please try again.")

    @bot.message_handler(commands=["help", "start"])
    def show_help(message):
        help_text = (
            "🤖 **Forex News Bot Commands:**\n\n"
            "📅 /calendar - Select a specific date for news\n"
            "📊 /impact - Choose impact level (High/Medium+)\n"
            "📰 /today - Get today's forex news\n"
            "❓ /help - Show this help message\n\n"
            "**How to use:**\n"
            "1. Use /impact to set your preferred news impact level\n"
            "2. Use /calendar to select a specific date, or /today for current news\n"
            "3. The bot will fetch and analyze forex news from ForexFactory\n\n"
            "**Impact Levels:**\n"
            "🔴 High - Only high-impact news\n"
            "🟠 Medium+ - Medium and high-impact news\n\n"
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
                impact_level = user_selected_impact.get(user_id, "high")
                bot.edit_message_text(
                    f"🔄 Fetching forex news for {date_str}...",
                    call.message.chat.id,
                    call.message.message_id,
                )

                def fetch_and_send():
                    try:
                        target_date = datetime.strptime(date_str, "%Y-%m-%d")
                        asyncio.run(process_news(target_date, impact_level, False))
                    except Exception as e:
                        logger.error("Error fetching news for %s: %s", date_str, e)
                        bot.send_message(call.message.chat.id, "❌ Error fetching news. Please try again.")

                threading.Thread(target=fetch_and_send, daemon=True).start()
            elif data.startswith("IMPACT_"):
                impact_level = data[7:]
                user_selected_impact[user_id] = impact_level
                impact_text = "🔴 High Impact" if impact_level == "high" else "🟠 Medium+ Impact"
                bot.edit_message_text(
                    f"✅ Impact level set to: {impact_text}\n\nUse /calendar to select a date or /today for current news.",
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
