import os
import logging
import time
from datetime import datetime
import sqlite3
import pytz
import random
from playwright.sync_api import sync_playwright, TimeoutError as PlaywrightTimeoutError
from bs4 import BeautifulSoup
import requests

# Logging setup with enhanced formatting
logging.basicConfig(
    level=logging.DEBUG,
    format="%(asctime)s [%(levelname)s] [%(funcName)s] %(message)s",
    handlers=[
        logging.FileHandler("scraper.log"),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# Timezone setup
prague_tz = pytz.timezone("Europe/Prague")

# List of User-Agents for rotation
USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/92.0.4515.159 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:89.0) Gecko/20100101 Firefox/89.0",
]

# Database connection manager
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
def analyze_event(currency, event, forecast, previous):
    analysis = "⚠️ ChatGPT analysis skipped"
    openai_api_key = os.getenv("OPENAI_API_KEY")
    if openai_api_key:
        try:
            prompt = f"Analyze the potential impact of the following Forex event on the {currency} currency market:\nEvent: {event}\nForecast: {forecast}\nPrevious: {previous}"
            headers = {
                "Authorization": f"Bearer {openai_api_key}",
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
        except Exception as e:
            logger.error(f"ChatGPT analysis failed: {e}")
    return analysis

def scrape_forex_news():
    logger.info("Starting scraping process...")
    db = Database()

    # Set the specific date to May 1, 2025
    target_date = datetime(2025, 5, 1, tzinfo=prague_tz)
    date_str = target_date.strftime("%Y-%m-%d")
    logger.info(f"Scraping data for date: {date_str}")

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

            # Use the daily calendar URL for May 1, 2025
            url = f"https://www.forexfactory.com/calendar?day=May1.2025"
            logger.debug(f"Navigating to URL: {url}")

            try:
                page.goto(url, timeout=60000)
                page.wait_for_load_state("networkidle", timeout=60000)
            except PlaywrightTimeoutError as e:
                logger.warning(f"Networkidle failed: {e}. Falling back to domcontentloaded.")
                try:
                    page.wait_for_load_state("domcontentloaded", timeout=60000)
                except PlaywrightTimeoutError as e:
                    logger.error(f"Domcontentloaded failed: {e}. Skipping date {date_str}.")
                    return

            time.sleep(random.uniform(3, 5))  # Random delay to avoid detection

            html = page.content()
            if "Just a moment..." in html:
                logger.error("Blocked by Cloudflare CAPTCHA. Rotating User-Agent and retrying.")
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
                try:
                    page.goto(url, timeout=60000)
                    page.wait_for_load_state("networkidle", timeout=60000)
                except PlaywrightTimeoutError:
                    logger.error("Still blocked by Cloudflare after retry. Skipping date.")
                    return

            soup = BeautifulSoup(html, "html.parser")
            table = soup.find("table", class_="calendar__table")
            if not table:
                tables = soup.find_all("table")
                for t in tables:
                    if "calendar" in str(t.get("class", [])) or "event" in str(t.get("class", [])):
                        table = t
                        break
                if not table:
                    logger.error(f"Could not find the calendar table for date {date_str}.")
                    return

            logger.info(f"Found table for date {date_str} with classes: {table.get('class', [])}")
            rows = table.find_all("tr", class_=lambda c: c and "calendar__row" in c)
            rows = [r for r in rows if r.get("data-event-id")]
            logger.info(f"Found {len(rows)} rows for date {date_str}")

            for idx, row in enumerate(rows):
                if idx == 0:
                    logger.debug(f"First row HTML: {row.prettify()[:500]}")

                logger.debug(f"Event row HTML: {row.prettify()[:1000]}")
                possible_time_classes = [
                    "calendar__cell calendar__time",
                    "calendar__cell--time",
                    "time",
                ]
                time_cell = None
                for time_class in possible_time_classes:
                    time_cell = row.find("td", class_=time_class)
                    if time_cell:
                        break

                raw_time = time_cell.text.strip() if time_cell and time_cell.text.strip() else None
                logger.debug(f"Raw time text: {raw_time}")
                if raw_time and raw_time.lower() == "all day":
                    logger.info(f"Skipping 'all day' event for date {date_str}")
                    continue

                event_time = None
                if raw_time:
                    try:
                        time_obj = datetime.strptime(raw_time, "%I:%M%p")
                        event_time = time_obj.strftime("%H:%M")
                        logger.debug(f"Parsed time: {event_time}")
                    except ValueError as e:
                        logger.warning(f"Could not parse time '{raw_time}': {e}")
                        continue
                else:
                    logger.warning(f"Skipping event: No time found for date {date_str}")
                    continue

                if not event_time:
                    continue

                currency_td = row.find("td", class_=lambda c: c and "calendar__currency" in c)
                currency = currency_td.text.strip() if currency_td else ""
                if not currency:
                    logger.warning(f"Skipping event: No currency found for date {date_str}, time {event_time}")
                    continue

                event_td = row.find("td", class_=lambda c: c and "calendar__event" in c)
                event = event_td.text.strip() if event_td else ""
                if not event:
                    logger.warning(f"Skipping event: No event name found for date {date_str}, time {event_time}, currency {currency}")
                    continue

                if db.check_duplicate_event(date_str, event_time, currency, event):
                    logger.info(f"Skipping duplicate event: {date_str}, {event_time}, {currency}, {event}")
                    continue

                impact = row.find("td", class_="calendar__cell--impact")
                impact = impact.find("span")["class"][-1].split("-")[-1] if impact and impact.find("span") else "N/A"
                forecast_td = row.find("td", class_=lambda c: c and "calendar__forecast" in c)
                forecast = forecast_td.text.strip() if forecast_td else "N/A"
                previous_td = row.find("td", class_=lambda c: c and "calendar__previous" in c)
                previous = previous_td.text.strip() if previous_td else "N/A"
                actual_td = row.find("td", class_=lambda c: c and "calendar__actual" in c)
                actual = actual_td.text.strip() if actual_td else "N/A"

                if not (date_str and event_time and currency and event):
                    logger.warning(f"Skipping incomplete event: {date_str}, {event_time}, {currency}, {event}")
                    continue

                analysis = analyze_event(currency, event, forecast, previous)
                event_data = (date_str, event_time, currency, event, forecast, previous, actual, impact, analysis)
                try:
                    db.insert_event(event_data)
                except Exception as e:
                    logger.error(f"Failed to insert event into DB: {e}")

        except Exception as e:
            logger.error(f"Scraping failed: {e}")
        finally:
            browser.close()
            logger.info("Browser closed.")

    logger.info("Scraping completed successfully")

if __name__ == "__main__":
    scrape_forex_news()
