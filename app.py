import os
import logging
import telebot
from flask import Flask, request, jsonify
from datetime import datetime, timedelta
from pytz import timezone
from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton, CallbackQuery
from bs4 import BeautifulSoup
from playwright.async_api import async_playwright
from contextlib import asynccontextmanager
import asyncio
import requests
from apscheduler.schedulers.background import BackgroundScheduler

# Logging setup
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[
        logging.FileHandler('scraper.log'),
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

# Check OPENAI_API_KEY
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
if not OPENAI_API_KEY:
    logging.warning("OPENAI_API_KEY is not set. News analysis with ChatGPT will be skipped.")
else:
    logging.info("OPENAI_API_KEY is set")

user_selected_date = {}
user_selected_impact = {}

# APScheduler setup for pinging
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

if os.getenv('RENDER_EXTERNAL_HOSTNAME'):
    scheduler.add_job(ping_self, 'interval', minutes=5)
    scheduler.start()
    logging.info("Started APScheduler for self-ping every 5 minutes")
else:
    logging.warning("RENDER_EXTERNAL_HOSTNAME not set, skipping self-ping")

# --- ChatGPT API Integration ---
def analyze_news_with_chatgpt(news_item):
    if not OPENAI_API_KEY:
        return "⚠️ ChatGPT analysis skipped: API key not configured."

    try:
        # Формируем запрос к OpenAI ChatGPT API
        url = "https://api.openai.com/v1/chat/completions"
        headers = {
            "Authorization": f"Bearer {OPENAI_API_KEY}",
            "Content-Type": "application/json"
        }
        prompt = (
            f"Analyze the following Forex news and predict its potential market impact:\n"
            f"Time: {news_item['time']}\n"
            f"Currency: {news_item['currency']}\n"
            f"Event: {news_item['event']}\n"
            f"Forecast: {news_item['forecast']}\n"
            f"Previous: {news_item['previous']}\n"
            "Provide a concise analysis (up to 100 words) of how this news might affect the market."
        )
        data = {
            "model": "gpt-4",
            "messages": [
                {"role": "system", "content": "You are a financial analyst specializing in Forex markets."},
                {"role": "user", "content": prompt}
            ],
            "max_tokens": 150,
            "temperature": 0.7
        }

        response = requests.post(url, headers=headers, json=data, timeout=10)
        response.raise_for_status()
        result = response.json()
        analysis = result["choices"][0]["message"]["content"].strip()
        return escape_markdown_v2(analysis)
    except Exception as e:
        logging.error(f"ChatGPT analysis failed: {e}")
        return "⚠️ Error in ChatGPT analysis."

# --- News parsing functions ---
def escape_markdown_v2(text: str) -> str:
    if not text:
        return "N/A"
    special = ['_', '*', '[', ']', '(', ')', '~', '`', '>', '#', '+', '-', '=', '|', '{', '}', '.', '!']
    for ch in special:
        text = text.replace(ch, f"\\{ch}")
    return text

@asynccontextmanager
async def get_page():
    async with async_playwright() as p:
        try:
            browser = await p.chromium.launch(headless=True)
            page = await browser.new_page()
            try:
                yield page
            finally:
                await browser.close()
        except Exception as e:
            logging.error(f"Failed to launch browser: {e}")
            raise

async def main(target_date=None, impact_level="high", debug=False):
    if not bot or not CHAT_ID:
        logging.error("Cannot send news: Bot or CHAT_ID not configured")
        return [] if debug else None

    try:
        if target_date is None:
            target_date = datetime.now(timezone("Europe/Prague"))
        scraped_display = target_date.strftime("%d.%m.%Y")
        scraped_display_esc = escape_markdown_v2(scraped_display)
        scraped_url = target_date.strftime("%b%d.%Y").lower()
        url = f"https://www.forexfactory.com/calendar?day={scraped_url}"

        logging.info(f"[DEBUG] Fetching URL: {url}")
        async with get_page() as page:
            await page.set_extra_http_headers({
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
                'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8'
            })
            for attempt in range(3):
                try:
                    await page.goto(url, timeout=120000)
                    await page.wait_for_selector('table.calendar__table', timeout=10000)
                    html = await page.content()
                    break
                except Exception as e:
                    if attempt == 2:
                        logging.error(f"Failed to load page {url} after 3 attempts: {e}")
                        return [] if debug else None
                    await asyncio.sleep(2)

        soup = BeautifulSoup(html, 'html.parser')
        rows = soup.select('table.calendar__table tr.calendar__row[data-event-id]') or soup.select('table.calendar tr.event')
        logging.info(f"[DEBUG] Total rows found: {len(rows)}")
        for i, row in enumerate(rows[:5]):
            logging.debug(f"[DEBUG] Row {i} snippet: {str(row)[:200]}")

        news = []
        last_time = "N/A"  # Храним последнее известное время
        for r in rows:
            imp = r.select_one('.calendar__impact span.icon') or r.select_one('.impact span.icon')
            if not imp:
                logging.debug(f"[DEBUG] No impact icon found in row: {str(r)[:200]}")
                continue
            classes = imp.get('class', [])
            is_high = 'icon--ff-impact-red' in classes
            is_medium = 'icon--ff-impact-orange' in classes

            if (impact_level == 'medium' and (is_high or is_medium)) or (impact_level == 'high' and is_high):
                time = r.select_one('.calendar__time').text.strip() if r.select_one('.calendar__time') else 'N/A'
                if time == "N/A":
                    time = last_time  # Используем время предыдущей новости
                else:
                    last_time = time  # Обновляем последнее известное время
                time = escape_markdown_v2(time)

                cur = escape_markdown_v2(r.select_one('.calendar__currency').text.strip() if r.select_one('.calendar__currency') else 'N/A')
                evt = escape_markdown_v2(r.select_one('.calendar__event-title').text.strip() if r.select_one('.calendar__event-title') else 'N/A')
                fct = escape_markdown_v2(r.select_one('.calendar__forecast').text.strip() if r.select_one('.calendar__forecast') else 'N/A')
                prv = escape_markdown_v2(r.select_one('.calendar__previous').text.strip() if r.select_one('.calendar__previous') else 'N/A')

                news_item = {
                    "time": time,
                    "currency": cur,
                    "event": evt,
                    "forecast": fct,
                    "previous": prv
                }
                # Анализируем новость через ChatGPT API
                analysis = analyze_news_with_chatgpt(news_item)
                news_item["analysis"] = analysis
                news.append(news_item)

        logging.info(f"[DEBUG] News items collected: {len(news)}")
        if debug:
            return news

        header = f"🗓️ Forex News for {scraped_display_esc} \\(CET\\):\n\n"
        if news:
            message_parts = [header]
            for item in news:
                part = (
                    f"⏰ Time: {item['time']}\n"
                    f"💰 Currency: {item['currency']}\n"
                    f"📰 Event: {item['event']}\n"
                    f"📈 Forecast: {item['forecast']}\n"
                    f"📊 Previous: {item['previous']}\n"
                    f"🔍 ChatGPT Analysis: {item['analysis']}\n\n"
                    f"{'-' * 40}\n\n"  # Добавляем разделитель между новостями
                )
                message_parts.append(part)
            message = "".join(message_parts)
        else:
            impact_esc = escape_markdown_v2(impact_level)
            message = header + f"✅ No news found for {scraped_display_esc} with impact: {impact_esc}\nPlease check the website for updates."

        logging.info(f"[DEBUG] Generated message: {message[:200]}... (total length: {len(message)})")
        if not message.strip():
            logging.error("Generated message is empty")
            return [] if debug else None

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
                    logging.info(f"[DEBUG] Sending message part (length: {len(part)}): {part[:50]}...")
                    bot.send_message(chat_id, part, parse_mode='MarkdownV2')
                except telebot.apihelper.ApiTelegramException as e:
                    logging.error(f"MarkdownV2 send failed: {e}. Falling back to plain.")
                    plain_part = part.replace('\\', '')
                    bot.send_message(chat_id, plain_part)
                logging.info(f"[DEBUG] Remaining message length: {len(message)}")

        send_long_message(CHAT_ID, message)

    except Exception as e:
        logging.exception(f"[DEBUG] Unexpected error: {e}")
        try:
            error_msg = escape_markdown_v2(f"⚠️ Error in Forex news scraping: {str(e)}")
            bot.send_message(CHAT_ID, error_msg, parse_mode='MarkdownV2')
        except Exception as te:
            logging.error(f"Failed to send error notification: {te}")
        return [] if debug else None

async def _fetch_html_and_rows(target_date=None):
    if target_date is None:
        target_date = datetime.now(timezone("Europe/Prague"))
    scraped_url = target_date.strftime("%b%d.%Y").lower()
    url = f"https://www.forexfactory.com/calendar?day={scraped_url}"
    async with get_page() as page:
        try:
            await page.set_extra_http_headers({
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
                'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8'
            })
            await page.goto(url, timeout=120000)
            await page.wait_for_selector('table.calendar__table', timeout=10000)
            html = await page.content()
        except Exception as e:
            logging.error(f"Failed to load page {url}: {e}")
            return "", []
    soup = BeautifulSoup(html, 'html.parser')
    rows = soup.select('table.calendar__table tr.calendar__row[data-event-id]') or soup.select('table.calendar tr.event')
    html_snippet = html[:2000]
    row_snippets = [str(r)[:200] for r in rows[:5]]
    return html_snippet, row_snippets

def fetch_debug_html():
    return asyncio.run(_fetch_html_and_rows())

def run_async():
    asyncio.run(main())

def run_async_for_date(date_str=None, impact_level="high", debug=False):
    try:
        target_date = datetime.strptime(date_str, "%Y-%m-%d") if date_str else None
        return asyncio.run(main(target_date, impact_level, debug))
    except Exception as e:
        logging.exception(f"[DEBUG] Error parsing date: {e}")
        return []

# --- Telegram bot with calendar ---
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
        bot.send_message(message.chat.id, "📬 Fetching today's Forex news...")
        run_async()
        bot.send_message(message.chat.id, "✅ News sent to the channel!")
    except Exception as e:
        logging.error(f"Error in /today: {e}")
        bot.send_message(message.chat.id, "⚠️ Error fetching news.")

@bot.message_handler(commands=["help", "start"])
def show_help(message):
    if not bot:
        logging.error("Bot not initialized due to missing TELEGRAM_BOT_TOKEN")
        return
    try:
        help_text = escape_markdown_v2("🤖 Forex News Bot Commands:\n\n/today — Get today's forex news\n/calendar — Choose a date to get past news\n/help — Show this message")
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
        run_async_for_date(date_str, impact)
        bot.send_message(chat_id, "✅ News sent to the channel!")
    except Exception as e:
        logging.error(f"Error in handle_impact_selection: {e}")
        bot.send_message(chat_id, "⚠️ Error fetching news.")

# --- Flask routes ---
@app.route("/", methods=["GET"])
def index():
    return "🤖 Forex bot is online!", 200

@app.route("/ping", methods=["GET"])
def ping():
    logging.info("Received ping request")
    return "OK", 200

@app.route("/run", methods=["GET"])
def run_today_forex():
    api_key = request.args.get("api_key")
    if api_key != os.getenv("API_KEY"):
        logging.warning("Unauthorized access attempt")
        return jsonify({"error": "Unauthorized"}), 401
    debug = request.args.get("debug") == "1"
    impact = request.args.get("impact", "high")
    date_str = request.args.get("date")
    try:
        if debug:
            logging.info("Running in debug mode")
            events = run_async_for_date(date_str=date_str, impact_level=impact, debug=True)
            html_snippet, row_snippets = fetch_debug_html()
            return jsonify({
                "date": (datetime.strptime(date_str, "%Y-%m-%d") if date_str else datetime.now(timezone("Europe/Prague"))).strftime("%Y-%m-%d"),
                "impact": impact,
                "count": len(events),
                "events": events,
                "html_snippet": html_snippet,
                "row_snippets": row_snippets
            }), 200
        else:
            logging.info("Triggering forex news")
            run_async_for_date(date_str=date_str, impact_level=impact)
            return f"✅ Forex news for {date_str or 'today'} triggered", 200
    except Exception as e:
        logging.error(f"Error in /run: {e}")
        return jsonify({"error": str(e)}), 500

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
        logging.info(f"Attempting to set webhook to {webhook_url}")
        bot.remove_webhook()
        logging.info("Removed existing webhook")
        bot.set_webhook(url=webhook_url)
        logging.info(f"Webhook successfully set to {webhook_url}")
    except Exception as e:
        logging.error(f"Failed to set webhook: {e}")
        # Try to check the current webhook status
        try:
            webhook_info = bot.get_webhook_info()
            logging.info(f"Current webhook info: {webhook_info}")
        except Exception as e2:
            logging.error(f"Failed to get webhook info: {e2}")

# Check required environment variables and setup webhook
logging.info("Checking required environment variables")
required_vars = ["TELEGRAM_BOT_TOKEN", "TELEGRAM_CHAT_ID", "API_KEY"]
missing_vars = [var for var in required_vars if not os.getenv(var)]
if missing_vars:
    logging.error(f"Missing required environment variables: {', '.join(missing_vars)}")
else:
    logging.info("All required environment variables are set")
    if bot:
        logging.info("Bot is initialized, setting up webhook")
        setup_webhook()
    else:
        logging.warning("Skipping bot setup due to missing TELEGRAM_BOT_TOKEN")

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
