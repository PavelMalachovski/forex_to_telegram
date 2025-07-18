import asyncio
import logging
from datetime import datetime, date, timedelta
from contextlib import asynccontextmanager
from typing import Optional, List, Dict, Any
from collections import defaultdict

import requests
from bs4 import BeautifulSoup
from playwright.async_api import async_playwright
from pytz import timezone

from .config import Config
from .utils import escape_markdown_v2, send_long_message
from .database import get_db_manager

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
        browser = None
        context = None
        
        # Try different browser configurations
        browser_configs = [
            {
                'headless': True,  # Start with headless for server environments
                'args': [
                    '--no-sandbox',
                    '--disable-blink-features=AutomationControlled',
                    '--disable-dev-shm-usage',
                    '--disable-extensions',
                    '--disable-plugins',
                    '--disable-javascript-harmony-shipping',
                    '--disable-background-timer-throttling',
                    '--disable-backgrounding-occluded-windows',
                    '--disable-renderer-backgrounding',
                    '--disable-web-security',
                    '--disable-features=VizDisplayCompositor',
                    '--user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
                ]
            },
            {
                'headless': False,  # Fallback to non-headless if available
                'args': [
                    '--no-sandbox',
                    '--disable-blink-features=AutomationControlled',
                    '--disable-dev-shm-usage',
                    '--disable-web-security',
                    '--user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
                ]
            }
        ]
        
        for config in browser_configs:
            try:
                logger.info(f"Trying browser config: headless={config['headless']}")
                
                browser = await playwright.chromium.launch(**config)
                
                # Create context with realistic settings
                context = await browser.new_context(
                    viewport={'width': 1920, 'height': 1080},
                    user_agent='Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
                    extra_http_headers={
                        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7',
                        'Accept-Language': 'en-US,en;q=0.9',
                        'Accept-Encoding': 'gzip, deflate, br',
                        'DNT': '1',
                        'Connection': 'keep-alive',
                        'Upgrade-Insecure-Requests': '1',
                    }
                )
                
                page = await context.new_page()
                
                # Add script to remove webdriver property
                await page.add_init_script("""
                    Object.defineProperty(navigator, 'webdriver', {
                        get: () => undefined,
                    });
                """)
                
                logger.info("Browser launched successfully")
                
                try:
                    yield page
                finally:
                    if context:
                        await context.close()
                    if browser:
                        await browser.close()
                return
                
            except Exception as e:
                logger.warning(f"Browser config failed: {e}")
                if context:
                    try:
                        await context.close()
                    except:
                        pass
                if browser:
                    try:
                        await browser.close()
                    except:
                        pass
                continue
        
        # If all configs failed
        raise Exception("Failed to launch browser with any configuration")


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
        """Fetch page content with improved error handling and Cloudflare bypass."""
        max_attempts = 5
        base_delay = 2
        
        for attempt in range(max_attempts):
            try:
                logger.info(f"Attempt {attempt + 1}/{max_attempts} to load {url}")
                
                # Navigate to the page with extended timeout
                await page.goto(url, timeout=60000, wait_until='domcontentloaded')
                
                # Add human-like delay
                await asyncio.sleep(3)
                
                # Wait for Cloudflare challenge to complete (if present)
                try:
                    # Check if we're on a Cloudflare challenge page
                    challenge_present = await page.locator('title:has-text("Just a moment")').count() > 0
                    if challenge_present:
                        logger.info("Cloudflare challenge detected, waiting for completion...")
                        # Wait for the challenge to complete (up to 45 seconds)
                        await page.wait_for_function(
                            "document.title !== 'Just a moment...'",
                            timeout=45000
                        )
                        logger.info("Cloudflare challenge completed")
                        # Additional wait after challenge completion
                        await asyncio.sleep(5)
                except Exception as cf_e:
                    logger.warning(f"Cloudflare challenge handling failed: {cf_e}")
                
                # Simulate human behavior - scroll and move mouse
                try:
                    await page.mouse.move(100, 100)
                    await page.mouse.move(200, 200)
                    await asyncio.sleep(1)
                except Exception:
                    pass
                
                # Try multiple selectors with different timeouts
                selectors_to_try = [
                    ('table.calendar__table', 15000),
                    ('table.calendar', 10000),
                    ('table', 5000),
                    ('.calendar__table', 5000)
                ]
                
                table_found = False
                for selector, timeout in selectors_to_try:
                    try:
                        logger.info(f"Trying selector: {selector}")
                        await page.wait_for_selector(selector, timeout=timeout)
                        logger.info(f"Successfully found selector: {selector}")
                        table_found = True
                        break
                    except Exception as selector_e:
                        logger.warning(f"Selector {selector} failed: {selector_e}")
                        continue
                
                if not table_found:
                    raise Exception("No calendar table found with any selector")
                
                # Additional wait to ensure dynamic content is loaded
                await asyncio.sleep(2)
                
                # Verify we have actual content
                content = await page.content()
                if len(content) < 1000:  # Too small, likely an error page
                    raise Exception("Page content too small, likely blocked or error page")
                
                # Check if we have actual calendar data
                table_count = await page.locator('table').count()
                if table_count == 0:
                    raise Exception("No tables found in page content")
                
                logger.info(f"Successfully loaded page with {len(content)} characters")
                return content
                
            except Exception as e:
                delay = base_delay * (2 ** attempt)  # Exponential backoff
                logger.warning(f"Attempt {attempt + 1} failed: {e}")
                
                if attempt == max_attempts - 1:
                    logger.error(f"Failed to load page {url} after {max_attempts} attempts: {e}")
                    raise
                
                logger.info(f"Waiting {delay} seconds before retry...")
                await asyncio.sleep(delay)

    def _parse_news_from_html(self, html: str, impact_level: str) -> List[Dict[str, str]]:
        soup = BeautifulSoup(html, 'html.parser')
        
        # Try multiple selector combinations for finding event rows
        row_selectors = [
            'table.calendar__table tr.calendar__row[data-event-id]',
            'table.calendar__table tr[data-event-id]',
            'table.calendar tr.event',
            'table tr[data-event-id]',
            '.calendar__table tr.calendar__row',
            '.calendar__table tr[data-event-id]'
        ]
        
        rows = []
        for selector in row_selectors:
            rows = soup.select(selector)
            if rows:
                logger.info(f"Found {len(rows)} rows using selector: {selector}")
                break
        
        if not rows:
            logger.warning("No event rows found with any selector")
            # Fallback: try to find any table rows that might contain events
            tables = soup.select('table')
            for table in tables:
                potential_rows = table.select('tr')
                for row in potential_rows:
                    # Check if row has event-like content
                    if (row.select('.calendar__currency') or 
                        row.select('.calendar__event-title') or
                        row.get('data-event-id')):
                        rows.append(row)
            logger.info(f"Fallback found {len(rows)} potential event rows")
        
        news_items: List[Dict[str, str]] = []
        
        for row in rows:
            try:
                if self._should_include_news(row, impact_level):
                    news_item = self._extract_news_data(row)
                    if news_item["time"] != "N/A":
                        self.last_seen_time = news_item["time"]
                    elif self.last_seen_time != "N/A":
                        # Use last seen time if current row doesn't have time
                        news_item["time"] = self.last_seen_time
                    news_items.append(news_item)
            except Exception as e:
                logger.warning(f"Error processing row: {e}")
                continue
        
        logger.info(f"Successfully parsed {len(news_items)} news items")
        return news_items

    def _should_include_news(self, row, impact_level: str) -> bool:
        # Try multiple selectors for impact element
        impact_selectors = [
            '.calendar__impact span.icon',
            '.impact span.icon',
            '.calendar__impact .icon',
            '.impact .icon',
            'span.icon',
            '.icon'
        ]
        
        impact_element = None
        for selector in impact_selectors:
            impact_element = row.select_one(selector)
            if impact_element:
                break
        
        if not impact_element:
            # If no impact element found, check if row has event content
            # and include it for 'all' level
            if impact_level == 'all':
                has_event_content = (
                    row.select_one('.calendar__event-title') or
                    row.select_one('.calendar__currency') or
                    row.get('data-event-id')
                )
                return bool(has_event_content)
            return False
        
        classes = impact_element.get('class', [])
        is_high = any('red' in cls.lower() or 'high' in cls.lower() for cls in classes)
        is_medium = any('orange' in cls.lower() or 'medium' in cls.lower() for cls in classes)
        is_low = any('yellow' in cls.lower() or 'low' in cls.lower() for cls in classes)
        
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
        # Extract time with fallback selectors
        time_selectors = ['.calendar__time', '.time', 'td:first-child']
        time = self._get_text_with_fallback(row, time_selectors)
        
        # Extract currency with fallback selectors
        currency_selectors = ['.calendar__currency', '.currency', 'td:nth-child(2)']
        currency = self._get_text_with_fallback(row, currency_selectors)
        
        # Extract event title with fallback selectors
        event_selectors = ['.calendar__event-title', '.event-title', '.event', 'td:nth-child(3)']
        event = self._get_text_with_fallback(row, event_selectors)
        
        # Extract actual value with proper handling and fallbacks
        actual_selectors = ['.calendar__actual', '.actual', 'td:nth-child(4)']
        actual = self._get_text_with_fallback(row, actual_selectors)
        
        # Extract forecast with fallback selectors
        forecast_selectors = ['.calendar__forecast', '.forecast', 'td:nth-child(5)']
        forecast = self._get_text_with_fallback(row, forecast_selectors)
        
        # Extract previous with fallback selectors
        previous_selectors = ['.calendar__previous', '.previous', 'td:nth-child(6)']
        previous = self._get_text_with_fallback(row, previous_selectors)
        
        return {
            "time": escape_markdown_v2(time),
            "currency": escape_markdown_v2(currency),
            "event": escape_markdown_v2(event),
            "actual": escape_markdown_v2(actual),
            "forecast": escape_markdown_v2(forecast),
            "previous": escape_markdown_v2(previous),
        }

    def _get_text_with_fallback(self, row, selectors: List[str]) -> str:
        """Try multiple selectors to extract text, return 'N/A' if none found."""
        for selector in selectors:
            element = row.select_one(selector)
            if element:
                text = element.text.strip()
                if text and text != "":
                    return text
        return "N/A"

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


def scrape_and_send_forex_data(start_date: date, end_date: date):
    """
    Main function to scrape forex data for a date range and send to telegram.
    Checks database first, scrapes if needed, stores in database, and sends to telegram.
    """
    from .telegram_handlers import get_bot
    
    config = Config()
    bot = get_bot()
    db_manager = get_db_manager()
    
    # Initialize scraper and analyzer
    analyzer = ChatGPTAnalyzer(config.openai_api_key)
    scraper = ForexNewsScraper(config, analyzer)
    
    logger.info(f"Processing forex data from {start_date} to {end_date}")
    
    # Check if data already exists in database
    if db_manager.check_data_exists(start_date, end_date):
        logger.info(f"Data already exists in database for {start_date} to {end_date}")
        # Get existing data from database and send to telegram
        events = db_manager.get_events_by_date_range(start_date, end_date)
        if events:
            _send_database_events_to_telegram(events, bot, config)
        return
    
    # Scrape data for each date in the range
    all_events_data = []
    current_date = start_date
    
    while current_date <= end_date:
        logger.info(f"Scraping data for {current_date}")
        
        # Convert date to datetime for scraper
        target_datetime = datetime.combine(current_date, datetime.min.time())
        target_datetime = timezone(config.timezone).localize(target_datetime)
        
        try:
            # Scrape news for this date
            news_items = asyncio.run(scraper.scrape_news(target_datetime, "high", debug=True))
            
            # Convert scraped data to database format
            for item in news_items:
                event_data = {
                    'currencies': item['currency'].replace('\\', ''),  # Remove escape chars
                    'date': current_date,
                    'impact': 'high',  # We're only scraping high impact
                    'actual': item['actual'].replace('\\', '') if item['actual'] != 'N/A' else None,
                    'forecast': item['forecast'].replace('\\', '') if item['forecast'] != 'N/A' else None,
                    'previous': item['previous'].replace('\\', '') if item['previous'] != 'N/A' else None,
                    'event_title': item['event'].replace('\\', '')  # Remove escape chars
                }
                all_events_data.append(event_data)
                
        except Exception as e:
            logger.error(f"Error scraping data for {current_date}: {e}")
            
        current_date += timedelta(days=1)
    
    # Store all scraped data in database
    if all_events_data:
        try:
            db_manager.insert_events(all_events_data)
            logger.info(f"Stored {len(all_events_data)} events in database")
        except Exception as e:
            logger.error(f"Error storing events in database: {e}")
    
    # Get the stored data from database and send to telegram
    events = db_manager.get_events_by_date_range(start_date, end_date)
    if events:
        _send_database_events_to_telegram(events, bot, config)
    else:
        logger.warning("No events found to send to telegram")


def _send_database_events_to_telegram(events, bot, config: Config):
    """Send events from database to telegram with proper formatting"""
    if not bot or not config.telegram_chat_id:
        logger.error("Cannot send to telegram: Bot or CHAT_ID not configured")
        return
        
    try:
        # Group events by date
        events_by_date = defaultdict(list)
        for event in events:
            events_by_date[event.date].append(event)
        
        # Send message for each date
        for event_date, date_events in sorted(events_by_date.items()):
            # Convert database events to the format expected by MessageFormatter
            formatted_events = []
            for event in date_events:
                formatted_event = {
                    'time': escape_markdown_v2('All Day'),  # Database doesn't store time
                    'currency': escape_markdown_v2(event.currencies or 'N/A'),
                    'event': escape_markdown_v2(event.event_title or 'N/A'),
                    'actual': escape_markdown_v2(event.actual or 'N/A'),
                    'forecast': escape_markdown_v2(event.forecast or 'N/A'),
                    'previous': escape_markdown_v2(event.previous or 'N/A'),
                    'analysis': escape_markdown_v2('Analysis from database')
                }
                formatted_events.append(formatted_event)
            
            # Create datetime object for formatting
            target_datetime = datetime.combine(event_date, datetime.min.time())
            target_datetime = timezone(config.timezone).localize(target_datetime)
            
            # Format and send message
            message = MessageFormatter.format_news_message(formatted_events, target_datetime, 'high')
            if message.strip():
                send_long_message(bot, config.telegram_chat_id, message)
                logger.info(f"Sent telegram message for {event_date}")
            
    except Exception as e:
        logger.error(f"Error sending events to telegram: {e}")
        try:
            error_msg = escape_markdown_v2(f"⚠️ Error sending forex data: {str(e)}")
            bot.send_message(config.telegram_chat_id, error_msg, parse_mode='MarkdownV2')
        except Exception:
            logger.exception("Failed to send error notification")
