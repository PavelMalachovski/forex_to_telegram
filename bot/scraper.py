import asyncio
import logging
from datetime import datetime
from contextlib import asynccontextmanager
from typing import Optional, List, Dict, Any
from collections import defaultdict

import requests
from bs4 import BeautifulSoup
from playwright.async_api import async_playwright
from pytz import timezone

from .config import Config
from .utils import escape_markdown_v2, send_long_message

logger = logging.getLogger(__name__)


class ChatGPTAnalyzer:
    """Handles ChatGPT API integration for news analysis."""

    def __init__(self, api_key: Optional[str]):
        self.api_key = api_key
        self.api_url = "https://api.openai.com/v1/chat/completions"

    def analyze_news(self, news_item: Dict[str, str]) -> str:
        if not self.api_key:
            return "⚠️ ChatGPT analysis skipped: API key not configured."

        try:
            headers = {
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json",
            }
            prompt = self._create_analysis_prompt(news_item)
            data = {
                "model": "gpt-4",
                "messages": [
                    {"role": "system", "content": "You are a financial analyst specializing in Forex markets."},
                    {"role": "user", "content": prompt},
                ],
                "max_tokens": 150,
                "temperature": 0.7,
            }
            response = requests.post(self.api_url, headers=headers, json=data, timeout=10)
            response.raise_for_status()
            result = response.json()
            analysis = result["choices"][0]["message"]["content"].strip()
            return escape_markdown_v2(analysis)
        except Exception as e:
            logger.error("ChatGPT analysis failed: %s", e)
            return "⚠️ Error in ChatGPT analysis."

    def _create_analysis_prompt(self, news_item: Dict[str, str]) -> str:
        return (
            f"Analyze the following Forex news and predict its potential market impact:\n"
            f"Time: {news_item['time']}\n"
            f"Currency: {news_item['currency']}\n"
            f"Event: {news_item['event']}\n"
            f"Actual: {news_item.get('actual', 'N/A')}\n"
            f"Forecast: {news_item['forecast']}\n"
            f"Previous: {news_item['previous']}\n"
            "Provide a concise analysis (up to 100 words) of how this news might affect the market."
        )


@asynccontextmanager
async def get_browser_page():
    async with async_playwright() as playwright:
        try:
            browser = await playwright.chromium.launch(headless=True)
            page = await browser.new_page()
            await page.set_extra_http_headers({
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
                'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
            })
            try:
                yield page
            finally:
                await browser.close()
        except Exception as e:
            logger.error("Failed to launch browser: %s", e)
            raise


class ForexNewsScraper:
    """Handles scraping of forex news from ForexFactory."""

    def __init__(self, config: Config, analyzer: ChatGPTAnalyzer):
        self.config = config
        self.analyzer = analyzer
        self.base_url = "https://www.forexfactory.com/calendar"
        self.last_seen_time = "N/A"  # Keep track of last seen time

    async def scrape_news(self, target_date: Optional[datetime] = None, impact_level: str = "high", debug: bool = False) -> List[Dict[str, Any]]:
        if target_date is None:
            target_date = datetime.now(timezone(self.config.timezone))
        url = self._build_url(target_date)
        logger.info("Fetching URL: %s", url)
        try:
            async with get_browser_page() as page:
                html = await self._fetch_page_content(page, url)
                news_items = self._parse_news_from_html(html, impact_level)
                for item in news_items:
                    item["analysis"] = self.analyzer.analyze_news(item)
                logger.info("Collected %s news items", len(news_items))
                return news_items
        except Exception as e:
            logger.error("Error scraping news: %s", e)
            return []

    def _build_url(self, target_date: datetime) -> str:
        date_str = target_date.strftime("%b%d.%Y").lower()
        return f"{self.base_url}?day={date_str}"

    async def _fetch_page_content(self, page, url: str) -> str:
        for attempt in range(3):
            try:
                await page.goto(url, timeout=120000)
                await page.wait_for_selector('table.calendar__table', timeout=10000)
                return await page.content()
            except Exception as e:
                if attempt == 2:
                    logger.error("Failed to load page %s after 3 attempts: %s", url, e)
                    raise
                await asyncio.sleep(2)

    def _parse_news_from_html(self, html: str, impact_level: str) -> List[Dict[str, str]]:
        soup = BeautifulSoup(html, 'html.parser')
        rows = (
            soup.select('table.calendar__table tr.calendar__row[data-event-id]')
            or soup.select('table.calendar tr.event')
        )
        logger.info("Found %s total rows", len(rows))
        news_items: List[Dict[str, str]] = []
        
        for row in rows:
            if self._should_include_news(row, impact_level):
                news_item = self._extract_news_data(row)
                if news_item["time"] != "N/A":
                    self.last_seen_time = news_item["time"]
                elif self.last_seen_time != "N/A":
                    # Use last seen time if current row doesn't have time
                    news_item["time"] = self.last_seen_time
                news_items.append(news_item)
        
        return news_items

    def _should_include_news(self, row, impact_level: str) -> bool:
        impact_element = (
            row.select_one('.calendar__impact span.icon')
            or row.select_one('.impact span.icon')
        )
        if not impact_element:
            return False
        
        classes = impact_element.get('class', [])
        is_high = 'icon--ff-impact-red' in classes
        is_medium = 'icon--ff-impact-orange' in classes
        is_low = 'icon--ff-impact-yellow' in classes
        
        # Handle different impact levels
        if impact_level == 'all':
            return is_high or is_medium or is_low
        elif impact_level == 'low':
            return is_low
        elif impact_level == 'medium':
            return is_high or is_medium
        elif impact_level == 'high':
            return is_high
        
        return False

    def _extract_news_data(self, row) -> Dict[str, str]:
        time_elem = row.select_one('.calendar__time')
        time = time_elem.text.strip() if time_elem else "N/A"
        
        # Extract actual value with proper handling
        actual_elem = row.select_one('.calendar__actual')
        actual = "N/A"
        if actual_elem:
            actual_text = actual_elem.text.strip()
            if actual_text and actual_text != "":
                actual = actual_text
        
        return {
            "time": escape_markdown_v2(time),
            "currency": escape_markdown_v2(self._get_text_or_na(row, '.calendar__currency')),
            "event": escape_markdown_v2(self._get_text_or_na(row, '.calendar__event-title')),
            "actual": escape_markdown_v2(actual),
            "forecast": escape_markdown_v2(self._get_text_or_na(row, '.calendar__forecast')),
            "previous": escape_markdown_v2(self._get_text_or_na(row, '.calendar__previous')),
        }

    @staticmethod
    def _get_text_or_na(row, selector: str) -> str:
        element = row.select_one(selector)
        return element.text.strip() if element else 'N/A'


class MessageFormatter:
    """Handles formatting of news messages for Telegram with grouping."""

    @staticmethod
    def format_news_message(news_items: List[Dict[str, Any]], target_date: datetime, impact_level: str) -> str:
        date_str = target_date.strftime("%d.%m.%Y")
        date_escaped = escape_markdown_v2(date_str)
        header = f"🗓️ Forex News for {date_escaped} \\(CET\\):\n\n"
        
        if not news_items:
            impact_escaped = escape_markdown_v2(impact_level)
            return (
                header
                + f"✅ No news found for {date_escaped} with impact: {impact_escaped}\n"
                + "Please check the website for updates."
            )

        # Group events by currency and time
        grouped_events = MessageFormatter._group_events_by_currency_and_time(news_items)
        
        message_parts = [header]
        
        for (currency, time), events in grouped_events.items():
            # Currency and time header
            currency_header = f"💰 **{currency}** \\- {time}\n"
            message_parts.append(currency_header)
            
            for event in events:
                part = (
                    f"📰 Event: {event['event']}\n"
                    f"📊 Actual: {event['actual']}\n"
                    f"📈 Forecast: {event['forecast']}\n"
                    f"📉 Previous: {event['previous']}\n"
                    f"🔍 Analysis: {event['analysis']}\n\n"
                )
                message_parts.append(part)
            
            message_parts.append(f"{'-' * 30}\n\n")
        
        return "".join(message_parts)

    @staticmethod
    def _group_events_by_currency_and_time(news_items: List[Dict[str, Any]]) -> Dict[tuple, List[Dict[str, Any]]]:
        """Group events by currency and time for better presentation."""
        grouped = defaultdict(list)
        
        for item in news_items:
            # Remove escape characters for grouping key
            currency = item['currency'].replace('\\', '')
            time = item['time'].replace('\\', '')
            key = (currency, time)
            grouped[key].append(item)
        
        # Sort by time, then by currency
        def sort_key(item):
            currency, time = item[0]
            # Convert time to sortable format (handle "All Day" and other formats)
            if time == "N/A" or "All Day" in time:
                return (99, currency)  # Put "All Day" events at the end
            try:
                # Try to parse time in various formats
                if ":" in time:
                    if "am" in time.lower() or "pm" in time.lower():
                        time_obj = datetime.strptime(time, "%I:%M%p")
                    else:
                        time_obj = datetime.strptime(time, "%H:%M")
                    return (time_obj.hour * 60 + time_obj.minute, currency)
            except:
                pass
            return (50, currency)  # Default sorting for unparseable times
        
        return dict(sorted(grouped.items(), key=sort_key))


async def process_forex_news(scraper: ForexNewsScraper, bot, config: Config, target_date: Optional[datetime] = None, impact_level: str = "high", debug: bool = False) -> Optional[List[Dict[str, Any]]]:
    if not bot or not config.telegram_chat_id:
        logger.error("Cannot process news: Bot or CHAT_ID not configured")
        return [] if debug else None
    try:
        if target_date is None:
            target_date = datetime.now(timezone(config.timezone))
        news_items = await scraper.scrape_news(target_date, impact_level, debug)
        if debug:
            return news_items
        message = MessageFormatter.format_news_message(news_items, target_date, impact_level)
        if message.strip():
            send_long_message(bot, config.telegram_chat_id, message)
        else:
            logger.error("Generated message is empty")
        return news_items
    except Exception as e:
        logger.exception("Unexpected error in process_forex_news: %s", e)
        try:
            error_msg = escape_markdown_v2(f"⚠️ Error in Forex news scraping: {str(e)}")
            bot.send_message(config.telegram_chat_id, error_msg, parse_mode='MarkdownV2')
        except Exception:
            logger.exception("Failed to send error notification")
        return [] if debug else None


def run_forex_news_sync(scraper: ForexNewsScraper, bot, config: Config):
    return asyncio.run(process_forex_news(scraper, bot, config))


def run_forex_news_for_date(scraper: ForexNewsScraper, bot, config: Config, date_str: Optional[str] = None, impact_level: str = "high", debug: bool = False):
    try:
        target_date = datetime.strptime(date_str, "%Y-%m-%d") if date_str else None
        return asyncio.run(process_forex_news(scraper, bot, config, target_date, impact_level, debug))
    except Exception as e:
        logger.exception("Error parsing date: %s", e)
        return []
