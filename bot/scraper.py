import asyncio
import logging
import random
from datetime import datetime
from contextlib import asynccontextmanager
from typing import Optional, List, Dict, Any
from collections import defaultdict
import time

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
    """Enhanced browser context with comprehensive anti-bot detection bypass."""
    async with async_playwright() as playwright:
        try:
            # Enhanced browser launch arguments for stealth
            browser = await playwright.chromium.launch(
                headless=True,
                args=[
                    '--no-sandbox',
                    '--disable-setuid-sandbox',
                    '--disable-dev-shm-usage',
                    '--disable-accelerated-2d-canvas',
                    '--no-first-run',
                    '--no-zygote',
                    '--single-process',
                    '--disable-gpu',
                    '--disable-web-security',
                    '--disable-features=VizDisplayCompositor',
                    '--disable-background-networking',
                    '--disable-background-timer-throttling',
                    '--disable-renderer-backgrounding',
                    '--disable-backgrounding-occluded-windows',
                    '--disable-client-side-phishing-detection',
                    '--disable-component-extensions-with-background-pages',
                    '--disable-default-apps',
                    '--disable-extensions',
                    '--disable-features=TranslateUI',
                    '--disable-hang-monitor',
                    '--disable-ipc-flooding-protection',
                    '--disable-popup-blocking',
                    '--disable-prompt-on-repost',
                    '--disable-sync',
                    '--force-color-profile=srgb',
                    '--metrics-recording-only',
                    '--no-default-browser-check',
                    '--no-pings',
                    '--password-store=basic',
                    '--use-mock-keychain',
                    '--disable-blink-features=AutomationControlled'
                ]
            )
            
            # Create new page with enhanced stealth configuration
            page = await browser.new_page()
            
            # Remove webdriver traces
            await page.add_init_script("""
                Object.defineProperty(navigator, 'webdriver', {
                    get: () => undefined,
                });
                
                // Remove automation indicators
                delete window.cdc_adoQpoasnfa76pfcZLmcfl_Array;
                delete window.cdc_adoQpoasnfa76pfcZLmcfl_Promise;
                delete window.cdc_adoQpoasnfa76pfcZLmcfl_Symbol;
                
                // Mock plugins
                Object.defineProperty(navigator, 'plugins', {
                    get: () => [1, 2, 3, 4, 5],
                });
                
                // Mock languages
                Object.defineProperty(navigator, 'languages', {
                    get: () => ['en-US', 'en'],
                });
                
                // Mock permissions
                const originalQuery = window.navigator.permissions.query;
                window.navigator.permissions.query = (parameters) => (
                    parameters.name === 'notifications' ?
                        Promise.resolve({ state: Notification.permission }) :
                        originalQuery(parameters)
                );
            """)
            
            # Set comprehensive headers with randomization
            user_agents = [
                'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
                'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36',
                'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
                'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
            ]
            
            await page.set_extra_http_headers({
                'User-Agent': random.choice(user_agents),
                'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7',
                'Accept-Language': 'en-US,en;q=0.9',
                'Accept-Encoding': 'gzip, deflate, br',
                'DNT': '1',
                'Connection': 'keep-alive',
                'Upgrade-Insecure-Requests': '1',
                'Sec-Fetch-Dest': 'document',
                'Sec-Fetch-Mode': 'navigate',
                'Sec-Fetch-Site': 'none',
                'Sec-Fetch-User': '?1',
                'Cache-Control': 'max-age=0'
            })
            
            # Set viewport to common resolution
            await page.set_viewport_size({"width": 1366, "height": 768})
            
            try:
                yield page
            finally:
                await browser.close()
        except Exception as e:
            logger.error("Failed to launch browser: %s", e)
            raise


class ForexNewsScraper:
    """Enhanced ForexFactory scraper with anti-bot detection bypass."""

    def __init__(self, config: Config, analyzer: ChatGPTAnalyzer):
        self.config = config
        self.analyzer = analyzer
        self.base_url = "https://www.forexfactory.com/calendar"
        self.last_seen_time = "N/A"
        self.max_retries = 5
        self.base_delay = 2

    async def scrape_news(self, target_date: Optional[datetime] = None, impact_level: str = "high", debug: bool = False) -> List[Dict[str, Any]]:
        if target_date is None:
            target_date = datetime.now(timezone(self.config.timezone))
        url = self._build_url(target_date)
        logger.info("Fetching URL: %s", url)
        
        for attempt in range(self.max_retries):
            try:
                async with get_browser_page() as page:
                    html = await self._fetch_page_content_with_retry(page, url, attempt)
                    if html:
                        news_items = self._parse_news_from_html(html, impact_level)
                        for item in news_items:
                            item["analysis"] = self.analyzer.analyze_news(item)
                        logger.info("Collected %s news items", len(news_items))
                        return news_items
            except Exception as e:
                logger.error("Attempt %d failed: %s", attempt + 1, e)
                if attempt < self.max_retries - 1:
                    delay = self.base_delay * (2 ** attempt) + random.uniform(1, 3)
                    logger.info("Retrying in %.2f seconds...", delay)
                    await asyncio.sleep(delay)
                else:
                    logger.error("All attempts failed. Returning empty list.")
                    return []

    def _build_url(self, target_date: datetime) -> str:
        date_str = target_date.strftime("%b%d.%Y").lower()
        return f"{self.base_url}?day={date_str}"

    async def _fetch_page_content_with_retry(self, page, url: str, attempt: int) -> Optional[str]:
        """Enhanced page fetching with multiple fallback strategies."""
        try:
            # Add random delay to mimic human behavior
            await asyncio.sleep(random.uniform(1, 3))
            
            # Navigate to page with extended timeout
            await page.goto(url, timeout=60000, wait_until='domcontentloaded')
            
            # Wait for page to stabilize
            await asyncio.sleep(random.uniform(2, 4))
            
            # Try multiple selector strategies with dynamic waiting
            selectors_to_try = [
                'table.calendar__table',
                'table.calendar',
                '.calendar__table',
                '.calendar',
                'table[class*="calendar"]',
                'div[class*="calendar"]'
            ]
            
            content = None
            for selector in selectors_to_try:
                try:
                    logger.info("Trying selector: %s", selector)
                    await page.wait_for_selector(selector, timeout=15000)
                    content = await page.content()
                    logger.info("Successfully loaded content with selector: %s", selector)
                    break
                except Exception as selector_error:
                    logger.warning("Selector %s failed: %s", selector, selector_error)
                    continue
            
            if not content:
                # Fallback: try to get content without waiting for specific selectors
                logger.info("All selectors failed, attempting to get page content directly")
                await asyncio.sleep(5)  # Give page more time to load
                content = await page.content()
                
                # Check if we got a meaningful page
                if len(content) < 1000:
                    raise Exception("Page content too short, likely blocked or failed to load")
            
            # Check for common anti-bot indicators
            if self._detect_bot_blocking(content):
                raise Exception("Bot detection triggered")
            
            return content
            
        except Exception as e:
            logger.error("Failed to fetch page content (attempt %d): %s", attempt + 1, e)
            
            # Take screenshot for debugging on final attempt
            if attempt == self.max_retries - 1:
                try:
                    await page.screenshot(path=f'/tmp/forex_scraper_error_{int(time.time())}.png')
                    logger.info("Screenshot saved for debugging")
                except:
                    pass
            
            raise

    def _detect_bot_blocking(self, content: str) -> bool:
        """Detect common bot blocking patterns."""
        blocking_indicators = [
            'blocked',
            'captcha',
            'cloudflare',
            'access denied',
            'forbidden',
            'rate limit',
            'too many requests',
            'suspicious activity',
            'verify you are human'
        ]
        
        content_lower = content.lower()
        for indicator in blocking_indicators:
            if indicator in content_lower:
                logger.warning("Bot blocking detected: %s", indicator)
                return True
        return False

    def _parse_news_from_html(self, html: str, impact_level: str) -> List[Dict[str, str]]:
        soup = BeautifulSoup(html, 'html.parser')
        
        # Try multiple row selectors for different ForexFactory layouts
        row_selectors = [
            'table.calendar__table tr.calendar__row[data-event-id]',
            'table.calendar tr.event',
            'tr.calendar__row',
            'tr[data-event-id]',
            '.calendar__row',
            'tr.event'
        ]
        
        rows = []
        for selector in row_selectors:
            rows = soup.select(selector)
            if rows:
                logger.info("Found %s rows with selector: %s", len(rows), selector)
                break
        
        if not rows:
            logger.warning("No news rows found with any selector")
            return []
        
        news_items: List[Dict[str, str]] = []
        
        for row in rows:
            if self._should_include_news(row, impact_level):
                news_item = self._extract_news_data(row)
                if news_item["time"] != "N/A":
                    self.last_seen_time = news_item["time"]
                elif self.last_seen_time != "N/A":
                    news_item["time"] = self.last_seen_time
                news_items.append(news_item)
        
        return news_items

    def _should_include_news(self, row, impact_level: str) -> bool:
        # Try multiple impact selectors
        impact_selectors = [
            '.calendar__impact span.icon',
            '.impact span.icon',
            '.calendar__impact .icon',
            '.impact .icon',
            'span.icon'
        ]
        
        impact_element = None
        for selector in impact_selectors:
            impact_element = row.select_one(selector)
            if impact_element:
                break
        
        if not impact_element:
            return False
        
        classes = impact_element.get('class', [])
        is_high = 'icon--ff-impact-red' in classes or 'red' in ' '.join(classes).lower()
        is_medium = 'icon--ff-impact-orange' in classes or 'orange' in ' '.join(classes).lower()
        is_low = 'icon--ff-impact-yellow' in classes or 'yellow' in ' '.join(classes).lower()
        
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
        # Enhanced data extraction with multiple selector fallbacks
        def get_text_with_fallbacks(selectors: List[str]) -> str:
            for selector in selectors:
                elem = row.select_one(selector)
                if elem:
                    text = elem.text.strip()
                    if text:
                        return text
            return "N/A"
        
        time = get_text_with_fallbacks([
            '.calendar__time',
            '.time',
            '[class*="time"]'
        ])
        
        currency = get_text_with_fallbacks([
            '.calendar__currency',
            '.currency',
            '[class*="currency"]'
        ])
        
        event = get_text_with_fallbacks([
            '.calendar__event-title',
            '.event-title',
            '.calendar__event',
            '.event',
            '[class*="event"]'
        ])
        
        actual = get_text_with_fallbacks([
            '.calendar__actual',
            '.actual',
            '[class*="actual"]'
        ])
        
        forecast = get_text_with_fallbacks([
            '.calendar__forecast',
            '.forecast',
            '[class*="forecast"]'
        ])
        
        previous = get_text_with_fallbacks([
            '.calendar__previous',
            '.previous',
            '[class*="previous"]'
        ])
        
        return {
            "time": escape_markdown_v2(time),
            "currency": escape_markdown_v2(currency),
            "event": escape_markdown_v2(event),
            "actual": escape_markdown_v2(actual),
            "forecast": escape_markdown_v2(forecast),
            "previous": escape_markdown_v2(previous),
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
        header = f"🗓️ Forex News for {date_escaped} \\\\(CET\\\\):\\n\\n"
        
        if not news_items:
            impact_escaped = escape_markdown_v2(impact_level)
            return (
                header
                + f"✅ No news found for {date_escaped} with impact: {impact_escaped}\\n"
                + "Please check the website for updates."
            )

        # Group events by currency and time
        grouped_events = MessageFormatter._group_events_by_currency_and_time(news_items)
        
        message_parts = [header]
        
        for (currency, time), events in grouped_events.items():
            # Currency and time header
            currency_header = f"💰 **{currency}** \\\\- {time}\\n"
            message_parts.append(currency_header)
            
            for event in events:
                part = (
                    f"📰 Event: {event['event']}\\n"
                    f"📊 Actual: {event['actual']}\\n"
                    f"📈 Forecast: {event['forecast']}\\n"
                    f"📉 Previous: {event['previous']}\\n"
                    f"🔍 Analysis: {event['analysis']}\\n\\n"
                )
                message_parts.append(part)
            
            message_parts.append(f"{'-' * 30}\\n\\n")
        
        return "".join(message_parts)

    @staticmethod
    def _group_events_by_currency_and_time(news_items: List[Dict[str, Any]]) -> Dict[tuple, List[Dict[str, Any]]]:
        """Group events by currency and time for better presentation."""
        grouped = defaultdict(list)
        
        for item in news_items:
            # Remove escape characters for grouping key
            currency = item['currency'].replace('\\\\', '')
            time = item['time'].replace('\\\\', '')
            key = (currency, time)
            grouped[key].append(item)
        
        # Sort by time, then by currency
        def sort_key(item):
            currency, time = item[0]
            # Convert time to sortable format (handle "All Day" and other formats)
            if time == "N/A" or "All Day" in time:
                return (99, currency)  # Put "All Day" events last
            
            # Try to parse time for proper sorting
            try:
                if ':' in time:
                    hour, minute = time.split(':')
                    return (int(hour), int(minute), currency)
                else:
                    return (50, 0, currency)  # Unknown time format
            except (ValueError, IndexError):
                return (50, 0, currency)  # Fallback for unparseable times
        
        return dict(sorted(grouped.items(), key=sort_key))