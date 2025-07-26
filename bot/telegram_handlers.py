import logging
import asyncio
import time
import threading
from datetime import datetime, timedelta, date as dt_date
from typing import Callable

import telebot
from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton, CallbackQuery
from calendar import monthrange, month_name

from .config import Config
from bot.utils import escape_markdown_v2
from .scraper import ForexNewsScraper
from .user_settings import UserSettingsHandler

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

        # Header with month/year
        first_day = datetime(year, month, 1)
        markup.add(InlineKeyboardButton(f"{first_day.strftime('%B')} {year}", callback_data="IGNORE"))

        # Weekday headers
        weekdays = ["Mo", "Tu", "We", "Th", "Fr", "Sa", "Su"]
        markup.add(*[InlineKeyboardButton(d, callback_data="IGNORE") for d in weekdays])

        # Calculate calendar days
        first_weekday = first_day.weekday()
        days = []

        # Add empty cells for days before the first day of the month
        for _ in range(first_weekday):
            days.append(InlineKeyboardButton(" ", callback_data="IGNORE"))

        # Add all days of the month
        next_month = first_day.replace(day=28) + timedelta(days=4)
        days_in_month = (next_month - timedelta(days=next_month.day)).day

        today = datetime.now().date()

        for day in range(1, days_in_month + 1):
            date_str = f"{year}-{month:02d}-{day:02d}"
            current_date = datetime(year, month, day).date()

            # Highlight today
            if current_date == today:
                days.append(InlineKeyboardButton(f"📍{day}", callback_data=f"pickdate_{year}_{month}_{day}"))
            else:
                days.append(InlineKeyboardButton(str(day), callback_data=f"pickdate_{year}_{month}_{day}"))

        # Fill remaining cells to complete the week
        while len(days) % 7 != 0:
            days.append(InlineKeyboardButton(" ", callback_data="IGNORE"))

        # Add days in rows
        for i in range(0, len(days), 7):
            markup.row(*days[i:i+7])

        # Navigation buttons
        prev_month = (month - 1) or 12
        prev_year = year - 1 if month == 1 else year
        next_month = (month + 1) if month < 12 else 1
        next_year = year + 1 if month == 12 else year

        nav_buttons = [
            InlineKeyboardButton("⬅️", callback_data=f"cal_{prev_year}_{prev_month}"),
            InlineKeyboardButton("📍 Today", callback_data="pickdate_today"),
            InlineKeyboardButton("➡️", callback_data=f"cal_{next_year}_{next_month}")
        ]
        markup.row(*nav_buttons)

        # Quick access buttons
        today_str = datetime.today().strftime('%Y-%m-%d')
        tomorrow_str = (datetime.today() + timedelta(days=1)).strftime('%Y-%m-%d')
        yesterday_str = (datetime.today() - timedelta(days=1)).strftime('%Y-%m-%d')

        quick_buttons = [
            InlineKeyboardButton("📅 Yesterday", callback_data=f"pickdate_{yesterday_str.replace('-', '_')}"),
            InlineKeyboardButton("📅 Tomorrow", callback_data=f"pickdate_{tomorrow_str.replace('-', '_')}")
        ]
        markup.row(*quick_buttons)

        return markup

    @staticmethod
    def filter_news_by_impact(news_items, impact_level):
        if impact_level == 'all':
            return news_items
        return [item for item in news_items if item.get('impact') == impact_level]


user_selected_date = {}
user_selected_impact = {}
user_analysis_required = {}  # NEW: Store per-user analysis preference


def register_handlers(bot, process_news_func, config: Config, db_service=None, digest_scheduler=None):
    """Register all bot handlers."""
    from .user_settings import UserSettingsHandler

    # Initialize user state dictionary for storing user selections
    user_state = {}

    # Initialize settings handler if db_service is available
    settings_handler = None
    if db_service:
        settings_handler = UserSettingsHandler(db_service, digest_scheduler)

    @bot.message_handler(commands=["start", "help"])
    def send_welcome(message):
        help_text = get_help_text()
        bot.reply_to(message, help_text, parse_mode="HTML")

    @bot.message_handler(commands=["settings"])
    def show_settings(message):
        if not settings_handler:
            bot.reply_to(message, "❌ Settings not available. Database connection required.")
            return

        markup = settings_handler.get_settings_keyboard(message.from_user.id)
        bot.reply_to(message, "⚙️ Your Settings:", reply_markup=markup)

    @bot.callback_query_handler(func=lambda call: True)
    def handle_callback(call):
        # Handle settings-related callbacks
        if (call.data.startswith("settings_") or
            call.data.startswith("currency_") or
            call.data.startswith("impact_") or
            call.data.startswith("time_") or
            call.data.startswith("hour_") or
            call.data.startswith("minute_")):

            if settings_handler:
                handled, message, markup = settings_handler.handle_settings_callback(call)
                if handled:
                    bot.edit_message_text(
                        message,
                        chat_id=call.message.chat.id,
                        message_id=call.message.message_id,
                        reply_markup=markup,
                        parse_mode="HTML"
                    )
                    bot.answer_callback_query(call.id)
                    return
            else:
                bot.answer_callback_query(call.id, "❌ Settings not available")
                return

        # Handle calendar navigation
        if call.data.startswith("cal_"):
            calendar_nav(call)
            return

        # Handle calendar date selection
        if call.data == "pickdate_today":
            pick_today(call)
            return

        if call.data.startswith("pickdate_"):
            pick_date(call)
            return

        # Handle classic news flow callbacks
        if call.data in ["ANALYSIS_YES", "ANALYSIS_NO"]:
            analysis_choice_callback(call)
        elif call.data.startswith("impact_"):
            select_impact_callback(call)
        elif call.data == "IGNORE":
            bot.answer_callback_query(call.id)
        else:
            bot.answer_callback_query(call.id, "❌ Unknown callback")

    @bot.message_handler(commands=["today"])
    def get_today_news(message):
        chat_id = message.chat.id
        user_id = message.from_user.id
        user_state[chat_id] = {'date': datetime.now().date(), 'impact_level': 'high'}

        markup = InlineKeyboardMarkup(row_width=2)
        markup.add(
            InlineKeyboardButton("🔴 High Impact", callback_data="impact_high"),
            InlineKeyboardButton("🟠 Medium Impact", callback_data="impact_medium"),
            InlineKeyboardButton("🟡 Low Impact", callback_data="impact_low"),
            InlineKeyboardButton("📊 All Impacts", callback_data="impact_all")
        )

        bot.reply_to(message, "Select impact level for today's news:", reply_markup=markup)

    @bot.message_handler(commands=["tomorrow"])
    def get_tomorrow_news(message):
        chat_id = message.chat.id
        user_id = message.from_user.id
        tomorrow = datetime.now().date() + timedelta(days=1)
        user_state[chat_id] = {'date': tomorrow, 'impact_level': 'high'}

        markup = InlineKeyboardMarkup(row_width=2)
        markup.add(
            InlineKeyboardButton("🔴 High Impact", callback_data="impact_high"),
            InlineKeyboardButton("🟠 Medium Impact", callback_data="impact_medium"),
            InlineKeyboardButton("🟡 Low Impact", callback_data="impact_low"),
            InlineKeyboardButton("📊 All Impacts", callback_data="impact_all")
        )

        bot.reply_to(message, "Select impact level for tomorrow's news:", reply_markup=markup)

    @bot.message_handler(commands=["calendar"])
    def show_calendar(message):
        chat_id = message.chat.id
        user_id = message.from_user.id
        user_state[chat_id] = {'date': None, 'impact_level': 'high'}

        today = datetime.now().date()
        markup = TelegramHandlers.generate_calendar(today.year, today.month)

        bot.reply_to(message, "Please pick a date:", reply_markup=markup)

    @bot.callback_query_handler(func=lambda call: call.data.startswith("cal_"))
    def calendar_nav(call):
        _, year, month = call.data.split('_')
        year, month = int(year), int(month)
        bot.edit_message_reply_markup(
            chat_id=call.message.chat.id,
            message_id=call.message.message_id,
            reply_markup=TelegramHandlers.generate_calendar(year, month)
        )
        bot.answer_callback_query(call.id)

    def impact_keyboard():
        kb = InlineKeyboardMarkup()
        kb.row(
            InlineKeyboardButton("🔴 Red", callback_data="impact_high"),
            InlineKeyboardButton("🟠 Orange", callback_data="impact_medium"),
        )
        kb.row(
            InlineKeyboardButton("🟡 Yellow", callback_data="impact_low"),
            InlineKeyboardButton("🌈 All", callback_data="impact_all"),
        )
        return kb

    @bot.callback_query_handler(func=lambda call: call.data == "pickdate_today")
    def pick_today(call):
        today = datetime.now().date()
        user_state[call.message.chat.id] = {'date': today}

        # Check if user has saved preferences
        if settings_handler and db_service:
            try:
                user = db_service.get_or_create_user(call.from_user.id)
                saved_impact = user.get_impact_levels_list()
                saved_analysis = user.analysis_required

                if saved_impact and len(saved_impact) > 0:
                    # Use saved preferences for one-click news
                    impact_level = saved_impact[0] if len(saved_impact) == 1 else 'all'
                    user_state[call.message.chat.id]['impact_level'] = impact_level

                    bot.edit_message_text(
                        f"📅 Fetching news for {today.strftime('%Y-%m-%d')} with your saved preferences...",
                        chat_id=call.message.chat.id,
                        message_id=call.message.message_id
                    )

                    # Fetch news directly with saved preferences
                    import asyncio
                    asyncio.run(process_news_func(
                        datetime.combine(today, datetime.min.time()),
                        impact_level,
                        saved_analysis,
                        False,
                        call.from_user.id
                    ))
                    user_state.pop(call.message.chat.id, None)
                    bot.answer_callback_query(call.id)
                    return
            except Exception as e:
                logger.error(f"Error using saved preferences: {e}")

        # Fallback to manual selection if no saved preferences
        bot.edit_message_text(
            f"Selected date: {today.strftime('%Y-%m-%d')}. Now select impact:",
            chat_id=call.message.chat.id,
            message_id=call.message.message_id,
            reply_markup=impact_keyboard()
        )
        bot.answer_callback_query(call.id)

    @bot.callback_query_handler(func=lambda call: call.data.startswith("pickdate_"))
    def pick_date(call):
        logger.info(f"pick_date triggered: call.data={call.data}")
        try:
            _, year, month, day = call.data.split('_')
            picked = datetime(int(year), int(month), int(day)).date()
            logger.info(f"Parsed date: {picked}")
            user_state[call.message.chat.id] = {'date': picked}

            # Check if user has saved preferences
            if settings_handler and db_service:
                try:
                    user = db_service.get_or_create_user(call.from_user.id)
                    saved_impact = user.get_impact_levels_list()
                    saved_analysis = user.analysis_required

                    if saved_impact and len(saved_impact) > 0:
                        # Use saved preferences for one-click news
                        impact_level = saved_impact[0] if len(saved_impact) == 1 else 'all'
                        user_state[call.message.chat.id]['impact_level'] = impact_level

                        bot.edit_message_text(
                            f"📅 Fetching news for {picked.strftime('%Y-%m-%d')} with your saved preferences...",
                            chat_id=call.message.chat.id,
                            message_id=call.message.message_id
                        )

                        # Fetch news directly with saved preferences
                        import asyncio
                        asyncio.run(process_news_func(
                            datetime.combine(picked, datetime.min.time()),
                            impact_level,
                            saved_analysis,
                            False,
                            call.from_user.id
                        ))
                        user_state.pop(call.message.chat.id, None)
                        bot.answer_callback_query(call.id)
                        return
                except Exception as e:
                    logger.error(f"Error using saved preferences: {e}")

            # Fallback to manual selection if no saved preferences
            bot.edit_message_text(
                f"Selected date: {picked.strftime('%Y-%m-%d')}. Now select impact:",
                chat_id=call.message.chat.id,
                message_id=call.message.message_id,
                reply_markup=impact_keyboard()
            )
        except Exception as e:
            logger.error(f"Error in pick_date: {e}")
        bot.answer_callback_query(call.id)

    def select_impact_callback(call):
        chat_id = call.message.chat.id
        user_id = call.from_user.id
        impact_level = call.data.replace("impact_", "")
        logger.info(f"select_impact_callback: chat_id={chat_id}, impact_level={impact_level}")
        if chat_id in user_state:
            user_state[chat_id]['impact_level'] = impact_level
        markup = InlineKeyboardMarkup(row_width=2)
        markup.add(
            InlineKeyboardButton("🤖 With AI Analysis", callback_data="ANALYSIS_YES"),
            InlineKeyboardButton("📊 Without Analysis", callback_data="ANALYSIS_NO")
        )
        bot.edit_message_text(
            "Do you want AI analysis with the news?",
            chat_id=chat_id,
            message_id=call.message.message_id,
            reply_markup=markup
        )
        bot.answer_callback_query(call.id)

    @bot.callback_query_handler(func=lambda call: call.data in ["ANALYSIS_YES", "ANALYSIS_NO"])
    def analysis_choice_callback(call):
        chat_id = call.message.chat.id
        user_id = call.from_user.id
        analysis_required = (call.data == "ANALYSIS_YES")
        state = user_state.get(chat_id, {})
        date_obj = state.get('date')
        impact_level = state.get('impact_level', 'high')
        logger.info(f"analysis_choice_callback: chat_id={chat_id}, date={date_obj}, impact={impact_level}, analysis={analysis_required}")
        if not date_obj:
            bot.send_message(chat_id, "Please start with /today, /tomorrow, or /calendar.")
            return
        bot.edit_message_text(
            f"Fetching news for {date_obj.strftime('%Y-%m-%d')} with impact: {impact_level.capitalize()} (AI analysis: {'Yes' if analysis_required else 'No'})...",
            chat_id=chat_id,
            message_id=call.message.message_id
        )
        import asyncio
        asyncio.run(process_news_func(datetime.combine(date_obj, datetime.min.time()), impact_level, analysis_required, False, user_id))
        user_state.pop(chat_id, None)
        bot.answer_callback_query(call.id)

    def get_help_text():
        return """
🤖 <b>Forex News Bot</b>

<b>Commands:</b>
• /start, /help - Show this help
• /settings - Configure your preferences
• /today - Get today's news
• /tomorrow - Get tomorrow's news
• /calendar - Select a specific date

<b>Features:</b>
• 📊 Personalized news filtering
• 💰 Currency preferences
• 📈 Impact level selection
• 🤖 AI-powered analysis
• ⏰ Daily digest scheduling
• ⚙️ User settings management

<b>Settings:</b>
• Choose preferred currencies
• Select impact levels (High/Medium/Low)
• Enable/disable AI analysis
• Set daily digest time

Use /settings to customize your experience!
        """

    logger.info("All handlers registered successfully")
