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
import time
import random
from playwright.sync_api import sync_playwright, TimeoutError as PlaywrightTimeoutError
from bs4 import BeautifulSoup

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

# List of User-Agents for rotation
USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/92.0.4515.159 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:89.0) Gecko/20100101 Firefox/89.0",
]

# Impact mapping: CSS suffix to human-readable category
IMPACT_MAP = {
    "gra": "NON-ECONOMIC",
    "yel": "LOW",
    "ora": "MEDIUM",
    "red": "HIGH",
}

# Database helper
class Database:
    def __init__(self, db_name='news.db'):
        self.db_name = db_name
        self.init_db()

    def init_db(self):
        """Initialize the database and create the news table if it doesn't exist."""
        with sqlite3.connect(self.db_name) as conn:
            c = conn.cursor()
            c.execute('''
                CREATE TABLE IF NOT EXISTS news (
                    date TEXT,
                    time TEXT,
                    currency TEXT,
                    event TEXT,
                    forecast TEXT,
                    previous TEXT,
                    actual TEXT,
                    impact TEXT,
                    analysis TEXT,
                    UNIQUE(date, time, currency, event)
                )
            ''')
            # Ensure existing data has standardized impact values
            c.execute("UPDATE news SET impact = UPPER(TRIM(impact))")
            conn.commit()
        logger.info("Database initialized successfully.")

    def check_duplicate_event(self, date, time, currency, event):
        """Check if an event already exists in the database."""
        with sqlite3.connect(self.db_name) as conn:
            c = conn.cursor()
            c.execute('''
                SELECT COUNT(*) FROM news
                WHERE date = ? AND time = ? AND currency = ? AND event = ?
            ''', (date, time, currency, event))
            count = c.fetchone()[0]
        return count > 0

    def insert_event(self, event_data):
        """Insert or update an event in the database."""
        with sqlite3.connect(self.db_name) as conn:
            c = conn.cursor()
            c.execute('''
                INSERT OR REPLACE INTO news (date, time, currency, event, forecast, previous, actual, impact, analysis)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', event_data)
            conn.commit()
        logger.info(f"Inserted/Updated event: {event_data[0]}, {event_data[1]}, {event_data[2]}, {event_data[3]}")

# Function to perform ChatGPT analysis
def analyze_event(events: List[dict]):
    """Analyze multiple events with the same currency and time as one big news event."""
    if not events or not os.getenv("OPENAI_API_KEY"):
        return "⚠️ ChatGPT analysis skipped"

    try:
        # Combine event details into a single prompt
        currency = events[0]['currency']
        event_list = [event['event'] for event in events]
        forecast_list = [event['forecast'] for event in events]
        previous_list = [event['previous'] for event in events]
        actual_list = [event['actual'] for event in events]

        prompt = (
            f"Analyze the potential combined impact of the following Forex events on the {currency} currency market:\n"
            f"Events: {', '.join(event_list)}\n"
            f"Forecasts: {', '.join(forecast_list)}\n"
            f"Previous: {', '.join(previous_list)}\n"
            f"Actual: {', '.join(actual_list)}"
        )
        headers = {
            "Authorization": f"Bearer {os.getenv('OPENAI_API_KEY')}",
            "Content-Type": "application/json"
        }
        data = {
            "model": "gpt-3.5-turbo",
            "messages": [{"role": "user", "content": prompt}],
            "max_tokens": 150
        }
        response = requests.post("https://api.openai.com/v1/chat/completions", headers=headers, json=data, timeout=10)
        response.raise_for_status()
        analysis = response.json()["choices"][0]["message"]["content"].strip()
        return analysis
    except Exception as e:
        logger.error(f"ChatGPT analysis failed: {e}")
        return "⚠️ ChatGPT analysis failed"

def scrape_forex_news(start_date: str, end_date: str) -> List[dict]:
    """Scrape Forex news from the web for the given date range."""
    logger.info(f"Scraping Forex news for range: {start_date} to {end_date}")
    db = Database()
    scraped_events = []

    start = datetime.strptime(start_date, "%Y-%m-%d")
    end = datetime.strptime(end_date, "%Y-%m-%d")
    current = start

    with sync_playwright() as p:
        browser = p.chromium.launch(
            headless=True,
            args=[
                "--disable-blink-features=AutomationControlled",
                "--no-sandbox",
                "--disable-dev-shm-usage",
                "--disable-gpu",
            ]
        )
        try:
            while current <= end:
                date_str = current.strftime("%Y-%m-%d")
                logger.info(f"Scraping data for date: {date_str}")

                context = browser.new_context(
                    user_agent=random.choice(USER_AGENTS),
                    viewport={"width": 1280, "height": 720},
                    java_script_enabled=True,
                    bypass_csp=True,
                )
                context.set_extra_http_headers({
                    "Accept-Language": "en-US,en;q=0.9",
                    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
                    "Connection": "keep-alive",
                    "Upgrade-Insecure-Requests": "1",
                })
                page = context.new_page()

                url = f"https://www.forexfactory.com/calendar?day={current.strftime('%b')}{current.day}.{current.year}"
                logger.debug(f"Navigating to URL: {url}")

                try:
                    page.goto(url, timeout=60000)
                    page.wait_for_load_state("networkidle", timeout=60000)
                except PlaywrightTimeoutError as e:
                    logger.warning(f"Networkidle failed on {date_str}: {e}. Falling back to domcontentloaded.")
                    try:
                        page.wait_for_load_state("domcontentloaded", timeout=60000)
                    except PlaywrightTimeoutError as e:
                        logger.error(f"Failed loading {date_str}: {e}. Skipping.")
                        current += timedelta(days=1)
                        continue

                time.sleep(random.uniform(3, 5))
                html = page.content()
                if "Just a moment..." in html:
                    logger.error(f"Blocked by CAPTCHA on {date_str}. Skipping.")
                    current += timedelta(days=1)
                    continue

                soup = BeautifulSoup(html, "html.parser")
                table = soup.find("table", class_="calendar__table")
                if not table:
                    logger.error(f"No calendar table on {date_str}. Skipping.")
                    current += timedelta(days=1)
                    continue

                rows = table.find_all("tr", class_=lambda c: c and "calendar__row" in c)
                rows = [r for r in rows if r.get("data-event-id")]
                logger.info(f"Found {len(rows)} events for {date_str}")

                for row in rows:
                    time_cell = row.find("td", class_=lambda c: c and ("calendar__time" in c or "--time" in c))
                    raw_time = time_cell.text.strip() if time_cell else None
                    if not raw_time or raw_time.lower() == "all day":
                        continue
                    try:
                        event_time = datetime.strptime(raw_time, "%I:%M%p").strftime("%H:%M")
                    except ValueError:
                        continue

                    currency_td = row.find("td", class_=lambda c: c and "calendar__currency" in c)
                    currency = currency_td.text.strip() if currency_td else ""
                    if not currency:
                        continue

                    event_td = row.find("td", class_=lambda c: c and "calendar__event" in c)
                    event = event_td.text.strip() if event_td else ""
                    if not event:
                        continue

                    if db.check_duplicate_event(date_str, event_time, currency, event):
                        continue

                    forecast = row.find("td", class_=lambda c: c and "calendar__forecast" in c)
                    forecast = forecast.text.strip() if forecast else "N/A"
                    previous = row.find("td", class_=lambda c: c and "calendar__previous" in c)
                    previous = previous.text.strip() if previous else "N/A"
                    actual = row.find("td", class_=lambda c: c and "calendar__actual" in c)
                    actual = actual.text.strip() if actual else "N/A"

                    impact = "N/A"
                    impact_td = row.find("td", class_=lambda c: c and "calendar__impact" in c)
                    if impact_td:
                        span = impact_td.find("span", class_=lambda cl: cl and cl.startswith("icon--ff-impact-"))
                        if span:
                            cls = next((cl for cl in span["class"] if cl.startswith("icon--ff-impact-")), "")
                            code = cls.rsplit("-", 1)[-1]
                            impact = IMPACT_MAP.get(code, "N/A")
                    logger.debug(f"Scraped event impact: {impact} for {event}")

                    analysis = analyze_event([{"currency": currency, "event": event, "forecast": forecast,
                                             "previous": previous, "actual": actual}])
                    event_data = (date_str, event_time, currency, event, forecast, previous, actual, impact.upper(), analysis)

                    try:
                        db.insert_event(event_data)
                        scraped_events.append({
                            "date": date_str,
                            "time": event_time,
                            "currency": currency,
                            "event": event,
                            "forecast": forecast,
                            "previous": previous,
                            "actual": actual,
                            "impact": impact.upper(),
                            "analysis": analysis
                        })
                    except Exception as e:
                        logger.error(f"Insert failed for {date_str} {event}: {e}")

                page.close()
                current += timedelta(days=1)

        except Exception as e:
            logger.error(f"Scraping failed overall: {e}")
        finally:
            browser.close()
            logger.info("Browser closed.")

    return scraped_events

def get_news_from_db(start_date: str, end_date: str, impact_level: str = "high") -> List[dict]:
    """Fetch news from the database with the given date range and impact level; scrape if not found."""
    try:
        with sqlite3.connect('news.db') as conn:
            c = conn.cursor()
            query = '''
                SELECT date, time, currency, event, forecast, previous, actual, impact, analysis
                FROM news
                WHERE date BETWEEN ? AND ? AND UPPER(TRIM(impact)) = ?
            '''
            params = (start_date, end_date, impact_level.upper())
            if impact_level.lower() == "medium":
                query = '''
                    SELECT date, time, currency, event, forecast, previous, actual, impact, analysis
                    FROM news
                    WHERE date BETWEEN ? AND ? AND UPPER(TRIM(impact)) IN ('HIGH', 'MEDIUM')
                '''
            c.execute(query, params)
            rows = c.fetchall()
            if rows:
                news_items = [{"date": row[0], "time": row[1], "currency": row[2], "event": row[3], "forecast": row[4],
                               "previous": row[5], "actual": row[6], "impact": row[7], "analysis": row[8]} for row in rows]
                logger.info(f"Found {len(news_items)} events in database for {start_date} to {end_date} with impact {impact_level}")
                return news_items
    except sqlite3.Error as e:
        logger.error(f"Database error: {e}")

    # If no data found in the database, scrape from the web
    logger.info(f"No data found in database for {start_date} to {end_date} with impact {impact_level}. Scraping from web...")
    scraped_events = scrape_forex_news(start_date, end_date)

    # Filter scraped events by impact level
    filtered_events = []
    for event in scraped_events:
        logger.debug(f"Filtering scraped event: {event['event']}, impact: {event['impact']}")
        if impact_level.lower() == "medium":
            if event['impact'] in ('HIGH', 'MEDIUM'):
                filtered_events.append(event)
        elif event['impact'] == impact_level.upper():
            filtered_events.append(event)
    logger.info(f"After filtering, found {len(filtered_events)} scraped events with impact {impact_level}")

    return filtered_events

def escape_markdown_v2(text: str) -> str:
    """Escape special characters for MarkdownV2, including periods."""
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

    # Group events by currency and time
    events_by_key: Dict[Tuple[str, str, str], List[dict]] = {}
    for news_item in news_items:
        key = (news_item['date'], news_item['time'], news_item['currency'])
        if key not in events_by_key:
            events_by_key[key] = []
        events_by_key[key].append(news_item)

    for (event_date, event_time, currency), events in events_by_key.items():
        try:
            event_datetime = timezone("Europe/Prague").localize(datetime.strptime(f"{event_date} {event_time}", "%Y-%m-%d %H:%M"))
            time_diff = (event_datetime - now).total_seconds() / 60
        except ValueError as e:
            logger.warning(f"Could not parse event time: {event_time} for date {event_date}, error: {e}")
            continue

        if 19 <= time_diff <= 21:
            event_list = [event['event'] for event in events]
            forecast_list = [event['forecast'] for event in events]
            previous_list = [event['previous'] for event in events]
            actual_list = [event['actual'] for event in events]
            combined_analysis = analyze_event(events)

            message = (
                f"⏰ Reminder: In 20 minutes, there will be a news event!\n"
                f"📰 Events: {escape_markdown_v2(' & '.join(event_list))}\n"
                f"📈 Forecast: {escape_markdown_v2(' & '.join(forecast_list))}\n"
                f"📊 Previous: {escape_markdown_v2(' & '.join(previous_list))}\n"
                f"🎯 Actual: {escape_markdown_v2(' & '.join(actual_list))}\n"
                f"🔍 Combined ChatGPT Analysis: {escape_markdown_v2(combined_analysis)}\n"
                f"📅 Time: {escape_markdown_v2(event_time)}"
            )

            for chat_id, currencies in user_currency_preferences.items():
                if currency in currencies:
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

    # Format the date separately to avoid f-string backslash issue
    formatted_date = datetime.now(timezone('Europe/Prague')).strftime('%d.%m.%Y')
    header = f"🗓️ Forex News for {escape_markdown_v2(formatted_date)} \\(CET\\):\n\n"
    if news:
        # Group events by currency and time
        events_by_key: Dict[Tuple[str, str, str], List[dict]] = {}
        for item in news:
            key = (item['date'], item['time'], item['currency'])
            if key not in events_by_key:
                events_by_key[key] = []
            events_by_key[key].append(item)

        message_parts = [header]
        for (event_date, event_time, currency), events in sorted(events_by_key.items(), key=lambda x: x[1][0]['time']):
            event_list = [event['event'] for event in events]
            forecast_list = [event['forecast'] for event in events]
            previous_list = [event['previous'] for event in events]
            actual_list = [event['actual'] for event in events]
            combined_analysis = analyze_event(events)

            part = f"⏰ Time: {event_time}\n💱 Currency: {currency}\n📰 Events: {escape_markdown_v2(' & '.join(event_list))}\n"
            part += (
                f"📈 Forecast: {escape_markdown_v2(' & '.join(forecast_list))}\n"
                f"📊 Previous: {escape_markdown_v2(' & '.join(previous_list))}\n"
                f"🎯 Actual: {escape_markdown_v2(' & '.join(actual_list))}\n"
                f"🔍 Combined ChatGPT Analysis: {escape_markdown_v2(combined_analysis)}\n"
                f"💥 Impact: {escape_markdown_v2(events[0]['impact'])}\n\n"
            )
            part += f"{'-' * 40}\n\n"
            message_parts.append(part)
        message = "".join(message_parts)
    else:
        message = header + f"✅ No news found for {escape_markdown_v2(today)} with impact: high\nPlease check the website for updates."

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
        # Group events by currency and time
        events_by_key: Dict[Tuple[str, str, str], List[dict]] = {}
        for item in news:
            key = (item['date'], item['time'], item['currency'])
            if key not in events_by_key:
                events_by_key[key] = []
            events_by_key[key].append(item)

        message_parts = [header]
        for (event_date, event_time, currency), events in sorted(events_by_key.items(), key=lambda x: x[1][0]['time']):
            event_list = [event['event'] for event in events]
            forecast_list = [event['forecast'] for event in events]
            previous_list = [event['previous'] for event in events]
            actual_list = [event['actual'] for event in events]
            combined_analysis = analyze_event(events)

            part = f"⏰ Time: {event_time}\n💱 Currency: {currency}\n📰 Events: {escape_markdown_v2(' & '.join(event_list))}\n"
            part += (
                f"📈 Forecast: {escape_markdown_v2(' & '.join(forecast_list))}\n"
                f"📊 Previous: {escape_markdown_v2(' & '.join(previous_list))}\n"
                f"🎯 Actual: {escape_markdown_v2(' & '.join(actual_list))}\n"
                f"🔍 Combined ChatGPT Analysis: {escape_markdown_v2(combined_analysis)}\n"
                f"💥 Impact: {escape_markdown_v2(events[0]['impact'])}\n\n"
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
