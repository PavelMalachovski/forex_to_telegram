import logging
import os
import asyncio
import time
import threading
from datetime import datetime, timedelta, date as dt_date
from typing import Callable
import pytz

import telebot
from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton, CallbackQuery


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
        logger.info("Attempting to set webhook to: %s", webhook_url)

        # First, check current webhook status
        try:
            current_webhook = self.bot.get_webhook_info()
            logger.info("Current webhook info: URL=%s, Pending updates=%s, Last error=%s",
                       current_webhook.url, current_webhook.pending_update_count,
                       current_webhook.last_error_message)
        except Exception as e:
            logger.error("Failed to get current webhook info: %s", e)

        for attempt in range(max_retries):
            try:
                logger.info("Setting webhook attempt %s/%s to %s", attempt + 1, max_retries, webhook_url)

                # Remove existing webhook first
                try:
                    self.bot.remove_webhook()
                    time.sleep(2)
                    logger.info("Removed existing webhook")
                except Exception as e:
                    logger.warning("Failed to remove existing webhook: %s", e)

                # Set new webhook (include secret token if configured)
                webhook_kwargs = {"url": webhook_url}
                if getattr(self.config, "telegram_webhook_secret", None):
                    webhook_kwargs["secret_token"] = self.config.telegram_webhook_secret
                result = self.bot.set_webhook(**webhook_kwargs)
                if result:
                    logger.info("Webhook setup returned True")

                    # Verify webhook was set correctly
                    try:
                        time.sleep(3)  # Wait a bit for Telegram to process
                        new_webhook = self.bot.get_webhook_info()
                        logger.info("Webhook verification: URL=%s, Pending updates=%s, Last error=%s",
                                   new_webhook.url, new_webhook.pending_update_count,
                                   new_webhook.last_error_message)

                        if new_webhook.url == webhook_url:
                            logger.info("✅ Webhook URL matches expected URL")

                            # Check if there are any pending updates
                            if new_webhook.pending_update_count > 0:
                                logger.info("📥 Found %s pending updates", new_webhook.pending_update_count)

                            # Check for any recent errors
                            if new_webhook.last_error_message:
                                logger.warning("⚠️ Webhook has recent error: %s", new_webhook.last_error_message)

                            return True
                        else:
                            logger.warning("❌ Webhook URL mismatch. Expected: %s, Got: %s",
                                         webhook_url, new_webhook.url)
                    except Exception as e:
                        logger.error("Failed to verify webhook: %s", e)

                    return True
                else:
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

    def check_webhook_status(self):
        """Check the current webhook status and return detailed information."""
        if not self.bot:
            return {"error": "Bot not initialized"}

        try:
            webhook_info = self.bot.get_webhook_info()
            return {
                "url": webhook_info.url,
                "has_custom_certificate": webhook_info.has_custom_certificate,
                "pending_update_count": webhook_info.pending_update_count,
                "last_error_date": webhook_info.last_error_date.isoformat() if webhook_info.last_error_date else None,
                "last_error_message": webhook_info.last_error_message,
                "max_connections": webhook_info.max_connections,
                "allowed_updates": webhook_info.allowed_updates,
                "is_configured": webhook_info.url is not None and webhook_info.url != ""
            }
        except Exception as e:
            return {"error": str(e)}

    def test_bot_connection(self):
        """Test if the bot can connect to Telegram API."""
        if not self.bot:
            return {"error": "Bot not initialized"}

        try:
            me = self.bot.get_me()
            return {
                "success": True,
                "bot_info": {
                    "id": me.id,
                    "username": me.username,
                    "first_name": me.first_name,
                    "can_join_groups": me.can_join_groups,
                    "can_read_all_group_messages": me.can_read_all_group_messages,
                    "supports_inline_queries": me.supports_inline_queries
                }
            }
        except Exception as e:
            return {"error": str(e)}

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
    def generate_calendar(year: int, month: int, timezone_str: str = "UTC") -> InlineKeyboardMarkup:
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

        today = datetime.now(pytz.timezone(timezone_str)).date()

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
        today_str = datetime.now(pytz.timezone(timezone_str)).strftime('%Y-%m-%d')
        tomorrow_str = (datetime.now(pytz.timezone(timezone_str)) + timedelta(days=1)).strftime('%Y-%m-%d')
        yesterday_str = (datetime.now(pytz.timezone(timezone_str)) - timedelta(days=1)).strftime('%Y-%m-%d')

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

    # Provide decorator shims when running in tests with a minimal MockBot
    if not hasattr(bot, 'message_handler'):
        def _noop_decorator_factory(*args, **kwargs):
            def _decorator(func):
                return func
            return _decorator
        setattr(bot, 'message_handler', _noop_decorator_factory)
    if not hasattr(bot, 'callback_query_handler'):
        def _noop_callback_decorator_factory(*args, **kwargs):
            def _decorator(func):
                return func
            return _decorator
        setattr(bot, 'callback_query_handler', _noop_callback_decorator_factory)

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
            call.data.startswith("minute_") or
            call.data.startswith("timezone_") or
            call.data.startswith("notification_")):

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

        # Handle visualize callbacks
        if (call.data.startswith("viz_currency_") or
            call.data.startswith("viz_event_name_") or
            call.data.startswith("viz_events_") or
            call.data.startswith("viz_event_") or
            call.data.startswith("viz_chart_") or
            call.data.startswith("viz_multi_") or
            call.data.startswith("viz_secondary_") or
            call.data == "viz_back_currencies"):

            logger.info(f"Processing visualize callback: {call.data}")

            if not db_service:
                bot.answer_callback_query(call.id, "❌ Database service not available")
                return

            # Import and initialize visualize handler
            from .visualize_handler import VisualizeHandler
            viz_handler = VisualizeHandler(db_service, config)

            # Handle different visualize callbacks
            try:
                if call.data.startswith("viz_currency_"):
                    logger.info("Handling currency selection")
                    viz_handler.handle_currency_selection(call, bot)
                elif call.data.startswith("viz_event_name_"):
                    logger.info("Handling event name selection")
                    viz_handler.handle_event_name_selection(call, bot)
                elif call.data.startswith("viz_events_"):
                    logger.info("Handling events pagination")
                    viz_handler.handle_events_page(call, bot)
                elif call.data.startswith("viz_event_"):
                    logger.info("Handling event selection")
                    viz_handler.handle_event_selection(call, bot)
                elif call.data.startswith("viz_chart_"):
                    logger.info("Handling single chart generation")
                    viz_handler.handle_chart_generation(call, bot)
                elif call.data.startswith("viz_multi_"):
                    logger.info("Handling multi-currency selection")
                    viz_handler.handle_multi_currency_selection(call, bot)
                elif call.data.startswith("viz_secondary_"):
                    logger.info("Handling secondary currency selection")
                    viz_handler.handle_secondary_currency_selection(call, bot)
                elif call.data == "viz_back_currencies":
                    logger.info("Handling back to currencies")
                    viz_handler.handle_back_to_currencies(call, bot)
            except Exception as e:
                logger.error(f"Error handling visualize callback {call.data}: {e}")
                bot.answer_callback_query(call.id, f"❌ Error: {str(e)[:50]}")
            return

        # Handle GPT analysis callbacks inline to avoid unknown callback
        if call.data.startswith("gpt_base_"):
            base = call.data.replace("gpt_base_", "")
            from .visualize_handler import VisualizeHandler
            viz_handler = VisualizeHandler(db_service, config) if db_service else None
            choices = [c for c in (viz_handler.available_currencies if viz_handler else ["USD","EUR","GBP","JPY"]) if c != base]
            keyboard = []
            row = []
            for c in choices:
                row.append(InlineKeyboardButton(c, callback_data=f"gpt_quote_{base}_{c}"))
                if len(row) == 3:
                    keyboard.append(row)
                    row = []
            if row:
                keyboard.append(row)
            reply_markup = InlineKeyboardMarkup(keyboard)
            bot.edit_message_text(
                f"🤖 Base: {base}\nChoose quote currency:",
                chat_id=call.message.chat.id,
                message_id=call.message.message_id,
                reply_markup=reply_markup
            )
            bot.answer_callback_query(call.id)
            return

        if call.data.startswith("gpt_quote_"):
            try:
                # Expected format: gpt_quote_BASE_QUOTE
                parts = call.data.split("_")
                # parts -> ["gpt", "quote", BASE, QUOTE]
                if len(parts) != 4:
                    raise ValueError("Malformed callback data")
                _, _, base, quote = parts
            except Exception:
                bot.answer_callback_query(call.id, "Invalid selection")
                return
            bot.answer_callback_query(call.id, "🔄 Computing features...")
            bot.edit_message_text(
                f"🔄 Computing local features for {base}/{quote}...",
                chat_id=call.message.chat.id,
                message_id=call.message.message_id
            )
            try:
                from .gpt_analysis import run_pair_analysis_with_features
                from .gpt_analysis import _get_symbol_from_currencies  # reuse symbol mapping
                api_key = os.getenv("OPENAI_API_KEY") or os.getenv("CHATGPT_API_KEY")
                result = run_pair_analysis_with_features(base, quote, api_key, config.timezone, call.from_user.id)
                if not result:
                    bot.edit_message_text(
                        f"❌ Could not compute analysis for {base}/{quote}.",
                        chat_id=call.message.chat.id,
                        message_id=call.message.message_id
                    )
                    return
                text = result.get("text")
                features = result.get("features", {})
                symbol = result.get("symbol") or _get_symbol_from_currencies(base, quote)
                # Build charts: full view (EMAs only) and zoomed view (features)
                try:
                    from .chart_service import chart_service
                    full_chart = chart_service.create_gpt_full_view_chart(symbol=symbol, features=features, window_hours=48)
                    zoom_chart = chart_service.create_gpt_zoom_view_chart(symbol=symbol, features=features, window_hours=48, zoom_hours=12)
                except Exception as ce:
                    logger.error(f"Failed to create GPT analysis chart: {ce}")
                    full_chart = None
                    zoom_chart = None
                if full_chart:
                    # Send photo first, then a separate message with analysis to avoid caption limits
                    try:
                        bot.send_photo(chat_id=call.message.chat.id, photo=full_chart, caption=f"📈 {base}/{quote} — EMAs (5m, last 48h)")
                    except Exception:
                        # fallback without caption
                        bot.send_photo(chat_id=call.message.chat.id, photo=full_chart)
                if zoom_chart:
                    try:
                        bot.send_photo(chat_id=call.message.chat.id, photo=zoom_chart, caption=f"🔍 {base}/{quote} — Zoomed (5m, last 12h)")
                    except Exception:
                        bot.send_photo(chat_id=call.message.chat.id, photo=zoom_chart)
                # Send analysis text
                bot.send_message(
                    chat_id=call.message.chat.id,
                    text=f"📊 {base}/{quote} analysis\n\n" + text,
                    parse_mode='Markdown'
                )
            except Exception as e:
                logger.error(f"GPT analysis failed: {e}")
                bot.edit_message_text(
                    f"❌ Error: {str(e)[:200]}",
                    chat_id=call.message.chat.id,
                    message_id=call.message.message_id
                )
            return

        # Handle classic news flow callbacks (AI analysis prompt removed)
        if call.data in ["ANALYSIS_YES", "ANALYSIS_NO"]:
            bot.answer_callback_query(call.id, "AI analysis is disabled.")
            return
        elif call.data.startswith("impact_"):
            select_impact_callback(call)
        elif call.data == "IGNORE":
            bot.answer_callback_query(call.id)
        else:
            # Gracefully ignore unknown callbacks to avoid user-facing errors
            bot.answer_callback_query(call.id)

    @bot.message_handler(commands=["today"])
    def get_today_news(message):
        chat_id = message.chat.id
        user_id = message.from_user.id
        user_state[chat_id] = {'date': datetime.now(pytz.timezone(config.timezone)).date(), 'impact_level': 'high'}

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
        tomorrow = datetime.now(pytz.timezone(config.timezone)).date() + timedelta(days=1)
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

        today = datetime.now(pytz.timezone(config.timezone)).date()
        markup = TelegramHandlers.generate_calendar(today.year, today.month, config.timezone)

        bot.reply_to(message, "Please pick a date:", reply_markup=markup)

    @bot.message_handler(commands=["visualize"])
    def show_visualize(message):
        chat_id = message.chat.id
        if not db_service:
            bot.send_message(chat_id, "❌ Database service not available.")
            return

        # Import and initialize visualize handler
        from .visualize_handler import VisualizeHandler
        viz_handler = VisualizeHandler(db_service, config)

        # Create currency selection keyboard
        keyboard = []
        row = []

        for currency in viz_handler.available_currencies:
            row.append(InlineKeyboardButton(currency, callback_data=f"viz_currency_{currency}"))
            if len(row) == 3:  # 3 buttons per row
                keyboard.append(row)
                row = []

        if row:  # Add remaining buttons
            keyboard.append(row)

        reply_markup = InlineKeyboardMarkup(keyboard)

        bot.send_message(
            chat_id,
            "📊 **Chart Visualization**\n\n"
            "Select a currency to view available events and generate charts:",
            reply_markup=reply_markup,
            parse_mode='Markdown'
        )

    @bot.message_handler(commands=["gptanalysis"])
    def show_gpt_analysis(message):
        chat_id = message.chat.id
        # Step 1: Choose base currency
        from .visualize_handler import VisualizeHandler
        if not db_service:
            bot.send_message(chat_id, "❌ Database service not available.")
            return
        viz_handler = VisualizeHandler(db_service, config)
        currencies = viz_handler.available_currencies

        keyboard = []
        row = []
        for c in currencies:
            row.append(InlineKeyboardButton(c, callback_data=f"gpt_base_{c}"))
            if len(row) == 3:
                keyboard.append(row)
                row = []
        if row:
            keyboard.append(row)
        reply_markup = InlineKeyboardMarkup(keyboard)
        bot.send_message(chat_id, "🤖 Choose base currency:", reply_markup=reply_markup)



    @bot.callback_query_handler(func=lambda call: call.data.startswith("cal_"))
    def calendar_nav(call):
        _, year, month = call.data.split('_')
        year, month = int(year), int(month)
        bot.edit_message_reply_markup(
            chat_id=call.message.chat.id,
            message_id=call.message.message_id,
            reply_markup=TelegramHandlers.generate_calendar(year, month, config.timezone)
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
        today = datetime.now(pytz.timezone(config.timezone)).date()
        user_state[call.message.chat.id] = {'date': today}

        # Check if user has saved preferences
        if settings_handler and db_service:
            try:
                user = db_service.get_or_create_user(call.from_user.id)
                saved_impact = user.get_impact_levels_list()
                saved_analysis = user.analysis_required

                if saved_impact and len(saved_impact) > 0:
                    # Use saved preferences for one-click news
                    # If user has multiple impact levels, use 'all' to show all selected levels
                    impact_level = 'all' if len(saved_impact) > 1 else saved_impact[0]
                    user_state[call.message.chat.id]['impact_level'] = impact_level

                    bot.edit_message_text(
                        f"📅 Fetching news for {today.strftime('%Y-%m-%d')} with your saved preferences...",
                        chat_id=call.message.chat.id,
                        message_id=call.message.message_id
                    )

                    # Fetch news directly with saved preferences
                    import asyncio
                    asyncio.run(process_news_func(
                        datetime.combine(today, datetime.min.time()).replace(tzinfo=pytz.timezone(config.timezone)),
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
                        # If user has multiple impact levels, use 'all' to show all selected levels
                        impact_level = 'all' if len(saved_impact) > 1 else saved_impact[0]
                        user_state[call.message.chat.id]['impact_level'] = impact_level

                        bot.edit_message_text(
                            f"📅 Fetching news for {picked.strftime('%Y-%m-%d')} with your saved preferences...",
                            chat_id=call.message.chat.id,
                            message_id=call.message.message_id
                        )

                        # Fetch news directly with saved preferences
                        import asyncio
                        asyncio.run(process_news_func(
                            datetime.combine(picked, datetime.min.time()).replace(tzinfo=pytz.timezone(config.timezone)),
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
        # AI analysis removed: proceed directly to fetch with no analysis, using selected date
        state = user_state.get(chat_id, {})
        date_obj = state.get('date')
        if not date_obj:
            date_obj = datetime.now(pytz.timezone(config.timezone)).date()
        bot.edit_message_text(
            f"Fetching news for {date_obj.strftime('%Y-%m-%d')} with impact: {impact_level.capitalize()}...",
            chat_id=chat_id,
            message_id=call.message.message_id
        )
        import asyncio
        tz = pytz.timezone(config.timezone)
        aware_dt = datetime.combine(date_obj, datetime.min.time()).replace(tzinfo=tz)
        asyncio.run(process_news_func(aware_dt, impact_level, False, False, call.from_user.id))
        # Clear state
        try:
            user_state.pop(chat_id, None)
        except Exception:
            pass
        bot.answer_callback_query(call.id)

    # Removed analysis_choice_callback (AI analysis disabled)

    def get_help_text():
        return """
🤖 <b>Forex News Bot — Command Guide</b>

<b>📌 Main Commands:</b>
/start – Welcome & help menu
/help – Show this guide
/today – Today’s forex news
/tomorrow – Tomorrow’s news
/calendar – Pick a date from calendar
/visualize – Charts of news events
/settings – Configure preferences
/gptanalysis – AI pair analysis

<b>✨ Key Features:</b>
📊 Personalized news by currency & impact level
💰 Currency filter (e.g., USD, EUR, JPY)
📈 Impact selection (High / Medium / Low)
🤖 AI analysis of currency pairs
⏰ Daily digest at your chosen time
⚙️ Full settings control
📊 Charts for price vs news events

<b>⚙️ Settings Menu Includes:</b>
Pick currencies you care about
Choose impact levels (High/Medium/Low)
Schedule daily digest
Quick /gptanalysis for any pair

<b>📊 Visualization Mode:</b>
Select currency & events
Generate price movement charts around news
Set your own time window for analysis

💡 Tip: Use /settings to customize everything for your trading style.
        """

    logger.info("All handlers registered successfully")
