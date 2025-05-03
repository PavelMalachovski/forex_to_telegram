import os
import logging
import time
from datetime import datetime, timedelta
import sqlite3
import pytz
from playwright.sync_api import sync_playwright
from bs4 import BeautifulSoup
import requests
from apscheduler.schedulers.background import BackgroundScheduler

# Logging setup
logging.basicConfig(
    level=logging.DEBUG,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[
        logging.FileHandler("scraper.log"),
        logging.StreamHandler()
    ]
)

# Timezone setup
prague_tz = pytz.timezone("Europe/Prague")

# Database setup
def init_db():
    conn = sqlite3.connect('news.db')
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
    conn.close()

# Function to check if an event already exists in the database
def check_duplicate_event(date, time, currency, event):
    conn = sqlite3.connect('news.db')
    c = conn.cursor()
    c.execute('''
        SELECT COUNT(*) FROM news
        WHERE date = ? AND time = ? AND currency = ? AND event = ?
    ''', (date, time, currency, event))
    count = c.fetchone()[0]
    conn.close()
    return count > 0

# Function to generate date periods for scraping
def generate_date_periods(start_date, end_date):
    periods = []
    current = start_date
    while current <= end_date:
        periods.append(current.strftime("%Y-%m-%d"))
        current += timedelta(days=1)
    return periods

# Function to scrape Forex Factory news for a given date
def scrape_forex_news():
    logging.info("Starting scraping process...")
    init_db()

    # Задаем диапазон дат (для теста ограничим первыми 5 днями апреля)
    start_date = datetime(2025, 4, 1, tzinfo=prague_tz)
    end_date = datetime(2025, 4, 5, tzinfo=prague_tz)  # Ограничим для теста
    logging.info(f"Scraping range: {start_date} to {end_date}")

    # Генерируем периоды для парсинга (по дням)
    dates = generate_date_periods(start_date, end_date)
    logging.info(f"Scraping data for dates: {dates} (total {len(dates)} days)")

    try:
        with sync_playwright() as p:
            browser = p.chromium.launch(
                headless=True,
                args=["--disable-blink-features=AutomationControlled"]
            )
            # Устанавливаем User-Agent для избежания блокировок
            page = browser.new_page(user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36")
            conn = sqlite3.connect('news.db')
            c = conn.cursor()

            for date in dates:
                logging.info(f"Scraping data for date: {date}")
                url = f"https://www.forexfactory.com/calendar?day={date}"
                try:
                    page.goto(url, timeout=60000)
                    page.wait_for_load_state("networkidle", timeout=60000)
                except Exception as e:
                    logging.warning(f"Networkidle failed: {e}. Falling back to domcontentloaded.")
                    page.wait_for_load_state("domcontentloaded", timeout=60000)
                time.sleep(2)  # Дополнительная задержка

                html = page.content()
                soup = BeautifulSoup(html, "html.parser")

                # Пробуем найти таблицу
                table = soup.find("table", class_="calendar__table")
                if not table:
                    tables = soup.find_all("table")
                    table = None
                    for t in tables:
                        if "calendar" in str(t.get("class", [])) or "event" in str(t.get("class", [])):
                            table = t
                            break
                    if not table:
                        logging.error(f"Could not find the calendar table for date {date}.")
                        logging.info(f"HTML structure: {soup.prettify()[:1000]}")
                        continue

                logging.info(f"Found table for date {date} with classes: {table.get('class', [])}")

                # Получаем все строки
                rows = table.find_all("tr", class_=lambda x: x and "calendar__row" in x)
                logging.info(f"Found {len(rows)} rows for date {date}")
                last_date = None

                for idx, row in enumerate(rows):
                    # Логируем HTML первой строки для отладки
                    if idx == 0:
                        logging.debug(f"First row HTML: {row.prettify()[:500]}")

                    # Проверяем, является ли строка новой датой
                    date_cell = row.find("td", class_="calendar__cell")
                    if date_cell and "calendar__row--day-breaker" in row.get("class", []):
                        date_text = date_cell.text.strip()
                        logging.debug(f"Raw date text: {date_text}")
                        if date_text:
                            try:
                                # Пробуем извлечь дату из текста (например, "Sun Apr 27")
                                # Учитываем, что год нужно взять из запрошенной даты
                                date_obj = datetime.strptime(date_text, "%a %b %d")
                                year = datetime.strptime(date, "%Y-%m-%d").year
                                date_obj = date_obj.replace(year=year)
                                date = date_obj.strftime("%Y-%m-%d")
                                last_date = date
                                logging.debug(f"Parsed date: {date}")
                            except ValueError as e:
                                logging.warning(f"Could not parse date '{date_text}': {e}")
                                continue
                    else:
                        date = last_date

                    if not last_date:
                        logging.warning("Skipping row: No date found and no previous date available")
                        continue

                    # Пропускаем события до 1 апреля 2025
                    event_date = datetime.strptime(last_date, "%Y-%m-%d").replace(tzinfo=prague_tz)
                    if event_date < start_date:
                        logging.info(f"Skipping event before start date: {last_date}")
                        continue

                    # Пропускаем события после текущей даты
                    if event_date > end_date:
                        logging.info(f"Skipping event after end date: {last_date}")
                        continue

                    # Извлекаем время
                    time_cell = row.find("td", class_="calendar__cell--time")
                    raw_time = time_cell.text.strip() if time_cell and time_cell.text.strip() else None
                    logging.debug(f"Raw time text: {raw_time}")

                    # Проверяем, является ли событие "all day"
                    if raw_time and raw_time.lower() == "all day":
                        logging.info(f"Skipping 'all day' event for date {last_date}")
                        continue

                    # Пробуем извлечь и парсить время
                    event_time = None
                    if raw_time:
                        try:
                            time_obj = datetime.strptime(raw_time, "%I:%M%p")
                            event_time = time_obj.strftime("%H:%M")
                            logging.debug(f"Parsed time: {event_time}")
                        except ValueError as e:
                            logging.warning(f"Could not parse time '{raw_time}': {e}")
                            continue
                    else:
                        logging.warning(f"Skipping event: No time found for date {last_date}")
                        continue

                    if not event_time:
                        logging.warning(f"Skipping event: No valid time parsed for date {last_date}")
                        continue

                    # Извлекаем остальные данные
                    currency = row.find("td", class_="calendar__cell--currency")
                    currency = currency.text.strip() if currency else ""
                    if not currency:
                        logging.warning(f"Skipping event: No currency found for date {last_date}, time {event_time}")
                        continue

                    event = row.find("td", class_="calendar__cell--event")
                    event = event.text.strip() if event else ""
                    if not event:
                        logging.warning(f"Skipping event: No event name found for date {last_date}, time {event_time}, currency {currency}")
                        continue

                    # Проверяем, есть ли такое событие в базе
                    if check_duplicate_event(date, event_time, currency, event):
                        logging.info(f"Skipping duplicate event: {date}, {event_time}, {currency}, {event}")
                        continue

                    impact = row.find("td", class_="calendar__cell--impact")
                    impact = impact.find("span")["class"][-1].split("-")[-1] if impact and impact.find("span") else "N/A"

                    forecast = row.find("td", class_="calendar__cell--forecast")
                    forecast = forecast.text.strip() if forecast else "N/A"

                    previous = row.find("td", class_="calendar__cell--previous")
                    previous = previous.text.strip() if previous else "N/A"

                    actual = row.find("td", class_="calendar__cell--actual")
                    actual = actual.text.strip() if actual else "N/A"

                    # Проверяем, что все обязательные поля заполнены
                    if not (date and event_time and currency and event):
                        logging.warning(f"Skipping incomplete event: {date}, {event_time}, {currency}, {event}")
                        continue

                    # Анализ события через ChatGPT (если есть API ключ)
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
                            logging.error(f"ChatGPT analysis failed: {e}")

                    # Логируем данные перед вставкой
                    logging.debug(f"Inserting event: date={date}, time={event_time}, currency={currency}, event={event}, forecast={forecast}, previous={previous}, actual={actual}, impact={impact}, analysis={analysis}")

                    # Вставляем или обновляем запись в базе
                    try:
                        c.execute('''
                            INSERT OR REPLACE INTO news (date, time, currency, event, forecast, previous, actual, impact, analysis)
                            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                        ''', (date, event_time, currency, event, forecast, previous, actual, impact, analysis))
                        logging.info(f"Inserted/Updated event: {date}, {event_time}, {currency}, {event}")
                    except Exception as e:
                        logging.error(f"Failed to insert event into DB: {e}")

            conn.commit()
            conn.close()
            browser.close()
            logging.info("Scraping completed successfully")

    except Exception as e:
        logging.error(f"Scraping failed: {e}")
        if 'conn' in locals():
            conn.close()

# Function to update 'actual' values for past events
def update_actual_values():
    logging.info("Starting to update actual values for past events...")
    conn = sqlite3.connect('news.db')
    c = conn.cursor()

    # Получаем все события, у которых actual = 'N/A' и время события прошло более чем на 1 час
    now = datetime.now(prague_tz)
    c.execute('''
        SELECT date, time, currency, event
        FROM news
        WHERE actual = 'N/A'
    ''')
    events = c.fetchall()

    try:
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            page = browser.new_page()
            page.goto("https://www.forexfactory.com/calendar?day=today", timeout=60000)
            page.wait_for_load_state("networkidle", timeout=60000)

            html = page.content()
            soup = BeautifulSoup(html, "html.parser")
            table = soup.find("table", class_="calendar__table")

            if not table:
                logging.error("Could not find the calendar table on the page")
                browser.close()
                return

            rows = table.find_all("tr", class_=lambda x: x and "calendar__row" in x)
            last_date = None
            last_time = None

            for row in rows:
                date_cell = row.find("td", class_="calendar__cell")
                if date_cell and "calendar__row--day-breaker" in row.get("class", []):
                    date_text = date_cell.text.strip()
                    if date_text:
                        try:
                            date_obj = datetime.strptime(date_text, "%a %b %d")
                            year = datetime.now(prague_tz).year
                            date_obj = date_obj.replace(year=year)
                            date = date_obj.strftime("%Y-%m-%d")
                            last_date = date
                        except ValueError:
                            continue
                else:
                    date = last_date

                if not last_date:
                    continue

                time_cell = row.find("td", class_="calendar__cell--time")
                raw_time = time_cell.text.strip() if time_cell and time_cell.text.strip() else None
                event_time = None
                if raw_time and raw_time.lower() == "all day":
                    continue
                if raw_time:
                    try:
                        time_obj = datetime.strptime(raw_time, "%I:%M%p")
                        event_time = time_obj.strftime("%H:%M")
                        last_time = event_time
                    except ValueError:
                        continue
                else:
                    if last_time:
                        event_time = last_time
                    else:
                        continue

                currency = row.find("td", class_="calendar__cell--currency")
                currency = currency.text.strip() if currency else ""

                event = row.find("td", class_="calendar__cell--event")
                event = event.text.strip() if event else ""

                actual = row.find("td", class_="calendar__cell--actual")
                actual = actual.text.strip() if actual else "N/A"

                # Проверяем, есть ли это событие в списке для обновления
                for event in events:
                    event_date, event_time_db, event_currency, event_name = event
                    if (date == event_date and event_time == event_time_db and
                            currency == event_currency and event == event_name):
                        if actual != "N/A":
                            try:
                                c.execute('''
                                    UPDATE news
                                    SET actual = ?
                                    WHERE date = ? AND time = ? AND currency = ? AND event = ?
                                ''', (actual, event_date, event_time_db, event_currency, event_name))
                                logging.info(f"Updated actual for event: {event_date}, {event_time_db}, {event_currency}, {event_name}, new actual: {actual}")
                            except Exception as e:
                                logging.error(f"Failed to update actual for event: {event_name}, {e}")

            conn.commit()
            conn.close()
            browser.close()
            logging.info("Finished updating actual values")

    except Exception as e:
        logging.error(f"Failed to update actual values: {e}")
        if 'conn' in locals():
            conn.close()

# APScheduler setup
scheduler = BackgroundScheduler(timezone=prague_tz)

# Schedule the initial scrape every 2 minutes for testing
scheduler.add_job(scrape_forex_news, 'interval', minutes=2)

# Schedule the actual value update every hour
scheduler.add_job(update_actual_values, 'interval', hours=1)

# Start the scheduler
scheduler.start()
logging.info("Scheduler started for scraping and updating actual values")

# Run scrape_forex_news immediately for testing
scrape_forex_news()

# Keep the script running
try:
    while True:
        pass
except (KeyboardInterrupt, SystemExit):
    scheduler.shutdown()
    logging.info("Scheduler shut down")
