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

# Logging setup
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[
        logging.FileHandler('bot.log'),
        logging.StreamHandler()
    ]
)

app = Flask(__name__)

# Check TELEGRAM_BOT_TOKEN
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
if not TELEGRAM_BOT_TOKEN:
    logging.error("TELEGRAM_BOT_TOKEN is not set. Bot functionality will be disabled.")
    bot = None
else:
    bot = telebot.TeleBot(TELEGRAM_BOT_TOKEN)
    logging.info("Telegram bot initialized successfully")

CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")
if not CHAT_ID:
    logging.error("TELEGRAM_CHAT_ID is not set. Bot functionality will be disabled.")
else:
    logging.info("TELEGRAM_CHAT_ID is set")

user_selected_date = {}
user_selected_impact = {}
user_currency_preferences = {}

# Список доступных валют
AVAILABLE_CURRENCIES = ["EUR", "USD", "JPY", "GBP", "CAD"]

# Функция для получения новостей из базы данных
def get_news_from_db(start_date, end_date, impact_level="high"):
    conn = sqlite3.connect('news.db')
    c = conn.cursor()
    if impact_level == "medium":
        c.execute('''
            SELECT date, time, currency, event, forecast, previous, actual, analysis
            FROM news
            WHERE date BETWEEN ? AND ? AND impact IN ('high', 'medium')
        ''', (start_date, end_date))
    else:
        c.execute('''
            SELECT date, time, currency, event, forecast, previous, actual, analysis
            FROM news
            WHERE date BETWEEN ? AND ? AND impact = ?
        ''', (start_date, end_date, impact_level))
    rows = c.fetchall()
    conn.close()
    return [{"date": row[0], "time": row[1], "currency": row[2], "event": row[3], "forecast": row[4], "previous": row[5], "actual": row[6], "analysis": row[7]} for row in rows]

# APScheduler setup
scheduler = BackgroundScheduler()

def ping_self():
    """Sends an HTTP request to /ping to prevent the app from sleeping on Render.com"""
    try:
        base_url = f"https://{os.getenv('RENDER_EXTERNAL_HOSTNAME')}"
        ping_url = f"{base_url}/ping"
        response = requests.get(ping_url, timeout=10)
        if response.status_code == 200:
            logging.info(f"Ping successful: {ping_url}")
        else:
            logging.error(f"Ping failed: {ping_url}, status code: {response.status_code}")
    except Exception as e:
        logging.error(f"Ping error: {e}")

# Функция для проверки и отправки уведомлений
def check_and_send_notifications():
    if not bot or not CHAT_ID:
        logging.error("Cannot send notifications: Bot or CHAT_ID not configured")
        return

    try:
        now = datetime.now(timezone("Europe/Prague"))
        start_date = now.strftime("%Y-%m-%d")
        end_date = (now + timedelta(days=3)).strftime("%Y-%m-%d")  # Проверяем новости на 3 дня вперед

        # Получаем новости из базы
        news_items = get_news_from_db(start_date, end_date, impact_level="high")

        # Группируем новости по времени
        events_by_time = {}
        for news_item in news_items:
            event_date = news_item['date']
            event_time = news_item['time'].replace("\\", "")
            currency = news_item['currency'].replace("\\", "")
            event = news_item['event'].replace("\\", "")
            forecast = news_item['forecast'].replace("\\", "")
            previous = news_item['previous'].replace("\\", "")
            actual = news_item['actual'].replace("\\", "")
            key = (event_date, event_time)

            if key not in events_by_time:
                events_by_time[key] = []
            events_by_time[key].append((currency, event, forecast, previous, actual))

        for (event_date, event_time), events in events_by_time.items():
            try:
                event_datetime = datetime.strptime(f"{event_date} {event_time}", "%Y-%m-%d %H:%M")
                event_datetime = timezone("Europe/Prague").localize(event_datetime)
                time_diff = (event_datetime - now).total_seconds() / 60  # Разница в минутах
            except ValueError:
                logging.warning(f"Could not parse event time: {event_time} for date {event_date}")
                continue

            # Проверяем, осталось ли 20 минут до события
            if 19 <= time_diff <= 21:  # Окно в 2 минуты для уведомлений
                # Формируем сообщение с группировкой
                event_list = [f"{currency} {event}" for currency, event, _, _, _ in events]
                forecast_list = [forecast for _, _, forecast, _, _ in events]
                previous_list = [previous for _, _, _, previous, _ in events]
                actual_list = [actual for _, _, _, _, actual in events]
                event_str = " & ".join(event_list)
                forecast_str = " & ".join(forecast_list)
                previous_str = " & ".join(previous_list)
                actual_str = " & ".join(actual_list)
                message = (
                    f"⏰ Reminder: In 20 minutes, there will be a news event!\n"
                    f"📰 Events: {event_str}\n"
                    f"📈 Forecast: {forecast_str}\n"
                    f"📊 Previous: {previous_str}\n"
                    f"🎯 Actual: {actual_str}\n"
                    f"📅 Time: {event_time}"
                )

                # Проверяем, интересует ли валюта пользователя
                for chat_id, currencies in user_currency_preferences.items():
                    if any(currency in currencies for currency, _, _, _, _ in events):
                        try:
                            bot.send_message(chat_id, message, parse_mode='MarkdownV2')
                            logging.info(f"Sent notification to chat {chat_id} for events: {event_str}")
                        except Exception as e:
                            logging.error(f"Failed to send notification to chat {chat_id}: {e}")
    except Exception as e:
        logging.error(f"Error in check_and_send_notifications: {e}")

# Настройка задач APScheduler
if os.getenv('RENDER_EXTERNAL_HOSTNAME'):
    scheduler.add_job(ping_self, 'interval', minutes=5)
    scheduler.add_job(check_and_send_notifications, 'interval', minutes=5)
    scheduler.start()
    logging.info("Started APScheduler for self-ping and notifications")
else:
    logging.warning("RENDER_EXTERNAL_HOSTNAME not set, skipping scheduler setup")

# --- Telegram bot functions ---
def escape_markdown_v2(text: str) -> str:
    if not text:
        return "N/A"
    special = ['_', '*', '[', ']', '(', ')', '~', '`', '>', '#', '+', '-', '=', '|', '{', '}', '.', '!']
    for ch in special:
        text = text.replace(ch, f"\\{ch}")
    return text

def generate_calendar(year: int, month: int):
    markup = InlineKeyboardMarkup(row_width=7)
    markup.add(*[InlineKeyboardButton(d, callback_data="IGNORE") for d in ["Mo","Tu","We","Th","Fr","Sa","Su"]])
    first_day = datetime(year, month, 1)
    start_day = first_day.weekday()
    days = []
    for _ in range(start_day):
        days.append(InlineKeyboardButton(" ", callback_data="IGNORE"))
    next_month = first_day.replace(day=28) + timedelta(days=4)
    days_in_month = (next_month - timedelta(days=next_month.day)).day
    for d in range(1, days_in_month+1):
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

def generate_currency_selection():
    markup = InlineKeyboardMarkup(row_width=3)
    for currency in AVAILABLE_CURRENCIES:
        markup.add(InlineKeyboardButton(currency, callback_data=f"CURRENCY_{currency}"))
    markup.add(InlineKeyboardButton("Done", callback_data="CURRENCY_DONE"))
    return markup

@bot.message_handler(commands=["start"])
def start_bot(message):
    if not bot:
        logging.error("Bot not initialized due to missing TELEGRAM_BOT_TOKEN")
        return
    try:
        chat_id = message.chat.id
        user_currency_preferences[chat_id] = []
        bot.send_message(
            chat_id,
            "Welcome to The Trading Nexus Bot! 🤖\nPlease select the currencies you're interested in (you can choose multiple):",
            reply_markup=generate_currency_selection()
        )
    except Exception as e:
        logging.error(f"Error in /start: {e}")
        bot.send_message(message.chat.id, "⚠️ Error starting the bot.")

@bot.message_handler(commands=["calendar"])
def show_calendar(message):
    if not bot:
        logging.error("Bot not initialized due to missing TELEGRAM_BOT_TOKEN")
        return
    try:
        today = datetime.today()
        bot.send_message(
            message.chat.id,
            "📅 Select a date:",
            reply_markup=generate_calendar(today.year, today.month)
        )
    except Exception as e:
        logging.error(f"Error in /calendar: {e}")
        bot.send_message(message.chat.id, "⚠️ Error showing calendar.")

@bot.message_handler(commands=["today"])
def send_today_news(message):
    if not bot:
        logging.error("Bot not initialized due to missing TELEGRAM_BOT_TOKEN")
        return
    try:
        today = datetime.now(timezone("Europe/Prague")).strftime("%Y-%m-%d")
        bot.send_message(message.chat.id, "📬 Fetching today's Forex news...")
        news = get_news_from_db(today, today, impact_level="high")

        scraped_display_esc = escape_markdown_v2(datetime.now(timezone("Europe/Prague")).strftime("%d.%m.%Y"))
        header = f"🗓️ Forex News for {scraped_display_esc} \\(CET\\):\n\n"

        if news:
            # Группируем новости по времени
            events_by_time = {}
            for item in news:
                key = (item['date'], item['time'])
                if key not in events_by_time:
                    events_by_time[key] = []
                events_by_time[key].append(item)

            message_parts = [header]
            for (event_date, event_time), events in sorted(events_by_time.items(), key=lambda x: x[1][0]['time']):
                event_list = [f"{event['currency']} {event['event']}" for event in events]
                event_str = " & ".join(event_list)
                part = (
                    f"⏰ Time: {event_time}\n"
                    f"📰 Events: {event_str}\n"
                )
                for event in events:
                    part += (
                        f"📈 Forecast: {event['forecast']}\n"
                        f"📊 Previous: {event['previous']}\n"
                        f"🎯 Actual: {event['actual']}\n"
                        f"🔍 ChatGPT Analysis: {event['analysis']}\n\n"
                    )
                part += f"{'-' * 40}\n\n"
                message_parts.append(part)
            message = "".join(message_parts)
        else:
            message = header + "✅ No news found for today with high impact.\nPlease check the website for updates."

        def send_long_message(chat_id, message):
            message = message.strip()
            if not message:
                logging.error("Attempted to send empty message")
                return
            while message:
                if len(message) <= 4096:
                    part = message
                    message = ""
                else:
                    cut = message[:4096].rfind('\n') if '\n' in message[:4096] else 4096
                    part = message[:cut].strip()
                    message = message[cut:].strip()
                if not part:
                    logging.warning(f"Skipping empty message part: {message[:50]}...")
                    continue
                try:
                    bot.send_message(chat_id, part, parse_mode='MarkdownV2')
                except telebot.apihelper.ApiTelegramException as e:
                    logging.error(f"MarkdownV2 send failed: {e}. Falling back to plain.")
                    plain_part = part.replace('\\', '')
                    bot.send_message(chat_id, plain_part)

        send_long_message(CHAT_ID, message)
        bot.send_message(message.chat.id, "✅ News sent to the channel!")
    except Exception as e:
        logging.error(f"Error in /today: {e}")
        bot.send_message(message.chat.id, "⚠️ Error fetching news.")

@bot.message_handler(commands=["help"])
def show_help(message):
    if not bot:
        logging.error("Bot not initialized due to missing TELEGRAM_BOT_TOKEN")
        return
    try:
        help_text = escape_markdown_v2(
            "🤖 Forex News Bot Commands:\n\n"
            "/start — Set up your currency preferences\n"
            "/today — Get today's forex news\n"
            "/calendar — Choose a date to get past news\n"
            "/help — Show this message"
        )
        bot.send_message(message.chat.id, help_text, parse_mode="MarkdownV2")
    except Exception as e:
        logging.error(f"Error in /help: {e}")
        bot.send_message(message.chat.id, "⚠️ Error showing help.")

@bot.callback_query_handler(func=lambda c: c.data.startswith(("DAY_","NEXT_","PREV_")))
def handle_calendar(c: CallbackQuery):
    if not bot:
        logging.error("Bot not initialized due to missing TELEGRAM_BOT_TOKEN")
        return
    try:
        chat_id = c.message.chat.id
        data = c.data
        if data.startswith("DAY_"):
            date_str = data[4:]
            if datetime.strptime(date_str, "%Y-%m-%d") < datetime.today() - timedelta(days=365):
                bot.send_message(chat_id, "⚠️ Date too far in the past.")
                return
            user_selected_date[chat_id] = date_str
            markup = InlineKeyboardMarkup()
            markup.add(
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
            if prefix == "NEXT":
                new = datetime(year, month, 15) + timedelta(days=31)
            else:
                new = datetime(year, month, 1) - timedelta(days=1)
            bot.edit_message_reply_markup(
                chat_id=chat_id,
                message_id=c.message.message_id,
                reply_markup=generate_calendar(new.year, new.month)
            )
    except Exception as e:
        logging.error(f"Error in handle_calendar: {e}")
        bot.send_message(c.message.chat.id, "⚠️ Error processing calendar.")

@bot.callback_query_handler(func=lambda c: c.data.startswith("IMPACT_"))
def handle_impact_selection(c: CallbackQuery):
    if not bot:
        logging.error("Bot not initialized due to missing TELEGRAM_BOT_TOKEN")
        return
    try:
        chat_id = c.message.chat.id
        impact = c.data.split("_")[1]
        date_str = user_selected_date.get(chat_id)
        user_selected_impact[chat_id] = impact
        if not date_str:
            bot.send_message(chat_id, "⚠️ No date selected.")
            return
        date_str_esc = escape_markdown_v2(date_str)
        impact_esc = escape_markdown_v2(impact)
        bot.send_message(
            chat_id,
            f"🔄 Fetching Forex news for *{date_str_esc}*\nImpact: *{impact_esc}*",
            parse_mode="MarkdownV2"
        )
        news = get_news_from_db(date_str, date_str, impact_level=impact)

        header = f"🗓️ Forex News for {date_str_esc} \\(CET\\):\n\n"
        if news:
            # Группируем новости по времени
            events_by_time = {}
            for item in news:
                key = (item['date'], item['time'])
                if key not in events_by_time:
                    events_by_time[key] = []
                events_by_time[key].append(item)

            message_parts = [header]
            for (event_date, event_time), events in sorted(events_by_time.items(), key=lambda x: x[1][0]['time']):
                event_list = [f"{event['currency']} {event['event']}" for event in events]
                event_str = " & ".join(event_list)
                part = (
                    f"⏰ Time: {event_time}\n"
                    f"📰 Events: {event_str}\n"
                )
                for event in events:
                    part += (
                        f"📈 Forecast: {event['forecast']}\n"
                        f"📊 Previous: {event['previous']}\n"
                        f"🎯 Actual: {event['actual']}\n"
                        f"🔍 ChatGPT Analysis: {event['analysis']}\n\n"
                    )
                part += f"{'-' * 40}\n\n"
                message_parts.append(part)
            message = "".join(message_parts)
        else:
            message = header + f"✅ No news found for {date_str_esc} with impact: {impact_esc}\nPlease check the website for updates."

        def send_long_message(chat_id, message):
            message = message.strip()
            if not message:
                logging.error("Attempted to send empty message")
                return
            while message:
                if len(message) <= 4096:
                    part = message
                    message = ""
                else:
                    cut = message[:4096].rfind('\n') if '\n' in message[:4096] else 4096
                    part = message[:cut].strip()
                    message = message[cut:].strip()
                if not part:
                    logging.warning(f"Skipping empty message part: {message[:50]}...")
                    continue
                try:
                    bot.send_message(chat_id, part, parse_mode='MarkdownV2')
                except telebot.apihelper.ApiTelegramException as e:
                    logging.error(f"MarkdownV2 send failed: {e}. Falling back to plain.")
                    plain_part = part.replace('\\', '')
                    bot.send_message(chat_id, plain_part)

        send_long_message(CHAT_ID, message)
        bot.send_message(chat_id, "✅ News sent to the channel!")
    except Exception as e:
        logging.error(f"Error in handle_impact_selection: {e}")
        bot.send_message(chat_id, "⚠️ Error fetching news.")

@bot.callback_query_handler(func=lambda c: c.data.startswith("CURRENCY_"))
def handle_currency_selection(c: CallbackQuery):
    if not bot:
        logging.error("Bot not initialized due to missing TELEGRAM_BOT_TOKEN")
        return
    try:
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
    except Exception as e:
        logging.error(f"Error in handle_currency_selection: {e}")
        bot.send_message(chat_id, "⚠️ Error selecting currencies.")

# --- Flask routes ---
@app.route("/", methods=["GET"])
def index():
    return "🤖 Forex bot is online!", 200

@app.route("/ping", methods=["GET"])
def ping():
    logging.info("Received ping request")
    return "OK", 200

@app.route("/webhook", methods=["POST"])
def webhook():
    if not bot:
        logging.error("Webhook not available: Bot not initialized")
        return "Bot not initialized", 503
    try:
        update = telebot.types.Update.de_json(request.get_json())
        bot.process_new_updates([update])
        return "OK", 200
    except Exception as e:
        logging.error(f"Webhook error: {e}")
        return "Error", 500

# Webhook setup on startup
def setup_webhook():
    if not bot:
        logging.error("Cannot set webhook: Bot not initialized")
        return
    try:
        webhook_url = f"https://{os.getenv('RENDER_EXTERNAL_HOSTNAME')}/webhook"
        render_hostname = os.getenv('RENDER_EXTERNAL_HOSTNAME')
        if render_hostname and render_hostname.strip():  # Проверяем, что строка не пустая
            logging.info(f"Attempting to set webhook to {webhook_url}")
            bot.remove_webhook()
            logging.info("Removed existing webhook")
            bot.set_webhook(url=webhook_url)
            logging.info(f"Webhook successfully set to {webhook_url}")
        else:
            logging.info("RENDER_EXTERNAL_HOSTNAME not set or empty, starting polling in a separate thread")
            bot.remove_webhook()
            polling_thread = threading.Thread(target=bot.polling, kwargs={"none_stop": True}, daemon=True)
            polling_thread.start()
            logging.info("Polling started in a separate thread")
    except Exception as e:
        logging.error(f"Failed to set webhook or polling: {e}")
        try:
            webhook_info = bot.get_webhook_info()
            logging.info(f"Current webhook info: {webhook_info}")
        except Exception as e2:
            logging.error(f"Failed to get webhook info: {e2}")

# Check required environment variables and setup webhook
logging.info("Checking required environment variables")
required_vars = ["TELEGRAM_BOT_TOKEN", "TELEGRAM_CHAT_ID"]
missing_vars = [var for var in required_vars if not os.getenv(var)]
if missing_vars:
    logging.error(f"Missing required environment variables: {', '.join(missing_vars)}")
else:
    logging.info("All required environment variables are set")
    if bot:
        logging.info("Bot is initialized, setting up webhook or polling")
        setup_webhook()
    else:
        logging.warning("Skipping bot setup due to missing TELEGRAM_BOT_TOKEN")

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
