import os
import logging
import time
from datetime import datetime, timedelta
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
                    UNIQUE(date, currency, event)
                )
            ''')
            conn.commit()
        logger.info("Database initialized successfully.")

    def log_existing_events(self):
        """Log all existing events in the database for debugging."""
        with sqlite3.connect(self.db_name) as conn:
            c = conn.cursor()
            c.execute("SELECT date, time, currency, event FROM news")
            existing_events = c.fetchall()
            for event in existing_events:
                logger.debug(f"Existing event in DB: {event}")

    def check_duplicate_event(self, date, time, currency, event):
        """Check if an event already exists in the database."""
        with sqlite3.connect(self.db_name) as conn:
            c = conn.cursor()
            c.execute('''
                SELECT COUNT(*) FROM news
                WHERE date = ? AND currency = ? AND event = ?
            ''', (date, currency, event))
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

    def clear_db(self):
        """Clear all events from the database for a fresh scrape."""
        with sqlite3.connect(self.db_name) as conn:
            c = conn.cursor()
            c.execute("DELETE FROM news")
            conn.commit()
        logger.info("Database cleared for fresh scrape.")

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

# Impact mapping: CSS suffix to human-readable category
IMPACT_MAP = {
    "gra": "Non-Economic",
    "yel": "Low",
    "ora": "Medium",
    "red": "High",
}

def scrape_forex_news():
    # Calculate date range: today + 7 days
    start_date = datetime.now(prague_tz).date()
    end_date = start_date + timedelta(days=7)
    logger.info(f"Starting scraping from {start_date} to {end_date}...")
    db = Database()

    # Log existing events for debugging
    db.log_existing_events()

    # Optional: Clear database for fresh scrape (uncomment to enable)
    # db.clear_db()

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
            current = start_date
            while current <= end_date:
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

                # Format day as MonthDay.Year (e.g., May5.2025)
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

                last_time = None  # Track the last seen time for events with missing times

                for row in rows:
                    # Time
                    time_cell = row.find("td", class_=lambda c: c and ("calendar__time" in c or "--time" in c))
                    raw_time = time_cell.text.strip() if time_cell else ""

                    # Handle invalid time (e.g., "All Day")
                    if raw_time.lower() in ["all day", "tentative"]:
                        logger.debug(f"Skipping event due to invalid time: {raw_time}")
                        continue

                    # Parse time or use last_time if missing
                    if raw_time:
                        try:
                            event_time = datetime.strptime(raw_time, "%I:%M%p").strftime("%H:%M")
                            last_time = event_time  # Update last seen time
                            logger.debug(f"Parsed time: {event_time}")
                        except ValueError:
                            logger.debug(f"Failed to parse time {raw_time}, skipping event")
                            continue
                    else:
                        # If time is missing, use the last seen time
                        if last_time:
                            event_time = last_time
                            logger.debug(f"Using last seen time {event_time} for event with missing time")
                        else:
                            logger.debug("No previous time available, skipping event with missing time")
                            continue

                    # Currency
                    currency_td = row.find("td", class_=lambda c: c and "calendar__currency" in c)
                    currency = currency_td.text.strip() if currency_td else ""
                    if not currency:
                        logger.debug("Skipping event due to missing currency")
                        continue

                    # Event name
                    event_td = row.find("td", class_=lambda c: c and "calendar__event" in c)
                    event = event_td.text.strip() if event_td else ""
                    if not event:
                        logger.debug("Skipping event due to missing event name")
                        continue

                    # Duplicate
                    if db.check_duplicate_event(date_str, event_time, currency, event):
                        logger.debug(f"Skipping duplicate event: {date_str}, {event_time}, {currency}, {event}")
                        continue

                    # Forecast, Previous, Actual
                    forecast = row.find("td", class_=lambda c: c and "calendar__forecast" in c)
                    forecast = forecast.text.strip() if forecast else "N/A"
                    previous = row.find("td", class_=lambda c: c and "calendar__previous" in c)
                    previous = previous.text.strip() if previous else "N/A"
                    actual = row.find("td", class_=lambda c: c and "calendar__actual" in c)
                    actual = actual.text.strip() if actual else "N/A"

                    # Impact
                    impact = "N/A"
                    impact_td = row.find("td", class_=lambda c: c and "calendar__impact" in c)
                    if impact_td:
                        span = impact_td.find("span", class_=lambda cl: cl and cl.startswith("icon--ff-impact-"))
                        if span:
                            cls = next((cl for cl in span["class"] if cl.startswith("icon--ff-impact-")), "")
                            code = cls.rsplit("-", 1)[-1]
                            impact = IMPACT_MAP.get(code, "N/A")

                    # Analysis
                    analysis = analyze_event(currency, event, forecast, previous)
                    event_data = (date_str, event_time, currency, event, forecast, previous, actual, impact, analysis)

                    # Insert
                    logger.debug(f"Inserting: {event_data}")
                    try:
                        db.insert_event(event_data)
                    except Exception as e:
                        logger.error(f"Insert failed for {date_str} {event}: {e}")

                page.close()
                current += timedelta(days=1)

        except Exception as e:
            logger.error(f"Scraping failed overall: {e}")
        finally:
            browser.close()
            logger.info("Browser closed.")

    logger.info("Scraping completed successfully")

if __name__ == "__main__":
    scrape_forex_news()
