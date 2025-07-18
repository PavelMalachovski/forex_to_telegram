
import asyncio
import logging
import random
import time
from datetime import datetime, date, timedelta
from contextlib import asynccontextmanager
from typing import Optional, List, Dict, Any
from collections import defaultdict

import requests
import aiohttp
import undetected_chromedriver as uc
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.action_chains import ActionChains
from selenium.common.exceptions import TimeoutException, WebDriverException
from bs4 import BeautifulSoup
from fake_useragent import UserAgent
from pytz import timezone
import cloudscraper

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


class CloudflareBypass:
    """Advanced Cloudflare bypass using multiple techniques."""
    
    def __init__(self):
        self.ua = UserAgent()
        self.session = None
        self.driver = None
        self.proxies = []
        
    def get_random_user_agent(self):
        """Get a random realistic user agent."""
        agents = [
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36",
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36",
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:122.0) Gecko/20100101 Firefox/122.0",
            "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.2.1 Safari/605.1.15"
        ]
        return random.choice(agents)
    
    def simulate_human_behavior(self, driver):
        """Simulate realistic human behavior."""
        try:
            # Random mouse movements
            actions = ActionChains(driver)
            
            # Move mouse to random positions
            for _ in range(random.randint(2, 5)):
                x = random.randint(100, 800)
                y = random.randint(100, 600)
                actions.move_by_offset(x, y)
                time.sleep(random.uniform(0.1, 0.3))
            
            # Random scrolling
            driver.execute_script(f"window.scrollTo(0, {random.randint(100, 500)});")
            time.sleep(random.uniform(0.5, 1.5))
            
            # Perform actions
            actions.perform()
            
        except Exception as e:
            logger.debug(f"Human behavior simulation error: {e}")
    
    def create_stealth_driver(self):
        """Create an undetected Chrome driver with advanced stealth."""
        try:
            options = uc.ChromeOptions()
            
            # Essential headless options for server environment
            options.add_argument('--headless=new')
            options.add_argument('--no-sandbox')
            options.add_argument('--disable-setuid-sandbox')
            options.add_argument('--disable-dev-shm-usage')
            options.add_argument('--disable-gpu')
            options.add_argument('--remote-debugging-port=0')
            options.add_argument('--disable-web-security')
            options.add_argument('--disable-features=VizDisplayCompositor')
            options.add_argument('--disable-blink-features=AutomationControlled')
            options.add_argument('--disable-extensions')
            options.add_argument('--no-first-run')
            options.add_argument('--disable-default-apps')
            options.add_argument('--disable-sync')
            options.add_argument('--disable-background-networking')
            options.add_argument('--disable-background-timer-throttling')
            options.add_argument('--disable-client-side-phishing-detection')
            options.add_argument('--disable-hang-monitor')
            options.add_argument('--disable-prompt-on-repost')
            options.add_argument('--disable-domain-reliability')
            options.add_argument('--disable-component-extensions-with-background-pages')
            options.add_argument('--single-process')
            options.add_argument('--disable-ipc-flooding-protection')
            
            # Advanced fingerprint spoofing
            options.add_argument(f'--user-agent={self.get_random_user_agent()}')
            options.add_argument('--disable-features=VizDisplayCompositor,VizHitTestSurfaceLayer')
            options.add_argument('--force-color-profile=srgb')
            options.add_argument('--disable-background-media-suspend')
            options.add_argument('--disable-low-res-tiling')
            options.add_argument('--disable-extensions-http-throttling')
            options.add_argument('--disable-features=Translate')
            options.add_argument('--hide-scrollbars')
            options.add_argument('--mute-audio')
            options.add_argument('--no-default-browser-check')
            options.add_argument('--no-pings')
            options.add_argument('--disable-logging')
            options.add_argument('--disable-permissions-api')
            options.add_argument('--ignore-certificate-errors')
            options.add_argument('--ignore-ssl-errors')
            options.add_argument('--ignore-certificate-errors-spki-list')
            
            # Window size randomization
            width = random.randint(1200, 1920)
            height = random.randint(800, 1080)
            options.add_argument(f'--window-size={width},{height}')
            
            # Try to create driver without version_main first
            try:
                driver = uc.Chrome(options=options, headless=True)
            except Exception:
                # Fallback: try with specific version
                driver = uc.Chrome(options=options, version_main=120, headless=True)
            
            # Additional stealth JavaScript
            stealth_js = """
            Object.defineProperty(navigator, 'webdriver', {
                get: () => undefined,
            });
            
            Object.defineProperty(navigator, 'plugins', {
                get: () => [1, 2, 3, 4, 5],
            });
            
            Object.defineProperty(navigator, 'languages', {
                get: () => ['en-US', 'en'],
            });
            
            const originalQuery = window.navigator.permissions.query;
            window.navigator.permissions.query = (parameters) => (
                parameters.name === 'notifications' ?
                    Promise.resolve({ state: Notification.permission }) :
                    originalQuery(parameters)
            );
            
            // Override the `plugins` property to use a custom getter.
            Object.defineProperty(navigator, 'plugins', {
                get: function() {
                    return [1, 2, 3, 4, 5];
                },
            });
            
            // Override the `chrome` property to use a custom getter.
            Object.defineProperty(window, 'chrome', {
                get: function() {
                    return {
                        runtime: {},
                    };
                },
            });
            """
            
            try:
                driver.execute_cdp_cmd('Page.addScriptToEvaluateOnNewDocument', {
                    'source': stealth_js
                })
            except Exception as e:
                logger.debug(f"Could not add stealth JS: {e}")
            
            return driver
            
        except Exception as e:
            logger.error(f"Failed to create stealth driver: {e}")
            return None
    
    async def fetch_with_cloudscraper(self, url: str) -> Optional[str]:
        """Fetch content using cloudscraper as fallback."""
        try:
            # Add random delay to appear more human
            await asyncio.sleep(random.uniform(1, 3))
            
            scraper = cloudscraper.create_scraper(
                browser={
                    'browser': 'chrome',
                    'platform': 'windows',
                    'mobile': False
                },
                delay=random.uniform(1, 3)
            )
            
            headers = {
                'User-Agent': self.get_random_user_agent(),
                'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7',
                'Accept-Language': 'en-US,en;q=0.9',
                'Accept-Encoding': 'gzip, deflate, br',
                'Connection': 'keep-alive',
                'Upgrade-Insecure-Requests': '1',
                'Sec-Fetch-Dest': 'document',
                'Sec-Fetch-Mode': 'navigate',
                'Sec-Fetch-Site': 'none',
                'Sec-Fetch-User': '?1',
                'Cache-Control': 'max-age=0',
                'DNT': '1',
                'Sec-Ch-Ua': '"Not A(Brand";v="99", "Google Chrome";v="121", "Chromium";v="121"',
                'Sec-Ch-Ua-Mobile': '?0',
                'Sec-Ch-Ua-Platform': '"Windows"',
            }
            
            # Multiple attempts with different delays
            for attempt in range(3):
                try:
                    if attempt > 0:
                        await asyncio.sleep(random.uniform(2, 5))
                    
                    response = scraper.get(url, headers=headers, timeout=30)
                    response.raise_for_status()
                    
                    if len(response.text) > 1000:  # Basic content validation
                        return response.text
                    else:
                        logger.warning(f"Cloudscraper got minimal content on attempt {attempt + 1}")
                        
                except Exception as e:
                    logger.warning(f"Cloudscraper attempt {attempt + 1} failed: {e}")
                    if attempt == 2:  # Last attempt
                        raise
            
            return None
            
        except Exception as e:
            logger.error(f"Cloudscraper failed: {e}")
            return None


class ForexFactoryScraper:
    """Simplified ForexFactory scraper with advanced Cloudflare bypass."""
    
    def __init__(self, config: Config):
        self.config = config
        self.bypass = CloudflareBypass()
        self.base_url = "https://www.forexfactory.com"
        
    async def scrape_news(self, target_date: Optional[date] = None) -> List[Dict[str, Any]]:
        """Scrape ForexFactory news with advanced bypass techniques."""
        if target_date is None:
            target_date = date.today()
            
        url = f"{self.base_url}/calendar?day={target_date.strftime('%b%d.%Y').lower()}"
        logger.info(f"Scraping ForexFactory: {url}")
        
        # Try multiple methods in order of preference
        methods = [
            self._scrape_with_undetected_chrome,
            self._scrape_with_cloudscraper,
            self._scrape_with_requests
        ]
        
        for method in methods:
            try:
                content = await method(url)
                if content:
                    news_items = self._parse_forex_factory_content(content)
                    if news_items:
                        logger.info(f"Successfully scraped {len(news_items)} news items using {method.__name__}")
                        return news_items
            except Exception as e:
                logger.warning(f"Method {method.__name__} failed: {e}")
                continue
        
        logger.error("All scraping methods failed for ForexFactory")
        return []
    
    async def _scrape_with_undetected_chrome(self, url: str) -> Optional[str]:
        """Primary method: Use undetected-chromedriver."""
        driver = None
        try:
            driver = self.bypass.create_stealth_driver()
            if not driver:
                return None
            
            # Navigate with human-like behavior
            driver.get(url)
            
            # Wait for potential Cloudflare challenge
            time.sleep(random.uniform(3, 7))
            
            # Simulate human behavior
            self.bypass.simulate_human_behavior(driver)
            
            # Wait for content to load
            wait = WebDriverWait(driver, 20)
            wait.until(EC.presence_of_element_located((By.CLASS_NAME, "calendar_row")))
            
            # Additional human-like delay
            time.sleep(random.uniform(2, 4))
            
            content = driver.page_source
            return content
            
        except TimeoutException:
            logger.warning("Timeout waiting for ForexFactory content")
            return None
        except Exception as e:
            logger.error(f"Undetected Chrome scraping failed: {e}")
            return None
        finally:
            if driver:
                try:
                    driver.quit()
                except:
                    pass
    
    async def _scrape_with_cloudscraper(self, url: str) -> Optional[str]:
        """Fallback method: Use cloudscraper."""
        return await self.bypass.fetch_with_cloudscraper(url)
    
    async def _scrape_with_requests(self, url: str) -> Optional[str]:
        """Last resort: Basic requests with headers."""
        try:
            headers = {
                'User-Agent': self.bypass.get_random_user_agent(),
                'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
                'Accept-Language': 'en-US,en;q=0.5',
                'Accept-Encoding': 'gzip, deflate',
                'Connection': 'keep-alive',
                'Upgrade-Insecure-Requests': '1',
            }
            
            async with aiohttp.ClientSession() as session:
                async with session.get(url, headers=headers, timeout=30) as response:
                    if response.status == 200:
                        return await response.text()
                    else:
                        logger.warning(f"HTTP {response.status} from ForexFactory")
                        return None
                        
        except Exception as e:
            logger.error(f"Requests scraping failed: {e}")
            return None
    
    def _parse_forex_factory_content(self, content: str) -> List[Dict[str, Any]]:
        """Parse ForexFactory HTML content."""
        try:
            soup = BeautifulSoup(content, 'html.parser')
            news_items = []
            
            # Find calendar rows
            calendar_rows = soup.find_all('tr', class_='calendar_row')
            
            current_time = None
            
            for row in calendar_rows:
                try:
                    # Extract time
                    time_cell = row.find('td', class_='calendar__time')
                    if time_cell and time_cell.get_text(strip=True):
                        current_time = time_cell.get_text(strip=True)
                    
                    # Extract currency
                    currency_cell = row.find('td', class_='calendar__currency')
                    if not currency_cell:
                        continue
                    currency = currency_cell.get_text(strip=True)
                    
                    # Extract impact (importance)
                    impact_cell = row.find('td', class_='calendar__impact')
                    impact = 'low'
                    if impact_cell:
                        impact_span = impact_cell.find('span')
                        if impact_span:
                            classes = impact_span.get('class', [])
                            if 'icon--ff-impact-red' in classes:
                                impact = 'high'
                            elif 'icon--ff-impact-ora' in classes:
                                impact = 'medium'
                    
                    # Extract event
                    event_cell = row.find('td', class_='calendar__event')
                    if not event_cell:
                        continue
                    event = event_cell.get_text(strip=True)
                    
                    # Extract actual, forecast, previous
                    actual_cell = row.find('td', class_='calendar__actual')
                    forecast_cell = row.find('td', class_='calendar__forecast')
                    previous_cell = row.find('td', class_='calendar__previous')
                    
                    actual = actual_cell.get_text(strip=True) if actual_cell else ''
                    forecast = forecast_cell.get_text(strip=True) if forecast_cell else ''
                    previous = previous_cell.get_text(strip=True) if previous_cell else ''
                    
                    # Only include high and medium impact news
                    if impact in ['high', 'medium'] and currency and event:
                        news_item = {
                            'time': current_time or 'All Day',
                            'currency': currency,
                            'event': event,
                            'impact': impact,
                            'actual': actual,
                            'forecast': forecast,
                            'previous': previous,
                            'source': 'ForexFactory'
                        }
                        news_items.append(news_item)
                        
                except Exception as e:
                    logger.debug(f"Error parsing row: {e}")
                    continue
            
            return news_items
            
        except Exception as e:
            logger.error(f"Error parsing ForexFactory content: {e}")
            return []


class NewsScraper:
    """Main news scraper class - simplified to use only ForexFactory."""
    
    def __init__(self, config: Config):
        self.config = config
        self.forex_factory = ForexFactoryScraper(config)
        self.chatgpt_analyzer = ChatGPTAnalyzer(config.openai_api_key)
        
    async def scrape_all_news(self, target_date: Optional[date] = None) -> List[Dict[str, Any]]:
        """Scrape news from ForexFactory only."""
        logger.info("Starting ForexFactory news scraping...")
        
        try:
            news_items = await self.forex_factory.scrape_news(target_date)
            
            if not news_items:
                logger.warning("No news items found from ForexFactory")
                return []
            
            # Add ChatGPT analysis if configured
            if self.config.openai_api_key:
                for item in news_items:
                    try:
                        item['analysis'] = self.chatgpt_analyzer.analyze_news(item)
                        # Small delay to avoid rate limiting
                        await asyncio.sleep(1)
                    except Exception as e:
                        logger.error(f"Analysis failed for item: {e}")
                        item['analysis'] = "⚠️ Analysis unavailable"
            
            logger.info(f"Successfully scraped {len(news_items)} news items")
            return news_items
            
        except Exception as e:
            logger.error(f"News scraping failed: {e}")
            return []
    
    def format_news_for_telegram(self, news_items: List[Dict[str, Any]]) -> str:
        """Format news items for Telegram message."""
        if not news_items:
            return "📰 *Forex News Update*\n\nNo significant news events found for today\\."
        
        # Group by impact level
        high_impact = [item for item in news_items if item.get('impact') == 'high']
        medium_impact = [item for item in news_items if item.get('impact') == 'medium']
        
        message_parts = ["📰 *Forex News Update*\n"]
        
        if high_impact:
            message_parts.append("🔴 *HIGH IMPACT EVENTS*")
            for item in high_impact:
                formatted_item = self._format_single_news_item(item)
                message_parts.append(formatted_item)
            message_parts.append("")
        
        if medium_impact:
            message_parts.append("🟡 *MEDIUM IMPACT EVENTS*")
            for item in medium_impact:
                formatted_item = self._format_single_news_item(item)
                message_parts.append(formatted_item)
        
        message_parts.append(f"\n📊 *Total Events:* {len(news_items)}")
        message_parts.append("🏭 *Source:* ForexFactory")
        
        return "\n".join(message_parts)
    
    def _format_single_news_item(self, item: Dict[str, Any]) -> str:
        """Format a single news item."""
        time_str = escape_markdown_v2(item.get('time', 'N/A'))
        currency = escape_markdown_v2(item.get('currency', 'N/A'))
        event = escape_markdown_v2(item.get('event', 'N/A'))
        
        formatted = f"⏰ *{time_str}* \\| 💱 *{currency}*\n📋 {event}"
        
        # Add forecast/actual/previous if available
        details = []
        if item.get('forecast'):
            details.append(f"📈 Forecast: {escape_markdown_v2(item['forecast'])}")
        if item.get('actual'):
            details.append(f"✅ Actual: {escape_markdown_v2(item['actual'])}")
        if item.get('previous'):
            details.append(f"📊 Previous: {escape_markdown_v2(item['previous'])}")
        
        if details:
            separator = ' \\| '
            formatted += f"\n{separator.join(details)}"
        
        # Add analysis if available
        if item.get('analysis'):
            formatted += f"\n🤖 *Analysis:* {item['analysis']}"
        
        return formatted


# Test function for development
async def test_scraper():
    """Test the ForexFactory scraper."""
    from .config import Config
    
    config = Config()
    scraper = NewsScraper(config)
    
    print("Testing ForexFactory scraper...")
    
    # Create mock data for testing when live scraping fails
    mock_news_items = [
        {
            'time': '08:30',
            'currency': 'USD',
            'event': 'Non-Farm Payrolls',
            'impact': 'high',
            'actual': '200K',
            'forecast': '180K',
            'previous': '175K',
            'source': 'ForexFactory'
        },
        {
            'time': '10:00',
            'currency': 'EUR',
            'event': 'ECB Interest Rate Decision',
            'impact': 'high',
            'actual': '',
            'forecast': '4.50%',
            'previous': '4.50%',
            'source': 'ForexFactory'
        }
    ]
    
    try:
        news_items = await scraper.scrape_all_news()
        
        if news_items:
            print(f"✅ Successfully scraped {len(news_items)} news items:")
            for item in news_items[:3]:  # Show first 3 items
                print(f"- {item['time']} | {item['currency']} | {item['event']}")
        else:
            print("⚠️ Live scraping failed, using mock data for testing...")
            news_items = mock_news_items
            
        # Test message formatting
        formatted_message = scraper.format_news_for_telegram(news_items)
        print("\n📱 Formatted Telegram message preview:")
        print("=" * 50)
        print(formatted_message[:500] + "..." if len(formatted_message) > 500 else formatted_message)
        print("=" * 50)
        
        print(f"\n✅ Scraper system is functional with {len(news_items)} items")
        
    except Exception as e:
        print(f"❌ Test failed with error: {e}")
        print("Using mock data for basic functionality test...")
        formatted_message = scraper.format_news_for_telegram(mock_news_items)
        print(f"✅ Basic formatting works: {len(formatted_message)} characters")


if __name__ == "__main__":
    asyncio.run(test_scraper())
