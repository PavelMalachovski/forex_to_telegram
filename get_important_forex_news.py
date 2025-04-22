import os
import logging
from datetime import datetime
from contextlib import contextmanager
import telebot
import undetected_chromedriver as uc
from bs4 import BeautifulSoup
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

API_TOKEN_TELEGRAM = os.getenv('TELEGRAM_TOKEN')
CHAT_ID = os.getenv('TELEGRAM_CHAT_ID')
bot = telebot.TeleBot(API_TOKEN_TELEGRAM)

logging.basicConfig(filename='scraper.log', level=logging.DEBUG, format='%(asctime)s - %(levelname)s - %(message)s')

def escape_markdown_v2(text):
    special_chars = ['_', '*', '[', ']', '(', ')', '~', '`', '>', '#', '+', '-', '=', '|', '{', '}', '.', '!']
    for char in special_chars:
        text = text.replace(char, f'\{char}')
    return text

@contextmanager
def get_driver():
    options = uc.ChromeOptions()
    options.headless = True
    options.add_argument('--no-sandbox')
    options.add_argument('--disable-dev-shm-usage')
    options.add_argument('--disable-blink-features=AutomationControlled')
    driver = None
    try:
        driver = uc.Chrome(options=options, use_subprocess=True)
        yield driver
    finally:
        if driver:
            driver.quit()

def main():
    try:
        today = datetime.now()
        scraped_date_display = today.strftime("%d.%m.%Y")
        scraped_date_url = today.strftime("%b%d.%Y").lower()
        url = f"https://www.forexfactory.com/calendar?day={scraped_date_url}"

        with get_driver() as driver:
            driver.get(url)
            WebDriverWait(driver, 25).until(
                EC.presence_of_element_located((By.CSS_SELECTOR, 'table.calendar__table tbody'))
            )
            soup = BeautifulSoup(driver.page_source, 'html.parser')

        news_items_formatted = []
        table_body = soup.select_one('table.calendar__table tbody')
        if table_body:
            rows = table_body.select('tr.calendar__row[data-event-id]')
            for row in rows:
                time_tag = row.select_one('.calendar__time span')
                currency_tag = row.select_one('.calendar__currency')
                impact_span = row.select_one('.calendar__impact span.icon')
                event_tag = row.select_one('.calendar__event span.calendar__event-title')
                forecast_tag = row.select_one('.calendar__forecast')
                previous_tag = row.select_one('.calendar__previous')

                if not (currency_tag and impact_span and event_tag):
                    continue

                impact_classes = impact_span.get('class', [])
                if 'icon--ff-impact-red' in impact_classes:
                    news_items_formatted.append(
                        f"⏰ *Time:* {escape_markdown_v2(time_tag.text.strip())}"
                        f"💰 *Currency:* {escape_markdown_v2(currency_tag.text.strip())}"
                        f"📰 *Event:* {escape_markdown_v2(event_tag.text.strip())}"
                        f"📈 *Forecast:* {escape_markdown_v2(forecast_tag.text.strip() if forecast_tag else 'N/A')}"
                        f"📊 *Previous:* {escape_markdown_v2(previous_tag.text.strip() if previous_tag else 'N/A')}"
                        f"\-\-\-"
                    )

        escaped_date = escape_markdown_v2(scraped_date_display)
        message = f"🗓️ *_High\-Impact Forex News for {escaped_date} \(EST\):_*"
        message += "\n".join(news_items_formatted) if news_items_formatted else f"✅ No high\-importance news found for {escaped_date}\."

        if len(message) > 4096:
            message = message[:message.rfind('\n', 0, 4090)] + "\n\n\.\.\. \(message truncated\)"

        bot.send_message(CHAT_ID, message, parse_mode='MarkdownV2')

    except Exception as e:
        error_message = f"⚠️ Script Error: {escape_markdown_v2(str(e))}"
        try:
            if len(error_message) > 4000:
                error_message = error_message[:4000] + "\.\.\."
            bot.send_message(CHAT_ID, error_message, parse_mode='MarkdownV2')
        except Exception as inner:
            logging.error(f"Telegram send error: {inner}")
