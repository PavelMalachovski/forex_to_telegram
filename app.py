#!/usr/bin/env python3
"""
Forex News Telegram Bot

A Flask-based web application that scrapes forex news from ForexFactory
and sends them to a Telegram channel with ChatGPT analysis.

Optimized for deployment on Render.com with proper error handling,
logging, and environment variable management.
"""

import os
import logging
import asyncio
import time
from datetime import datetime, timedelta
from contextlib import asynccontextmanager
from typing import Optional, List, Dict, Any

import telebot
import requests
from flask import Flask, request, jsonify
from pytz import timezone
from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton, CallbackQuery
from bs4 import BeautifulSoup
from playwright.async_api import async_playwright
from apscheduler.schedulers.background import BackgroundScheduler


# =============================================================================
# CONFIGURATION AND SETUP
# =============================================================================

class Config:
    """Application configuration management."""
    
    def __init__(self):
        self.telegram_bot_token = os.getenv("TELEGRAM_BOT_TOKEN")
        self.telegram_chat_id = os.getenv("TELEGRAM_CHAT_ID")
        self.openai_api_key = os.getenv("OPENAI_API_KEY")
        self.api_key = os.getenv("API_KEY")
        self.render_hostname = os.getenv("RENDER_EXTERNAL_HOSTNAME")
        self.port = int(os.getenv("PORT", 5000))
        self.timezone = "Europe/Prague"
        
    def validate_required_vars(self) -> List[str]:
        """Validate required environment variables."""
        required_vars = {
            "TELEGRAM_BOT_TOKEN": self.telegram_bot_token,
            "TELEGRAM_CHAT_ID": self.telegram_chat_id,
            "API_KEY": self.api_key
        }
        return [var for var, value in required_vars.items() if not value]


def setup_logging():
    """Configure application logging."""
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        handlers=[
            logging.FileHandler('scraper.log'),
            logging.StreamHandler()
        ]
    )
    return logging.getLogger(__name__)


# Initialize configuration and logging
config = Config()
logger = setup_logging()

# Flask app initialization
app = Flask(__name__)

# Global state for user interactions
user_selected_date = {}
user_selected_impact = {}


# =============================================================================
# TELEGRAM BOT INITIALIZATION
# =============================================================================

class TelegramBotManager:
    """Manages Telegram bot initialization and webhook setup."""
    
    def __init__(self, config: Config):
        self.config = config
        self.bot = None
        self._initialize_bot()
    
    def _initialize_bot(self):
        """Initialize the Telegram bot if token is available."""
        if not self.config.telegram_bot_token:
            logger.error("TELEGRAM_BOT_TOKEN is not set. Bot functionality will be disabled.")
            return
        
        try:
            self.bot = telebot.TeleBot(self.config.telegram_bot_token)
            logger.info("Telegram bot initialized successfully")
        except Exception as e:
            logger.error(f"Failed to initialize Telegram bot: {e}")
    
    def setup_webhook(self, max_retries: int = 5, initial_delay: int = 10):
        """Set up webhook for Telegram bot with retry logic and exponential backoff."""
        if not self.bot:
            logger.warning("Cannot set webhook: Bot not initialized")
            return False
        
        if not self.config.render_hostname:
            logger.warning("Cannot set webhook: RENDER_EXTERNAL_HOSTNAME not set")
            return False
        
        webhook_url = f"https://{self.config.render_hostname}/webhook"
        
        for attempt in range(max_retries):
            try:
                logger.info(f"Setting webhook attempt {attempt + 1}/{max_retries} to {webhook_url}")
                
                # Remove existing webhook first
                self.bot.remove_webhook()
                time.sleep(2)  # Brief pause between remove and set
                
                # Set new webhook
                result = self.bot.set_webhook(url=webhook_url)
                
                if result:
                    logger.info("Webhook successfully configured")
                    return True
                else:
                    logger.warning(f"Webhook setup returned False on attempt {attempt + 1}")
                    
            except Exception as e:
                logger.error(f"Failed to set webhook on attempt {attempt + 1}: {e}")
                
                if attempt < max_retries - 1:
                    delay = initial_delay * (2 ** attempt)  # Exponential backoff
                    logger.info(f"Retrying webhook setup in {delay} seconds...")
                    time.sleep(delay)
                else:
                    logger.error("All webhook setup attempts failed")
        
        return False
    
    def setup_webhook_async(self):
        """Set up webhook asynchronously after a delay to allow service to fully start."""
        def delayed_webhook_setup():
            time.sleep(30)  # Wait 30 seconds for service to be fully ready
            self.setup_webhook()
        
        import threading
        webhook_thread = threading.Thread(target=delayed_webhook_setup, daemon=True)
        webhook_thread.start()
        logger.info("Webhook setup scheduled for 30 seconds after startup")


# Initialize bot manager
bot_manager = TelegramBotManager(config)
bot = bot_manager.bot


# =============================================================================
# RENDER.COM KEEP-ALIVE FUNCTIONALITY
# =============================================================================

class RenderKeepAlive:
    """Manages self-ping functionality to prevent Render.com app from sleeping."""
    
    def __init__(self, config: Config):
        self.config = config
        self.scheduler = BackgroundScheduler()
        self._setup_scheduler()
    
    def _setup_scheduler(self):
        """Set up the scheduler for self-ping if hostname is available."""
        if not self.config.render_hostname:
            logger.warning("RENDER_EXTERNAL_HOSTNAME not set, skipping self-ping")
            return
        
        self.scheduler.add_job(self._ping_self, 'interval', minutes=5)
        self.scheduler.start()
        logger.info("Started APScheduler for self-ping every 5 minutes")
    
    def _ping_self(self):
        """Send HTTP request to /ping to prevent app from sleeping."""
        try:
            ping_url = f"https://{self.config.render_hostname}/ping"
            response = requests.get(ping_url, timeout=10)
            
            if response.status_code == 200:
                logger.info(f"Ping successful: {ping_url}")
            else:
                logger.error(f"Ping failed: {ping_url}, status code: {response.status_code}")
        except Exception as e:
            logger.error(f"Ping error: {e}")


# Initialize keep-alive functionality
keep_alive = RenderKeepAlive(config)


# =============================================================================
# UTILITY FUNCTIONS
# =============================================================================

def escape_markdown_v2(text: str) -> str:
    """Escape special characters for Telegram MarkdownV2 format."""
    if not text:
        return "N/A"
    
    special_chars = ['_', '*', '[', ']', '(', ')', '~', '`', '>', '#', '+', '-', '=', '|', '{', '}', '.', '!']
    for char in special_chars:
        text = text.replace(char, f"\\{char}")
    return text


def send_long_message(chat_id: str, message: str):
    """Send long messages by splitting them into chunks."""
    if not bot or not message.strip():
        logger.error("Cannot send message: Bot not initialized or message is empty")
        return
    
    message = message.strip()
    while message:
        if len(message) <= 4096:
            part = message
            message = ""
        else:
            cut_pos = message[:4096].rfind('\n') if '\n' in message[:4096] else 4096
            part = message[:cut_pos].strip()
            message = message[cut_pos:].strip()
        
        if not part:
            logger.warning(f"Skipping empty message part")
            continue
        
        try:
            logger.info(f"Sending message part (length: {len(part)})")
            bot.send_message(chat_id, part, parse_mode='MarkdownV2')
        except telebot.apihelper.ApiTelegramException as e:
            logger.error(f"MarkdownV2 send failed: {e}. Falling back to plain text.")
            plain_part = part.replace('\\', '')
            bot.send_message(chat_id, plain_part)


# =============================================================================
# CHATGPT INTEGRATION
# =============================================================================

class ChatGPTAnalyzer:
    """Handles ChatGPT API integration for news analysis."""
    
    def __init__(self, api_key: Optional[str]):
        self.api_key = api_key
        self.api_url = "https://api.openai.com/v1/chat/completions"
    
    def analyze_news(self, news_item: Dict[str, str]) -> str:
        """Analyze forex news using ChatGPT API."""
        if not self.api_key:
            return "⚠️ ChatGPT analysis skipped: API key not configured."
        
        try:
            headers = {
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json"
            }
            
            prompt = self._create_analysis_prompt(news_item)
            data = {
                "model": "gpt-4",
                "messages": [
                    {"role": "system", "content": "You are a financial analyst specializing in Forex markets."},
                    {"role": "user", "content": prompt}
                ],
                "max_tokens": 150,
                "temperature": 0.7
            }
            
            response = requests.post(self.api_url, headers=headers, json=data, timeout=10)
            response.raise_for_status()
            
            result = response.json()
            analysis = result["choices"][0]["message"]["content"].strip()
            return escape_markdown_v2(analysis)
            
        except Exception as e:
            logger.error(f"ChatGPT analysis failed: {e}")
            return "⚠️ Error in ChatGPT analysis."
    
    def _create_analysis_prompt(self, news_item: Dict[str, str]) -> str:
        """Create analysis prompt for ChatGPT."""
        return (
            f"Analyze the following Forex news and predict its potential market impact:\n"
            f"Time: {news_item['time']}\n"
            f"Currency: {news_item['currency']}\n"
            f"Event: {news_item['event']}\n"
            f"Forecast: {news_item['forecast']}\n"
            f"Previous: {news_item['previous']}\n"
            "Provide a concise analysis (up to 100 words) of how this news might affect the market."
        )


# Initialize ChatGPT analyzer
chatgpt_analyzer = ChatGPTAnalyzer(config.openai_api_key)


# =============================================================================
# WEB SCRAPING FUNCTIONALITY
# =============================================================================

@asynccontextmanager
async def get_browser_page():
    """Context manager for browser page with proper cleanup."""
    async with async_playwright() as playwright:
        try:
            browser = await playwright.chromium.launch(headless=True)
            page = await browser.new_page()
            
            # Set headers to mimic real browser
            await page.set_extra_http_headers({
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
                'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8'
            })
            
            try:
                yield page
            finally:
                await browser.close()
        except Exception as e:
            logger.error(f"Failed to launch browser: {e}")
            raise


class ForexNewsScraper:
    """Handles scraping of forex news from ForexFactory."""
    
    def __init__(self, config: Config):
        self.config = config
        self.base_url = "https://www.forexfactory.com/calendar"
    
    async def scrape_news(self, target_date: Optional[datetime] = None, 
                         impact_level: str = "high", debug: bool = False) -> List[Dict[str, Any]]:
        """Scrape forex news for the specified date and impact level."""
        if target_date is None:
            target_date = datetime.now(timezone(self.config.timezone))
        
        url = self._build_url(target_date)
        logger.info(f"Fetching URL: {url}")
        
        try:
            async with get_browser_page() as page:
                html = await self._fetch_page_content(page, url)
                news_items = self._parse_news_from_html(html, impact_level)
                
                # Add ChatGPT analysis to each news item
                for item in news_items:
                    item["analysis"] = chatgpt_analyzer.analyze_news(item)
                
                logger.info(f"Collected {len(news_items)} news items")
                return news_items
                
        except Exception as e:
            logger.error(f"Error scraping news: {e}")
            return []
    
    def _build_url(self, target_date: datetime) -> str:
        """Build ForexFactory URL for the target date."""
        date_str = target_date.strftime("%b%d.%Y").lower()
        return f"{self.base_url}?day={date_str}"
    
    async def _fetch_page_content(self, page, url: str) -> str:
        """Fetch page content with retry logic."""
        for attempt in range(3):
            try:
                await page.goto(url, timeout=120000)
                await page.wait_for_selector('table.calendar__table', timeout=10000)
                return await page.content()
            except Exception as e:
                if attempt == 2:
                    logger.error(f"Failed to load page {url} after 3 attempts: {e}")
                    raise
                await asyncio.sleep(2)
    
    def _parse_news_from_html(self, html: str, impact_level: str) -> List[Dict[str, str]]:
        """Parse news items from HTML content."""
        soup = BeautifulSoup(html, 'html.parser')
        rows = (soup.select('table.calendar__table tr.calendar__row[data-event-id]') or 
                soup.select('table.calendar tr.event'))
        
        logger.info(f"Found {len(rows)} total rows")
        
        news_items = []
        last_time = "N/A"
        
        for row in rows:
            if self._should_include_news(row, impact_level):
                news_item = self._extract_news_data(row, last_time)
                if news_item["time"] != "N/A":
                    last_time = news_item["time"]
                news_items.append(news_item)
        
        return news_items
    
    def _should_include_news(self, row, impact_level: str) -> bool:
        """Check if news item should be included based on impact level."""
        impact_element = (row.select_one('.calendar__impact span.icon') or 
                         row.select_one('.impact span.icon'))
        
        if not impact_element:
            return False
        
        classes = impact_element.get('class', [])
        is_high = 'icon--ff-impact-red' in classes
        is_medium = 'icon--ff-impact-orange' in classes
        
        return ((impact_level == 'medium' and (is_high or is_medium)) or 
                (impact_level == 'high' and is_high))
    
    def _extract_news_data(self, row, last_time: str) -> Dict[str, str]:
        """Extract news data from a table row."""
        time_elem = row.select_one('.calendar__time')
        time = time_elem.text.strip() if time_elem else last_time
        
        return {
            "time": escape_markdown_v2(time),
            "currency": escape_markdown_v2(self._get_text_or_na(row, '.calendar__currency')),
            "event": escape_markdown_v2(self._get_text_or_na(row, '.calendar__event-title')),
            "forecast": escape_markdown_v2(self._get_text_or_na(row, '.calendar__forecast')),
            "previous": escape_markdown_v2(self._get_text_or_na(row, '.calendar__previous'))
        }
    
    def _get_text_or_na(self, row, selector: str) -> str:
        """Get text from element or return 'N/A' if not found."""
        element = row.select_one(selector)
        return element.text.strip() if element else 'N/A'


# Initialize scraper
scraper = ForexNewsScraper(config)


# =============================================================================
# MESSAGE FORMATTING
# =============================================================================

class MessageFormatter:
    """Handles formatting of news messages for Telegram."""
    
    @staticmethod
    def format_news_message(news_items: List[Dict[str, Any]], 
                           target_date: datetime, impact_level: str) -> str:
        """Format news items into a Telegram message."""
        date_str = target_date.strftime("%d.%m.%Y")
        date_escaped = escape_markdown_v2(date_str)
        header = f"🗓️ Forex News for {date_escaped} \\(CET\\):\n\n"
        
        if not news_items:
            impact_escaped = escape_markdown_v2(impact_level)
            return (header + 
                   f"✅ No news found for {date_escaped} with impact: {impact_escaped}\n"
                   "Please check the website for updates.")
        
        message_parts = [header]
        for item in news_items:
            part = (
                f"⏰ Time: {item['time']}\n"
                f"💰 Currency: {item['currency']}\n"
                f"📰 Event: {item['event']}\n"
                f"📈 Forecast: {item['forecast']}\n"
                f"📊 Previous: {item['previous']}\n"
                f"🔍 ChatGPT Analysis: {item['analysis']}\n\n"
                f"{'-' * 40}\n\n"
            )
            message_parts.append(part)
        
        return "".join(message_parts)


# =============================================================================
# MAIN NEWS PROCESSING
# =============================================================================

async def process_forex_news(target_date: Optional[datetime] = None, 
                           impact_level: str = "high", debug: bool = False) -> Optional[List[Dict[str, Any]]]:
    """Main function to process and send forex news."""
    if not bot or not config.telegram_chat_id:
        logger.error("Cannot process news: Bot or CHAT_ID not configured")
        return [] if debug else None
    
    try:
        if target_date is None:
            target_date = datetime.now(timezone(config.timezone))
        
        # Scrape news
        news_items = await scraper.scrape_news(target_date, impact_level, debug)
        
        if debug:
            return news_items
        
        # Format and send message
        message = MessageFormatter.format_news_message(news_items, target_date, impact_level)
        
        if message.strip():
            send_long_message(config.telegram_chat_id, message)
        else:
            logger.error("Generated message is empty")
        
        return news_items
        
    except Exception as e:
        logger.exception(f"Unexpected error in process_forex_news: {e}")
        
        # Send error notification
        try:
            error_msg = escape_markdown_v2(f"⚠️ Error in Forex news scraping: {str(e)}")
            bot.send_message(config.telegram_chat_id, error_msg, parse_mode='MarkdownV2')
        except Exception as te:
            logger.error(f"Failed to send error notification: {te}")
        
        return [] if debug else None


# =============================================================================
# ASYNC WRAPPER FUNCTIONS
# =============================================================================

def run_forex_news_sync():
    """Synchronous wrapper for running forex news processing."""
    return asyncio.run(process_forex_news())


def run_forex_news_for_date(date_str: Optional[str] = None, 
                           impact_level: str = "high", debug: bool = False):
    """Run forex news processing for a specific date."""
    try:
        target_date = datetime.strptime(date_str, "%Y-%m-%d") if date_str else None
        return asyncio.run(process_forex_news(target_date, impact_level, debug))
    except Exception as e:
        logger.exception(f"Error parsing date: {e}")
        return []


# =============================================================================
# TELEGRAM BOT HANDLERS
# =============================================================================

class TelegramHandlers:
    """Telegram bot command and callback handlers."""
    
    @staticmethod
    def generate_calendar(year: int, month: int) -> InlineKeyboardMarkup:
        """Generate calendar markup for date selection."""
        markup = InlineKeyboardMarkup(row_width=7)
        
        # Add weekday headers
        weekdays = ["Mo", "Tu", "We", "Th", "Fr", "Sa", "Su"]
        markup.add(*[InlineKeyboardButton(d, callback_data="IGNORE") for d in weekdays])
        
        # Calculate calendar layout
        first_day = datetime(year, month, 1)
        start_day = first_day.weekday()
        
        # Add empty cells for days before month start
        days = []
        for _ in range(start_day):
            days.append(InlineKeyboardButton(" ", callback_data="IGNORE"))
        
        # Add days of the month
        next_month = first_day.replace(day=28) + timedelta(days=4)
        days_in_month = (next_month - timedelta(days=next_month.day)).day
        
        for day in range(1, days_in_month + 1):
            date_str = f"{year}-{month:02d}-{day:02d}"
            days.append(InlineKeyboardButton(str(day), callback_data=f"DAY_{date_str}"))
        
        # Fill remaining cells
        while len(days) % 7 != 0:
            days.append(InlineKeyboardButton(" ", callback_data="IGNORE"))
        
        # Add days to markup in rows of 7
        for i in range(0, len(days), 7):
            markup.row(*days[i:i+7])
        
        # Add navigation buttons
        nav_buttons = [
            InlineKeyboardButton("<", callback_data=f"PREV_{year}-{month}"),
            InlineKeyboardButton(f"{first_day.strftime('%B')} {year}", callback_data="IGNORE"),
            InlineKeyboardButton(">", callback_data=f"NEXT_{year}-{month}")
        ]
        markup.row(*nav_buttons)
        
        # Add today button
        today_str = datetime.today().strftime('%Y-%m-%d')
        markup.add(InlineKeyboardButton("📍 Today", callback_data=f"DAY_{today_str}"))
        
        return markup


# Register bot handlers if bot is available
if bot:
    @bot.message_handler(commands=["calendar"])
    def show_calendar(message):
        """Show calendar for date selection."""
        try:
            today = datetime.today()
            bot.send_message(
                message.chat.id,
                "📅 Select a date:",
                reply_markup=TelegramHandlers.generate_calendar(today.year, today.month)
            )
        except Exception as e:
            logger.error(f"Error in /calendar: {e}")
            bot.send_message(message.chat.id, "⚠️ Error showing calendar.")

    @bot.message_handler(commands=["today"])
    def send_today_news(message):
        """Send today's forex news."""
        try:
            bot.send_message(message.chat.id, "📬 Fetching today's Forex news...")
            run_forex_news_sync()
            bot.send_message(message.chat.id, "✅ News sent to the channel!")
        except Exception as e:
            logger.error(f"Error in /today: {e}")
            bot.send_message(message.chat.id, "⚠️ Error fetching news.")

    @bot.message_handler(commands=["help", "start"])
    def show_help(message):
        """Show help message."""
        try:
            help_text = escape_markdown_v2(
                "🤖 Forex News Bot Commands:\n\n"
                "/today — Get today's forex news\n"
                "/calendar — Choose a date to get past news\n"
                "/help — Show this help message\n\n"
                "The bot scrapes high-impact forex news from ForexFactory "
                "and provides ChatGPT analysis for each event."
            )
            bot.send_message(message.chat.id, help_text, parse_mode='MarkdownV2')
        except Exception as e:
            logger.error(f"Error in /help: {e}")
            plain_help = (
                "🤖 Forex News Bot Commands:\n\n"
                "/today — Get today's forex news\n"
                "/calendar — Choose a date to get past news\n"
                "/help — Show this help message\n\n"
                "The bot scrapes high-impact forex news from ForexFactory "
                "and provides ChatGPT analysis for each event."
            )
            bot.send_message(message.chat.id, plain_help)

    @bot.callback_query_handler(func=lambda call: True)
    def handle_callback(call: CallbackQuery):
        """Handle inline keyboard callbacks."""
        try:
            data = call.data
            user_id = call.from_user.id
            
            if data == "IGNORE":
                bot.answer_callback_query(call.id)
                return
            
            if data.startswith("DAY_"):
                date_str = data[4:]
                user_selected_date[user_id] = date_str
                
                # Show impact level selection
                markup = InlineKeyboardMarkup()
                markup.add(
                    InlineKeyboardButton("🔴 High Impact", callback_data="IMPACT_high"),
                    InlineKeyboardButton("🟠 Medium+ Impact", callback_data="IMPACT_medium")
                )
                
                bot.edit_message_text(
                    f"📅 Selected date: {date_str}\n\nChoose impact level:",
                    call.message.chat.id,
                    call.message.message_id,
                    reply_markup=markup
                )
            
            elif data.startswith("IMPACT_"):
                impact = data[7:]
                selected_date = user_selected_date.get(user_id)
                
                if not selected_date:
                    bot.answer_callback_query(call.id, "❌ Date not selected")
                    return
                
                user_selected_impact[user_id] = impact
                
                bot.edit_message_text(
                    f"📅 Date: {selected_date}\n📊 Impact: {impact}\n\n⏳ Fetching news...",
                    call.message.chat.id,
                    call.message.message_id
                )
                
                # Process news for selected date and impact
                try:
                    run_forex_news_for_date(selected_date, impact)
                    bot.send_message(call.message.chat.id, "✅ News sent to the channel!")
                except Exception as e:
                    logger.error(f"Error processing news for {selected_date}: {e}")
                    bot.send_message(call.message.chat.id, "⚠️ Error fetching news.")
                
                # Clean up user data
                user_selected_date.pop(user_id, None)
                user_selected_impact.pop(user_id, None)
            
            elif data.startswith("PREV_") or data.startswith("NEXT_"):
                # Handle calendar navigation
                direction, date_part = data.split("_", 1)
                year, month = map(int, date_part.split("-"))
                
                if direction == "PREV":
                    if month == 1:
                        year -= 1
                        month = 12
                    else:
                        month -= 1
                else:  # NEXT
                    if month == 12:
                        year += 1
                        month = 1
                    else:
                        month += 1
                
                new_markup = TelegramHandlers.generate_calendar(year, month)
                bot.edit_message_reply_markup(
                    call.message.chat.id,
                    call.message.message_id,
                    reply_markup=new_markup
                )
            
            bot.answer_callback_query(call.id)
            
        except Exception as e:
            logger.error(f"Error in callback handler: {e}")
            bot.answer_callback_query(call.id, "❌ Error processing request")


# =============================================================================
# FLASK ROUTES
# =============================================================================

@app.route("/", methods=["GET"])
def index():
    """Health check endpoint."""
    return "🤖 Forex bot is online!", 200


@app.route("/ping", methods=["GET"])
def ping():
    """Ping endpoint for keep-alive functionality."""
    logger.info("Received ping request")
    return "OK", 200


@app.route("/run", methods=["GET"])
def run_forex_endpoint():
    """API endpoint to trigger forex news processing."""
    api_key = request.args.get("api_key")
    if api_key != config.api_key:
        logger.warning("Unauthorized access attempt")
        return jsonify({"error": "Unauthorized"}), 401
    
    debug = request.args.get("debug") == "1"
    impact = request.args.get("impact", "high")
    date_str = request.args.get("date")
    
    try:
        if debug:
            logger.info("Running in debug mode")
            events = run_forex_news_for_date(date_str, impact, debug=True)
            
            return jsonify({
                "date": date_str or datetime.now(timezone(config.timezone)).strftime("%Y-%m-%d"),
                "impact": impact,
                "count": len(events),
                "events": events
            }), 200
        else:
            logger.info("Triggering forex news processing")
            run_forex_news_for_date(date_str, impact)
            return f"✅ Forex news for {date_str or 'today'} triggered", 200
            
    except Exception as e:
        logger.error(f"Error in /run endpoint: {e}")
        return jsonify({"error": str(e)}), 500


@app.route("/webhook", methods=["POST"])
def webhook():
    """Webhook endpoint for Telegram bot updates."""
    if not bot:
        logger.error("Webhook not available: Bot not initialized")
        return "Bot not initialized", 503
    
    try:
        update = telebot.types.Update.de_json(request.get_json())
        bot.process_new_updates([update])
        return "OK", 200
    except Exception as e:
        logger.error(f"Webhook error: {e}")
        return "Error", 500


@app.route("/health", methods=["GET"])
def health_check():
    """Comprehensive health check endpoint for deployment monitoring."""
    try:
        health_status = {
            "status": "healthy",
            "timestamp": datetime.now().isoformat(),
            "port": config.port,
            "bot_initialized": bot is not None,
            "webhook_configured": config.render_hostname is not None,
            "required_env_vars": {
                "TELEGRAM_BOT_TOKEN": bool(config.telegram_bot_token),
                "TELEGRAM_CHAT_ID": bool(config.telegram_chat_id),
                "API_KEY": bool(config.api_key),
                "RENDER_EXTERNAL_HOSTNAME": bool(config.render_hostname)
            }
        }
        
        # Check if any critical components are missing
        missing_vars = config.validate_required_vars()
        if missing_vars:
            health_status["status"] = "degraded"
            health_status["missing_vars"] = missing_vars
        
        status_code = 200 if health_status["status"] == "healthy" else 503
        return jsonify(health_status), status_code
        
    except Exception as e:
        logger.error(f"Health check error: {e}")
        return jsonify({
            "status": "unhealthy",
            "error": str(e),
            "timestamp": datetime.now().isoformat()
        }), 500


# =============================================================================
# APPLICATION STARTUP
# =============================================================================

def initialize_application():
    """Initialize the application with proper error handling."""
    logger.info("Initializing Forex News Bot application")
    logger.info(f"Application will run on host 0.0.0.0 port {config.port}")
    
    # Validate environment variables
    missing_vars = config.validate_required_vars()
    if missing_vars:
        logger.error(f"Missing required environment variables: {', '.join(missing_vars)}")
        return False
    
    logger.info("All required environment variables are set")
    
    # Set up webhook if bot is available
    if bot:
        logger.info("Bot initialized, scheduling webhook setup")
        # Use async webhook setup to avoid blocking startup
        bot_manager.setup_webhook_async()
    else:
        logger.warning("Skipping webhook setup: Bot not initialized")
    
    return True


# =============================================================================
# MAIN ENTRY POINT
# =============================================================================

if __name__ == "__main__":
    if initialize_application():
        logger.info(f"Starting Flask application on host 0.0.0.0 port {config.port}")
        app.run(host="0.0.0.0", port=config.port, debug=False)
    else:
        logger.error("Application initialization failed")
        exit(1)
