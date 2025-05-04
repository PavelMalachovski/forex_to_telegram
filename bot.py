import os
import logging
import telebot
from flask import Flask, request, jsonify
from datetime import datetime, timedelta
from pytz import timezone
from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton, CallbackQuery
import sqlite3
from apscheduler.schedulers.background import BackgroundScheduler
import requests
import threading
from typing import Dict, List, Tuple

# Logging setup with enhanced formatting
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] [%(funcName)s] %(message)s",
    handlers=[
        logging.FileHandler('bot.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

app = Flask(__name__)

# Check TELEGRAM_BOT_TOKEN and CHAT_ID
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")
if not TELEGRAM_BOT_TOKEN or not CHAT_ID:
    logger.error("TELEGRAM_BOT_TOKEN or TELEGRAM_CHAT_ID is not set. Bot functionality will be disabled.")
    bot = None
else:
    bot = telebot.TeleBot(TELEGRAM_BOT_TOKEN)
    logger.info("Telegram bot initialized successfully")

# User preferences
user_selected_date: Dict[int, str] = {}
user_selected_impact: Dict[int, str] = {}
user_currency_preferences: Dict[int, List[str]] = {}

# Available currencies
AVAILABLE_CURRENCIES = ["EUR", "USD", "JPY", "GBP", "CAD"]

# Database helper
def get_news_from_db(start_date: str, end_date: str, impact_level: str = "high") -> List[dict]:
    """Fetch news from the database with the given date range and impact level."""
    try:
        with sqlite3.connect('news.db') as conn:
            c = conn.cursor()
            query = '''
                SELECT date, time, currency, event, forecast, previous, actual, analysis
                FROM news
                WHERE date BETWEEN ? AND ? AND impact = ?
            '''
            params = (start_date, end_date, impact_level)
            if impact_level == "medium":
                query = '''
                    SELECT date, time, currency, event, forecast, previous, actual, analysis
                    FROM news
                    WHERE date BETWEEN ? AND ? AND impact IN ('high', 'medium')
                '''
            c.execute(query, params)
            rows = c.fetchall()
        return [{"date": row[0], "time": row[1], "currency": row[2], "event": row[3], "forecast": row[4], "previous": row[5], "actual": row[6], "analysis": row[7]} for row in rows]
    except sqlite3.Error as e:
        logger.error(f"Database error: {e}")
        return []

def escape_markdown_v2(text: str) -> str:
    """Escape special characters for MarkdownV2."""
    if not text or text.strip() == "":
        return "N/A"
    special_chars = ['_', '*', '[', ']', '(', ')', '~', '`', '>', '#', '+', '-', '=', '|', '{', '}', '.', '!']
    for char in special_chars:
        text = text.replace(char, f"\\{char}")
    return text

# APScheduler setup
scheduler = BackgroundScheduler()

def ping_self():
    """Ping the app to prevent sleep on Render.com."""
    try:
        base_url = f"https://{os.getenv('RENDER_EXTERNAL_HOSTNAME')}"
        ping_url = f"{base_url}/ping"
        response = requests.get(ping_url, timeout=10)
        if response.status_code == 200:
            logger.info(f"Ping successful: {ping_url}")
        else:
            logger.error(f"Ping failed: {ping_url}, status code: {response.status_code}")
    except Exception as e:
        logger.error(f"Ping error: {e}")

def check_and_send_notifications():
    """Check and send notifications for upcoming high-impact events."""
    if not bot or not CHAT_ID:
        logger.error("Cannot send notifications: Bot or CHAT_ID not configured")
        return

    now = datetime.now(timezone("Europe/Prague"))
    start_date = now.strftime("%Y-%m-%d")
    end_date = (now + timedelta(days=3)).strftime("%Y-%m-%d")

    news_items = get_news_from_db(start_date, end_date, impact_level="high")
    if not news_items:
        logger.info("No high-impact news items to notify about.")
        return

    events_by_time: Dict[Tuple[str, str], List[Tuple[str, str, str, str, str]]] = {}
    for news_item in news_items:
        key = (news_item['date'], news_item['time'].replace("\\", ""))
        events_by_time.setdefault(key, []).append((
            news_item['currency'].replace("\\", ""),
            news_item['event'].replace("\\", ""),
            news_item['forecast'].replace("\\", ""),
            news_item['previous'].replace("\\", ""),
            news_item['actual'].replace("\\", "")
        ))

    for (event_date, event_time), events in events_by_time.items():
        try:
            event_datetime = timezone("Europe/Prague").localize(datetime.strptime(f"{event_date} {event_time}", "%Y-%m-%d %H:%M"))
            time_diff = (event_datetime - now).total_seconds() / 60
        except ValueError as e:
            logger.warning(f"Could not parse event time: {event_time} for date {event_date}, error: {e}")
            continue

        if 19 <= time_diff <= 21:
            event_list = [f"{currency} {event}" for currency, event, _, _, _ in events]
            forecast_list = [forecast for _, _, forecast, _, _ in events]
            previous_list = [previous for _, _, _, previous, _ in events]
            actual_list = [actual for _, _, _, _, actual in events]
            message = (
                f"⏰ Reminder: In 20 minutes, there will be a news event!\n"
                f"📰 Events: {escape_markdown_v2(' & '.join(event_list))}\n"
                f"📈 Forecast: {escape_markdown_v2(' & '.join(forecast_list))}\n"
                f"📊 Previous: {escape_markdown_v2(' & '.join(previous_list))}\n"
                f"🎯 Actual: {escape_markdown_v2(' & '.join(actual_list))}\n"
                f"📅 Time: {escape_markdown_v2(event_time)}"
            )

            for chat_id, currencies in user_currency_preferences.items():
                if any(currency in currencies for currency, _, _, _, _ in events):
                    try:
                        bot.send_message(chat_id, message, parse_mode='MarkdownV2', disable_web_page_preview=True)
                        logger.info(f"Sent notification to chat {chat_id} for events: {', '.join(event_list)}")
                    except Exception as e:
                        logger.error(f"Failed to send notification to chat {chat_id}: {e}")

# Scheduler setup
if os.getenv('RENDER_EXTERNAL_HOSTNAME'):
    scheduler.add_job(ping_self, 'interval', minutes=5)
    scheduler.add_job(check_and_send_notifications, 'interval', minutes=5)
    scheduler.start()
    logger.info("Started APScheduler for self-ping and notifications")
else:
    logger.warning("RENDER_EXTERNAL_HOSTNAME not set, skipping scheduler setup")

# Telegram bot handlers
def generate_calendar(year: int, month: int) -> InlineKeyboardMarkup:
    markup = InlineKeyboardMarkup(row_width=7)
    markup.row(*[InlineKeyboardButton(d, callback_data="IGNORE") for d in ["Mo", "Tu", "We", "Th", "Fr", "Sa", "Su"]])
    first_day = datetime(year, month, 1)
    start_day = first_day.weekday()
    days = []
    for _ in range(start_day):
        days.append(InlineKeyboardButton(" ", callback_data="IGNORE"))
    next_month = first_day.replace(day=28) + timedelta(days=4)
    days_in_month = (next_month - timedelta(days=next_month.day)).day
    for d in range(1, days_in_month + 1):
        date_str = f"{year}-{month:02d}-{d:02d}"
        days.append(InlineKeyboardButton(str(d), callback_data=f"DAY_{date_str}"))
    while len(days) % 7 != 0:
        days.append(InlineKeyboardButton(" ", callback_data="IGNORE"))
    for i in range(0, len(days), 7):
        markup.row(*days[i:i+7])
    nav = [
        InlineKeyboardButton("<", callback_data=f"PREV_{year}-{month}"),
        InlineKeyboardButton(f"{first_day.strftime('%B')} {year}", callback_data="IGNORE"),
        InlineKeyboardButton(">", callback_data=f"NEXT_{year}-{month}")
    ]
    markup.row(*nav)
    markup.add(InlineKeyboardButton("📍 Today", callback_data=f"DAY_{datetime.today().strftime('%Y-%m-%d')}"))
    return markup

def generate_currency_selection() -> InlineKeyboardMarkup:
    markup = InlineKeyboardMarkup(row_width=3)
    for currency in AVAILABLE_CURRENCIES:
        markup.add(InlineKeyboardButton(currency, callback_data=f"CURRENCY_{currency}"))
    markup.add(InlineKeyboardButton("Done", callback_data="CURRENCY_DONE"))
    return markup

@bot.message_handler(commands=["start"])
def start_bot(message):
    if not bot:
        logger.error("Bot not initialized due to missing TELEGRAM_BOT_TOKEN")
        return
    chat_id = message.chat.id
    user_currency_preferences[chat_id] = []
    bot.send_message(
        chat_id,
        "Welcome to The Trading Nexus Bot! 🤖\nPlease select the currencies you're interested in (you can choose multiple):",
        reply_markup=generate_currency_selection()
    )

@bot.message_handler(commands=["calendar"])
def show_calendar(message):
    if not bot:
        logger.error("Bot not initialized due to missing TELEGRAM_BOT_TOKEN")
        return
    today = datetime.today()
    bot.send_message(
        message.chat.id,
        "📅 Select a date:",
        reply_markup=generate_calendar(today.year, today.month)
    )

@bot.message_handler(commands=["today"])
def send_today_news(message):
    if not bot:
        logger.error("Bot not initialized due to missing TELEGRAM_BOT_TOKEN")
        return
    today = datetime.now(timezone("Europe/Prague")).strftime("%Y-%m-%d")
    bot.send_message(message.chat.id, "📬 Fetching today's Forex news...")
    news = get_news_from_db(today, today, impact_level="high")

    header = f"🗓️ Forex News for {escape_markdown_v2(datetime.now(timezone('Europe/Prague')).strftime('%d.%m.%Y'))} \\(CET\\):\n\n"
    if news:
        events_by_time = {}
        for item in news:
            key = (item['date'], item['time'])
            if key not in events_by_time:
                events_by_time[key] = []
            events_by_time[key].append(item)

        message_parts = [header]
        for (event_date, event_time), events in sorted(events_by_time.items(), key=lambda x: x[1][0]['time']):
            event_list = [f"{event['currency']} {event['event']}" for event in events]
            part = f"⏰ Time: {event_time}\n📰 Events: {escape_markdown_v2(' & '.join(event_list))}\n"
            for event in events:
                part += (
                    f"📈 Forecast: {escape_markdown_v2(event['forecast'])}\n"
                    f"📊 Previous: {escape_markdown_v2(event['previous'])}\n"
                    f"🎯 Actual: {escape_markdown_v2(event['actual'])}\n"
                    f"🔍 ChatGPT Analysis: {escape_markdown_v2(event['analysis'])}\n\n"
                )
            part += f"{'-' * 40}\n\n"
            message_parts.append(part)
        message = "".join(message_parts)
    else:
        message = header + "✅ No news found for today with high impact.\nPlease check the website for updates."

    def send_long_message(chat_id, text):
        text = text.strip()
        if not text:
            logger.error("Attempted to send empty message")
            return
        while text:
            if len(text) <= 4096:
                part = text
                text = ""
            else:
                cut = text[:4096].rfind('\n') if '\n' in text[:4096] else 4096
                part = text[:cut].strip()
                text = text[cut:].strip()
            if part:
                try:
                    bot.send_message(chat_id, part, parse_mode='MarkdownV2', disable_web_page_preview=True)
                except telebot.apihelper.ApiTelegramException as e:
                    logger.error(f"MarkdownV2 send failed: {e}. Falling back to plain.")
                    bot.send_message(chat_id, part.replace('\\', ''))

    send_long_message(CHAT_ID, message)
    bot.send_message(message.chat.id, "✅ News sent to the channel!")

@bot.message_handler(commands=["help"])
def show_help(message):
    if not bot:
        logger.error("Bot not initialized due to missing TELEGRAM_BOT_TOKEN")
        return
    help_text = escape_markdown_v2(
        "🤖 Forex News Bot Commands:\n\n"
        "/start — Set up your currency preferences\n"
        "/today — Get today's forex news\n"
        "/calendar — Choose a date to get past news\n"
        "/help — Show this message"
    )
    bot.send_message(message.chat.id, help_text, parse_mode="MarkdownV2")

@bot.callback_query_handler(func=lambda c: c.data.startswith(("DAY_", "NEXT_", "PREV_")))
def handle_calendar(c: CallbackQuery):
    if not bot:
        logger.error("Bot not initialized due to missing TELEGRAM_BOT_TOKEN")
        return
    chat_id = c.message.chat.id
    data = c.data
    if data.startswith("DAY_"):
        date_str = data[4:]
        if datetime.strptime(date_str, "%Y-%m-%d") < datetime.today() - timedelta(days=365):
            bot.send_message(chat_id, "⚠️ Date too far in the past.")
            return
        user_selected_date[chat_id] = date_str
        markup = InlineKeyboardMarkup()
        markup.row(
            InlineKeyboardButton("🔴 High Only", callback_data="IMPACT_high"),
            InlineKeyboardButton("🟠 Medium + High", callback_data="IMPACT_medium")
        )
        bot.edit_message_text(
            chat_id=chat_id,
            message_id=c.message.message_id,
            text=f"📅 Selected date: {date_str}\nSelect news impact level:",
            reply_markup=markup
        )
    else:
        prefix, ym = data.split("_")
        year, month = map(int, ym.split("-"))
        new = datetime(year, month, 15) + timedelta(days=31) if prefix == "NEXT" else datetime(year, month, 1) - timedelta(days=1)
        bot.edit_message_reply_markup(
            chat_id=chat_id,
            message_id=c.message.message_id,
            reply_markup=generate_calendar(new.year, new.month)
        )

@bot.callback_query_handler(func=lambda c: c.data.startswith("IMPACT_"))
def handle_impact_selection(c: CallbackQuery):
    if not bot:
        logger.error("Bot not initialized due to missing TELEGRAM_BOT_TOKEN")
        return
    chat_id = c.message.chat.id
    impact = c.data.split("_")[1]
    date_str = user_selected_date.get(chat_id)
    user_selected_impact[chat_id] = impact
    if not date_str:
        bot.send_message(chat_id, "⚠️ No date selected.")
        return
    bot.send_message(
        chat_id,
        f"🔄 Fetching Forex news for *{escape_markdown_v2(date_str)}*\nImpact: *{escape_markdown_v2(impact)}*",
        parse_mode="MarkdownV2"
    )
    news = get_news_from_db(date_str, date_str, impact_level=impact)

    header = f"🗓️ Forex News for {escape_markdown_v2(date_str)} \\(CET\\):\n\n"
    if news:
        events_by_time = {}
        for item in news:
            key = (item['date'], item['time'])
            if key not in events_by_time:
                events_by_time[key] = []
            events_by_time[key].append(item)

        message_parts = [header]
        for (event_date, event_time), events in sorted(events_by_time.items(), key=lambda x: x[1][0]['time']):
            event_list = [f"{event['currency']} {event['event']}" for event in events]
            part = f"⏰ Time: {event_time}\n📰 Events: {escape_markdown_v2(' & '.join(event_list))}\n"
            for event in events:
                part += (
                    f"📈 Forecast: {escape_markdown_v2(event['forecast'])}\n"
                    f"📊 Previous: {escape_markdown_v2(event['previous'])}\n"
                    f"🎯 Actual: {escape_markdown_v2(event['actual'])}\n"
                    f"🔍 ChatGPT Analysis: {escape_markdown_v2(event['analysis'])}\n\n"
                )
            part += f"{'-' * 40}\n\n"
            message_parts.append(part)
        message = "".join(message_parts)
    else:
        message = header + f"✅ No news found for {escape_markdown_v2(date_str)} with impact: {escape_markdown_v2(impact)}\nPlease check the website for updates."

    def send_long_message(chat_id, text):
        text = text.strip()
        if not text:
            logger.error("Attempted to send empty message")
            return
        while text:
            if len(text) <= 4096:
                part = text
                text = ""
            else:
                cut = text[:4096].rfind('\n') if '\n' in text[:4096] else 4096
                part = text[:cut].strip()
                text = text[cut:].strip()
            if part:
                try:
                    bot.send_message(chat_id, part, parse_mode='MarkdownV2', disable_web_page_preview=True)
                except telebot.apihelper.ApiTelegramException as e:
                    logger.error(f"MarkdownV2 send failed: {e}. Falling back to plain.")
                    bot.send_message(chat_id, part.replace('\\', ''))

    send_long_message(CHAT_ID, message)
    bot.send_message(chat_id, "✅ News sent to the channel!")

@bot.callback_query_handler(func=lambda c: c.data.startswith("CURRENCY_"))
def handle_currency_selection(c: CallbackQuery):
    if not bot:
        logger.error("Bot not initialized due to missing TELEGRAM_BOT_TOKEN")
        return
    chat_id = c.message.chat.id
    data = c.data

    if data == "CURRENCY_DONE":
        if chat_id in user_currency_preferences and user_currency_preferences[chat_id]:
            selected = ", ".join(user_currency_preferences[chat_id])
            bot.edit_message_text(
                chat_id=chat_id,
                message_id=c.message.message_id,
                text=f"✅ You selected: {selected}\nYou will receive notifications for these currencies. Use /help to see available commands."
            )
        else:
            bot.edit_message_text(
                chat_id=chat_id,
                message_id=c.message.message_id,
                text="⚠️ Please select at least one currency before proceeding."
            )
    else:
        currency = data.split("_")[1]
        if chat_id not in user_currency_preferences:
            user_currency_preferences[chat_id] = []
        if currency not in user_currency_preferences[chat_id]:
            user_currency_preferences[chat_id].append(currency)
        selected = ", ".join(user_currency_preferences[chat_id]) if user_currency_preferences[chat_id] else "None"
        bot.edit_message_text(
            chat_id=chat_id,
            message_id=c.message.message_id,
            text=f"Selected currencies: {selected}\nChoose more or press Done:",
            reply_markup=generate_currency_selection()
        )

# Flask routes
@app.route("/", methods=["GET"])
def index():
    return "🤖 Forex bot is online!", 200

@app.route("/ping", methods=["GET"])
def ping():
    logger.info("Received ping request")
    return "OK", 200

@app.route("/webhook", methods=["POST"])
def webhook():
    if not bot:
        logger.error("Webhook not available: Bot not initialized")
        return jsonify({"error": "Bot not initialized"}), 503
    try:
        update = telebot.types.Update.de_json(request.get_json())
        bot.process_new_updates([update])
        return "OK", 200
    except Exception as e:
        logger.error(f"Webhook error: {e}")
        return jsonify({"error": str(e)}), 500

def setup_webhook():
    if not bot:
        logger.error("Cannot set webhook: Bot not initialized")
        return
    try:
        webhook_url = f"https://{os.getenv('RENDER_EXTERNAL_HOSTNAME')}/webhook"
        render_hostname = os.getenv('RENDER_EXTERNAL_HOSTNAME')
        if render_hostname and render_hostname.strip():
            logger.info(f"Attempting to set webhook to {webhook_url}")
            bot.remove_webhook()
            logger.info("Removed existing webhook")
            bot.set_webhook(url=webhook_url)
            logger.info(f"Webhook successfully set to {webhook_url}")
        else:
            logger.info("RENDER_EXTERNAL_HOSTNAME not set or empty, starting polling in a separate thread")
            bot.remove_webhook()
            polling_thread = threading.Thread(target=bot.polling, kwargs={"none_stop": True}, daemon=True)
            polling_thread.start()
            logger.info("Polling started in a separate thread")
    except Exception as e:
        logger.error(f"Failed to set webhook or polling: {e}")
        try:
            webhook_info = bot.get_webhook_info()
            logger.info(f"Current webhook info: {webhook_info}")
        except Exception as e2:
            logger.error(f"Failed to get webhook info: {e2}")

# Setup on startup
logger.info("Checking required environment variables")
required_vars = ["TELEGRAM_BOT_TOKEN", "TELEGRAM_CHAT_ID"]
missing_vars = [var for var in required_vars if not os.getenv(var)]
if missing_vars:
    logger.error(f"Missing required environment variables: {', '.join(missing_vars)}")
else:
    logger.info("All required environment variables are set")
    if bot:
        logger.info("Bot is initialized, setting up webhook or polling")
        setup_webhook()
    else:
        logger.warning("Skipping bot setup due to missing TELEGRAM_BOT_TOKEN")

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
