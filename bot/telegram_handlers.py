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

    @staticmethod
    def filter_news_by_impact(news_items, impact_level):
        if impact_level == 'all':
            return news_items
        return [item for item in news_items if item.get('impact') == impact_level]


user_selected_date = {}
user_selected_impact = {}
user_analysis_required = {}  # NEW: Store per-user analysis preference


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

    def ask_analysis_required(chat_id):
        markup = InlineKeyboardMarkup()
        markup.add(
            InlineKeyboardButton("✅ Yes, include analysis", callback_data="ANALYSIS_YES"),
            InlineKeyboardButton("❌ No analysis", callback_data="ANALYSIS_NO"),
        )
        bot.send_message(chat_id, "🤖 Require ChatGPT analysis for news?", reply_markup=markup)

    @bot.message_handler(commands=["today"])
    def get_today_news(message):
        try:
            user_id = message.from_user.id
            impact_level = user_selected_impact.get(user_id, "high")
            # Ask for analysis requirement before fetching news
            user_selected_date[user_id] = datetime.now().strftime("%Y-%m-%d")
            ask_analysis_required(message.chat.id)
        except Exception as e:
            logger.error("Error in today command: %s", e)
            bot.send_message(message.chat.id, "❌ Error processing request. Please try again.")

    @bot.message_handler(commands=["tomorrow"])
    def get_tomorrow_news(message):
        try:
            user_id = message.from_user.id
            impact_level = user_selected_impact.get(user_id, "high")
            # Ask for analysis requirement before fetching news
            tomorrow = datetime.now() + timedelta(days=1)
            user_selected_date[user_id] = tomorrow.strftime("%Y-%m-%d")
            ask_analysis_required(message.chat.id)
        except Exception as e:
            logger.error("Error in tomorrow command: %s", e)
            bot.send_message(message.chat.id, "❌ Error processing request. Please try again.")

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
                # Ask for analysis requirement before fetching news
                ask_analysis_required(call.message.chat.id)
                bot.edit_message_text(
                    f"🔄 Fetching forex news for {date_str}...",
                    call.message.chat.id,
                    call.message.message_id,
                )
                return
            elif data.startswith("IMPACT_"):
                impact_level = data[7:]
                user_selected_impact[user_id] = impact_level
                ask_analysis_required(call.message.chat.id)
                bot.edit_message_text(
                    f"✅ Impact level set to: {impact_level.capitalize()}.\n\nDo you want AI analysis for news?",
                    call.message.chat.id,
                    call.message.message_id,
                )
                return
            elif data == "ANALYSIS_YES" or data == "ANALYSIS_NO":
                user_analysis_required[user_id] = (data == "ANALYSIS_YES")
                # Now fetch and send news with the selected options
                date_str = user_selected_date.get(user_id)
                impact_level = user_selected_impact.get(user_id, "high")
                analysis_required = user_analysis_required.get(user_id, True)
                if date_str:
                    try:
                        target_date = datetime.strptime(date_str, "%Y-%m-%d")
                    except Exception:
                        target_date = None
                else:
                    target_date = None
                bot.send_message(call.message.chat.id, "🔄 Fetching forex news...")
                def fetch_and_send():
                    try:
                        all_news = asyncio.run(process_news(target_date, impact_level, analysis_required, debug=True))
                        filtered_news = TelegramHandlers.filter_news_by_impact(all_news, impact_level)
                        msg = ForexNewsScraper.MessageFormatter.format_news_message(filtered_news, target_date or datetime.now(), impact_level, analysis_required)
                        bot.send_message(call.message.chat.id, msg, parse_mode='HTML')
                    except Exception as e:
                        logger.error("Error fetching news: %s", e)
                        bot.send_message(call.message.chat.id, "❌ Error fetching news. Please try again.")
                threading.Thread(target=fetch_and_send, daemon=True).start()
                return
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


user_state = {}

IMPACT_MAP = {
    'impact_high': 'high',
    'impact_medium': 'medium',
    'impact_low': 'low',
    'impact_all': 'all',
}

IMPACT_LABELS = {
    'impact_high': '🔴 Red',
    'impact_medium': '🟠 Orange',
    'impact_low': '🟡 Yellow',
    'impact_all': '🌈 All',
}

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

# --- Calendar UI ---
def calendar_keyboard(year, month):
    today = dt_date.today()
    kb = InlineKeyboardMarkup(row_width=7)
    # Month/year header
    kb.add(InlineKeyboardButton(f"{month_name[month]} {year}", callback_data="ignore"))
    # Weekday header
    week_days = ["Mo", "Tu", "We", "Th", "Fr", "Sa", "Su"]
    kb.row(*[InlineKeyboardButton(day, callback_data="ignore") for day in week_days])
    # Days
    first_weekday, num_days = monthrange(year, month)
    days = []
    for i in range(first_weekday):
        days.append(InlineKeyboardButton(" ", callback_data="ignore"))
    for day in range(1, num_days + 1):
        d = dt_date(year, month, day)
        if d < today:
            # Past day: show as ~DD~
            days.append(InlineKeyboardButton(f"~{str(day).zfill(2)}~", callback_data="ignore"))
        else:
            days.append(InlineKeyboardButton(str(day).zfill(2), callback_data=f"pickdate_{year}_{month}_{day}"))
        if (len(days) % 7) == 0:
            kb.row(*days)
            days = []
    if days:
        kb.row(*days)
    # Navigation
    prev_month = (month - 1) or 12
    prev_year = year - 1 if month == 1 else year
    next_month = (month + 1) if month < 12 else 1
    next_year = year + 1 if month == 12 else year
    nav_row = []
    nav_row.append(InlineKeyboardButton("⬅️", callback_data=f"cal_{prev_year}_{prev_month}"))
    nav_row.append(InlineKeyboardButton("Today", callback_data="pickdate_today"))
    nav_row.append(InlineKeyboardButton("➡️", callback_data=f"cal_{next_year}_{next_month}"))
    kb.row(*nav_row)
    return kb


def register_handlers(bot, process_news_func, config):
    def get_help_text():
        return (
            "👋 <b>Welcome to the Forex News Bot!</b>\n\n"
            "This bot helps you get the latest ForexFactory economic news directly in Telegram, with advanced features:\n\n"
            "<b>Commands:</b>\n"
            "• /today — Get today's news (pick impact)\n"
            "• /tomorrow — Get tomorrow's news (pick impact)\n"
            "• /calendar — Pick any date from a calendar UI\n"
            "• /help — Show this help message\n\n"
            "<b>Features:</b>\n"
            "• <b>Impact selection:</b> Red (high), Orange (medium), Yellow (low), All\n"
            "• <b>All news types:</b> High, medium, and low impact events are supported\n"
            "• <b>Database:</b> All news is stored and deduplicated for fast access\n"
            "• <b>AI Analysis:</b> Each event can include ChatGPT-powered analysis (if enabled)\n"
            "• <b>Fast & Reliable:</b> If news is already in the database, it's sent instantly\n"
            "• <b>Modern UI:</b> Use the calendar and inline buttons for a smooth experience\n\n"
            "<b>Tip:</b> Use /help at any time to see this info again."
        )

    @bot.message_handler(commands=['start', 'news'])
    def start_handler(message):
        bot.send_message(
            message.chat.id,
            get_help_text(),
            parse_mode="HTML"
        )

    @bot.message_handler(commands=['help'])
    def help_handler(message):
        bot.send_message(
            message.chat.id,
            get_help_text(),
            parse_mode="HTML"
        )

    # --- Unified date -> impact -> analysis flow ---

    @bot.message_handler(commands=['today'])
    def today_handler(message):
        user_state[message.chat.id] = {'date': datetime.now().date()}
        bot.send_message(message.chat.id, "Select impact level:", reply_markup=impact_keyboard())

    @bot.message_handler(commands=['tomorrow'])
    def tomorrow_handler(message):
        user_state[message.chat.id] = {'date': (datetime.now() + timedelta(days=1)).date()}
        bot.send_message(message.chat.id, "Select impact level:", reply_markup=impact_keyboard())

    @bot.message_handler(commands=['calendar'])
    def calendar_handler(message):
        today = dt_date.today()
        user_state[message.chat.id] = {'step': 'calendar'}
        bot.send_message(
            message.chat.id,
            "Please pick a date:",
            reply_markup=calendar_keyboard(today.year, today.month)
        )

    @bot.callback_query_handler(func=lambda call: call.data.startswith("cal_"))
    def calendar_nav(call):
        _, year, month = call.data.split('_')
        year, month = int(year), int(month)
        bot.edit_message_reply_markup(
            chat_id=call.message.chat.id,
            message_id=call.message.message_id,
            reply_markup=calendar_keyboard(year, month)
        )
        bot.answer_callback_query(call.id)

    @bot.callback_query_handler(func=lambda call: call.data == "pickdate_today")
    def pick_today(call):
        today = dt_date.today()
        user_state[call.message.chat.id] = {'date': today}
        bot.edit_message_text(
            f"Selected date: {today.strftime('%Y-%m-%d')}. Now select impact:",
            chat_id=call.message.chat.id,
            message_id=call.message.message_id,
            reply_markup=impact_keyboard()
        )
        bot.answer_callback_query(call.id)

    @bot.callback_query_handler(func=lambda call: call.data.startswith("pickdate_"))
    def pick_date(call):
        _, year, month, day = call.data.split('_')
        picked = dt_date(int(year), int(month), int(day))
        user_state[call.message.chat.id] = {'date': picked}
        bot.edit_message_text(
            f"Selected date: {picked.strftime('%Y-%m-%d')}. Now select impact:",
            chat_id=call.message.chat.id,
            message_id=call.message.message_id,
            reply_markup=impact_keyboard()
        )
        bot.answer_callback_query(call.id)

    @bot.message_handler(func=lambda m: user_state.get(m.chat.id, {}).get('step') == 'date')
    def date_input_handler(message):
        try:
            date_obj = datetime.strptime(message.text.strip(), "%Y-%m-%d").date()
            user_state[message.chat.id]['date'] = date_obj
            bot.send_message(message.chat.id, "Select impact level:", reply_markup=impact_keyboard())
            user_state[message.chat.id]['step'] = 'impact_keyboard'
        except Exception:
            bot.send_message(message.chat.id, "Invalid date format. Please use YYYY-MM-DD.")

    @bot.callback_query_handler(func=lambda call: call.data.startswith("impact_"))
    def impact_callback(call):
        impact_level = IMPACT_MAP[call.data]
        date_obj = user_state.get(call.message.chat.id, {}).get('date')
        if not date_obj:
            bot.answer_callback_query(call.id, "Please start with /today, /tomorrow, or /calendar.")
            return
        label = IMPACT_LABELS[call.data]
        # Store the impact level in user_state
        user_state[call.message.chat.id]['impact_level'] = impact_level
        # Show the AI analysis prompt
        markup = InlineKeyboardMarkup()
        markup.row(
            InlineKeyboardButton("✅ Yes, include analysis", callback_data="ANALYSIS_YES"),
            InlineKeyboardButton("❌ No analysis", callback_data="ANALYSIS_NO"),
        )
        bot.edit_message_text(
            f"Impact level set to: {label}. Do you want AI analysis for news?",
            chat_id=call.message.chat.id,
            message_id=call.message.message_id,
            reply_markup=markup
        )
        bot.answer_callback_query(call.id)

    @bot.callback_query_handler(func=lambda call: call.data in ["ANALYSIS_YES", "ANALYSIS_NO"])
    def analysis_choice_callback(call):
        chat_id = call.message.chat.id
        analysis_required = (call.data == "ANALYSIS_YES")
        state = user_state.get(chat_id, {})
        date_obj = state.get('date')
        impact_level = state.get('impact_level', 'high')
        if not date_obj:
            bot.send_message(chat_id, "Please start with /today, /tomorrow, or /calendar.")
            return
        bot.edit_message_text(
            f"Fetching news for {date_obj.strftime('%Y-%m-%d')} with impact: {impact_level.capitalize()} (AI analysis: {'Yes' if analysis_required else 'No'})...",
            chat_id=chat_id,
            message_id=call.message.message_id
        )
        import asyncio
        asyncio.run(process_news_func(datetime.combine(date_obj, datetime.min.time()), impact_level, analysis_required))
        user_state.pop(chat_id, None)
        bot.answer_callback_query(call.id)
