import os
import logging
from datetime import datetime
from contextlib import asynccontextmanager
import telebot
from bs4 import BeautifulSoup
from playwright.async_api import async_playwright
import asyncio

API_TOKEN_TELEGRAM = os.getenv('TELEGRAM_TOKEN')
CHAT_ID = os.getenv('TELEGRAM_CHAT_ID')
bot = telebot.TeleBot(API_TOKEN_TELEGRAM)

logging.basicConfig(filename='scraper.log', level=logging.DEBUG, format='%(asctime)s - %(levelname)s - %(message)s')

def escape_markdown_v2(text):
    special_chars = ['_', '*', '[', ']', '(', ')', '~', '`', '>', '#', '+', '-', '=', '|', '{', '}', '.', '!']
    for char in special_chars:
        text = text.replace(char, f'\\{char}')
    return text

@asynccontextmanager
async def get_page():
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        page = await browser.new_page()
        try:
            yield page
        finally:
            await browser.close()

async def main():
    try:
        today = datetime.now()
        scraped_date_display = today.strftime("%d.%m.%Y")
        scraped_date_url = today.strftime("%b%d.%Y").lower()
        url = f"https://www.forexfactory.com/calendar?day={scraped_date_url}"

        async with get_page() as page:
            await page.goto(url, timeout=30000)
            html = await page.content()

        soup = BeautifulSoup(html, 'html.parser')
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
                        f"⏰ *Time:* {escape_markdown_v2(time_tag.text.strip())}\n"
                        f"💰 *Currency:* {escape_markdown_v2(currency_tag.text.strip())}\n"
                        f"📰 *Event:* {escape_markdown_v2(event_tag.text.strip())}\n"
                        f"📈 *Forecast:* {escape_markdown_v2(forecast_tag.text.strip() if forecast_tag else 'N/A')}\n"
                        f"📊 *Previous:* {escape_markdown_v2(previous_tag.text.strip() if previous_tag else 'N/A')}\n"
                        f"\\-\\-\\-"
                    )

        escaped_date = escape_markdown_v2(scraped_date_display)
        message = f"🗓️ *_High\\-Impact Forex News for {escaped_date} \\(CET\\):_*\n\n"
        message += "\n".join(news_items_formatted) if news_items_formatted else f"✅ No high\\-importance news found for {escaped_date}\\."

        if len(message) > 4096:
            message = message[:message.rfind('\n', 0, 4090)] + "\n\n\\.\\.\\. \\(message truncated\\)"

        bot.send_message(CHAT_ID, message, parse_mode='MarkdownV2')

    except Exception as e:
        error_message = f"⚠️ Script Error: {escape_markdown_v2(str(e))}"
        try:
            if len(error_message) > 4000:
                error_message = error_message[:4000] + "\\.\\.\\."
            bot.send_message(CHAT_ID, error_message, parse_mode='MarkdownV2')
        except Exception as inner:
            logging.error(f"Telegram send error: {inner}")

# 👉 Вызов, который Render запускает
def run_async():
    import subprocess
    chromium_path = "/opt/render/.cache/ms-playwright"
    if not os.path.exists(chromium_path):
        print("▶ Installing Chromium manually at runtime...")
        subprocess.run(["playwright", "install", "chromium"], check=True)
    asyncio.run(main())
