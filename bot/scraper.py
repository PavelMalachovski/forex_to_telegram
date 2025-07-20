import asyncio
import logging
import random
import time
import subprocess
import tempfile
from datetime import datetime
from contextlib import asynccontextmanager
from typing import Optional, List, Dict, Any
from collections import defaultdict

import requests
from bs4 import BeautifulSoup
from playwright.async_api import async_playwright, TimeoutError as PlaywrightTimeoutError
# Try to import stealth plugin if available
try:
    from playwright_stealth import stealth_async
    HAS_STEALTH = True
except ImportError:
    HAS_STEALTH = False
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


<<<<<<< HEAD
@asynccontextmanager
async def get_browser_page():
    async with async_playwright() as playwright:
        try:
            browser = await playwright.chromium.launch(headless=True, args=[
                '--disable-blink-features=AutomationControlled',
                '--no-sandbox',
                '--disable-dev-shm-usage',
            ])
            page = await browser.new_page()
            await page.set_extra_http_headers({
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
                'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
            })
            # Apply stealth if available
            if HAS_STEALTH:
                await stealth_async(page)
            try:
                yield page
            finally:
                await browser.close()
        except Exception as e:
            logger.error("Failed to launch browser: %s", e)
            raise
=======
class CloudflareBypassError(Exception):
    """Custom exception for Cloudflare bypass failures."""
    pass
>>>>>>> 6dcd4ab582115852787f9eea11fed6d0e1c219cd


class ForexNewsScraper:
    """Enhanced ForexFactory scraper with advanced anti-bot bypass techniques."""
    
    def __init__(self, config: Config, analyzer: ChatGPTAnalyzer):
        self.config = config
        self.analyzer = analyzer
        self.base_url = "https://www.forexfactory.com/calendar"
        self.last_seen_time = "N/A"
        self.max_retries = 3
        self.base_delay = 2
        
        # Enhanced user agents pool
        self.user_agents = [
            'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36',
            'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:121.0) Gecko/20100101 Firefox/121.0',
            'Mozilla/5.0 (Macintosh; Intel Mac OS X 10.15; rv:121.0) Gecko/20100101 Firefox/121.0'
        ]

    async def scrape_news(self, target_date: Optional[datetime] = None, impact_level: str = "high", debug: bool = False) -> List[Dict[str, Any]]:
        """Main scraping method with multiple bypass strategies."""
        if target_date is None:
            target_date = datetime.now(timezone(self.config.timezone))
        
        url = self._build_url(target_date)
        logger.info(f"Fetching URL: {url}")
        
        # Strategy 1: Advanced curl-based scraping (most reliable)
        try:
            logger.info("Attempting Strategy 1: Advanced curl-based scraping")
            news_items = await self._scrape_with_advanced_curl(url, impact_level)
            if news_items:
                logger.info(f"Strategy 1 successful: {len(news_items)} items found")
                for item in news_items:
                    item["analysis"] = self.analyzer.analyze_news(item)
                return news_items
        except Exception as e:
            logger.warning(f"Strategy 1 failed: {e}")
        
        # Strategy 2: Enhanced HTTP with session management
        try:
            logger.info("Attempting Strategy 2: Enhanced HTTP session")
            news_items = await self._scrape_with_enhanced_http(url, impact_level)
            if news_items:
                logger.info(f"Strategy 2 successful: {len(news_items)} items found")
                for item in news_items:
                    item["analysis"] = self.analyzer.analyze_news(item)
                return news_items
        except Exception as e:
            logger.warning(f"Strategy 2 failed: {e}")
        
        # Strategy 3: Advanced Playwright with timeout
        try:
            logger.info("Attempting Strategy 3: Advanced Playwright")
            news_items = await asyncio.wait_for(
                self._scrape_with_advanced_playwright(url, impact_level, debug),
                timeout=90  # 90 second timeout
            )
            if news_items:
                logger.info(f"Strategy 3 successful: {len(news_items)} items found")
                for item in news_items:
                    item["analysis"] = self.analyzer.analyze_news(item)
                return news_items
        except asyncio.TimeoutError:
            logger.warning("Strategy 3 timed out")
        except Exception as e:
            logger.warning(f"Strategy 3 failed: {e}")
        
        logger.error("All scraping strategies failed")
        return []

    async def _scrape_with_advanced_curl(self, url: str, impact_level: str) -> List[Dict[str, Any]]:
        """Strategy 1: Advanced curl with multiple techniques."""
        techniques = [
            self._curl_with_browser_simulation,
            self._curl_with_mobile_headers,
            self._curl_with_minimal_headers
        ]
        
        for i, technique in enumerate(techniques):
            try:
                logger.info(f"Trying curl technique {i+1}")
                result = await technique(url, impact_level)
                if result:
                    return result
            except Exception as e:
                logger.warning(f"Curl technique {i+1} failed: {e}")
                await asyncio.sleep(random.uniform(2, 5))
        
        raise CloudflareBypassError("All curl techniques failed")

    async def _curl_with_browser_simulation(self, url: str, impact_level: str) -> List[Dict[str, Any]]:
        """Curl with full browser simulation."""
        with tempfile.NamedTemporaryFile(mode='w+', suffix='.html', delete=False) as temp_file:
            temp_path = temp_file.name
        
        try:
            curl_cmd = [
                'curl', '-s', '-L', '--compressed', '--max-time', '45',
                '-H', f'User-Agent: {random.choice(self.user_agents)}',
                '-H', 'Accept: text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8',
                '-H', 'Accept-Language: en-US,en;q=0.9',
                '-H', 'Accept-Encoding: gzip, deflate, br',
                '-H', 'Cache-Control: no-cache',
                '-H', 'Pragma: no-cache',
                '-H', 'Sec-Fetch-Dest: document',
                '-H', 'Sec-Fetch-Mode: navigate',
                '-H', 'Sec-Fetch-Site: cross-site',
                '-H', 'Sec-Fetch-User: ?1',
                '-H', 'Upgrade-Insecure-Requests: 1',
                '-H', 'Connection: keep-alive',
                '-b', 'session_id=abc123; preferences=en',  # Add some cookies
                '-o', temp_path,
                url
            ]
            
            process = await asyncio.create_subprocess_exec(
                *curl_cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            
            stdout, stderr = await process.communicate()
            
            if process.returncode != 0:
                raise Exception(f"Curl failed: {stderr.decode()}")
            
            with open(temp_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            logger.info(f"Downloaded {len(content)} characters")
            
            if len(content) < 1000 or self._is_blocked_content(content):
                raise Exception("Content blocked or too short")
            
            return self._parse_news_from_html(content, impact_level)
            
        finally:
            import os
            if os.path.exists(temp_path):
                os.unlink(temp_path)

    async def _curl_with_mobile_headers(self, url: str, impact_level: str) -> List[Dict[str, Any]]:
        """Curl with mobile browser headers."""
        with tempfile.NamedTemporaryFile(mode='w+', suffix='.html', delete=False) as temp_file:
            temp_path = temp_file.name
        
        try:
            curl_cmd = [
                'curl', '-s', '-L', '--compressed', '--max-time', '30',
                '-H', 'User-Agent: Mozilla/5.0 (iPhone; CPU iPhone OS 15_0 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/15.0 Mobile/15E148 Safari/604.1',
                '-H', 'Accept: text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
                '-H', 'Accept-Language: en-US,en;q=0.5',
                '-H', 'Accept-Encoding: gzip, deflate',
                '-H', 'Connection: keep-alive',
                '-o', temp_path,
                url
            ]
            
            process = await asyncio.create_subprocess_exec(
                *curl_cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            
            stdout, stderr = await process.communicate()
            
            if process.returncode != 0:
                raise Exception(f"Mobile curl failed: {stderr.decode()}")
            
            with open(temp_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            if len(content) < 1000 or self._is_blocked_content(content):
                raise Exception("Mobile content blocked")
            
            return self._parse_news_from_html(content, impact_level)
            
        finally:
            import os
            if os.path.exists(temp_path):
                os.unlink(temp_path)

    async def _curl_with_minimal_headers(self, url: str, impact_level: str) -> List[Dict[str, Any]]:
        """Curl with minimal headers to avoid detection."""
        with tempfile.NamedTemporaryFile(mode='w+', suffix='.html', delete=False) as temp_file:
            temp_path = temp_file.name
        
        try:
            curl_cmd = [
                'curl', '-s', '-L', '--max-time', '30',
                '-H', 'User-Agent: curl/7.68.0',
                '-o', temp_path,
                url
            ]
            
            process = await asyncio.create_subprocess_exec(
                *curl_cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            
            stdout, stderr = await process.communicate()
            
            if process.returncode != 0:
                raise Exception(f"Minimal curl failed: {stderr.decode()}")
            
            with open(temp_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            if len(content) < 1000 or self._is_blocked_content(content):
                raise Exception("Minimal content blocked")
            
            return self._parse_news_from_html(content, impact_level)
            
        finally:
            import os
            if os.path.exists(temp_path):
                os.unlink(temp_path)

    async def _scrape_with_enhanced_http(self, url: str, impact_level: str) -> List[Dict[str, Any]]:
        """Strategy 2: Enhanced HTTP with session management."""
        session = requests.Session()
        
        try:
            # First, establish session with main page
            await asyncio.sleep(random.uniform(1, 3))
            
            session.headers.update({
                'User-Agent': random.choice(self.user_agents),
                'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8',
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
            
            # Visit main page first
            main_response = session.get('https://www.forexfactory.com', timeout=30)
            logger.info(f"Main page status: {main_response.status_code}")
            
            # Wait before accessing calendar
            await asyncio.sleep(random.uniform(3, 6))
            
            # Now try calendar
            response = session.get(url, timeout=30)
            
            if response.status_code != 200:
                raise Exception(f"HTTP {response.status_code}")
            
            if len(response.text) < 1000 or self._is_blocked_content(response.text):
                raise Exception("Content blocked")
            
            return self._parse_news_from_html(response.text, impact_level)
            
        finally:
            session.close()

    async def _scrape_with_advanced_playwright(self, url: str, impact_level: str, debug: bool = False) -> List[Dict[str, Any]]:
        """Strategy 3: Advanced Playwright with comprehensive stealth."""
        async with self._get_stealth_browser_context() as page:
            # Navigate with human-like behavior
            await self._human_navigate(page, url)
            
            # Handle challenges
            if await self._detect_and_handle_challenges(page):
                logger.info("Challenges handled, waiting for content...")
                await asyncio.sleep(random.uniform(5, 10))
            
            # Get content
            content = await page.content()
            
            if debug:
                await page.screenshot(path=f'/tmp/forex_playwright_{int(time.time())}.png', full_page=True)
                with open('/tmp/forex_playwright_content.html', 'w', encoding='utf-8') as f:
                    f.write(content)
            
            if self._is_blocked_content(content):
                raise CloudflareBypassError("Still blocked after challenges")
            
            return self._parse_news_from_html(content, impact_level)

    @asynccontextmanager
    async def _get_stealth_browser_context(self):
        """Create advanced stealth browser context."""
        async with async_playwright() as playwright:
            browser = await playwright.chromium.launch(
                headless=True,
                args=[
                    '--no-sandbox',
                    '--disable-setuid-sandbox',
                    '--disable-dev-shm-usage',
                    '--disable-blink-features=AutomationControlled',
                    '--disable-web-security',
                    '--disable-features=VizDisplayCompositor',
                    '--no-first-run',
                    '--disable-default-apps',
                    '--disable-extensions',
                    '--disable-background-networking',
                    '--disable-background-timer-throttling',
                    '--disable-renderer-backgrounding',
                    '--disable-backgrounding-occluded-windows',
                    '--disable-client-side-phishing-detection',
                    '--disable-hang-monitor',
                    '--disable-popup-blocking',
                    '--disable-prompt-on-repost',
                    '--disable-sync',
                    '--metrics-recording-only',
                    '--no-pings',
                    '--password-store=basic',
                    '--use-mock-keychain',
                    '--force-color-profile=srgb'
                ]
            )
            
            context = await browser.new_context(
                viewport={'width': 1366, 'height': 768},
                user_agent=random.choice(self.user_agents),
                locale='en-US',
                timezone_id='America/New_York'
            )
            
            # Advanced stealth script
            await context.add_init_script("""
                // Remove webdriver traces
                Object.defineProperty(navigator, 'webdriver', {
                    get: () => undefined,
                });
                
                // Remove automation indicators
                delete window.cdc_adoQpoasnfa76pfcZLmcfl_Array;
                delete window.cdc_adoQpoasnfa76pfcZLmcfl_Promise;
                delete window.cdc_adoQpoasnfa76pfcZLmcfl_Symbol;
                
                // Mock plugins
                Object.defineProperty(navigator, 'plugins', {
                    get: () => [
                        {name: 'Chrome PDF Plugin', filename: 'internal-pdf-viewer'},
                        {name: 'Chromium PDF Plugin', filename: 'mhjfbmdgcfjbbpaeojofohoefgiehjai'}
                    ],
                });
                
                // Mock languages
                Object.defineProperty(navigator, 'languages', {
                    get: () => ['en-US', 'en'],
                });
                
                // Mock hardware
                Object.defineProperty(navigator, 'hardwareConcurrency', {
                    get: () => 4,
                });
                
                // Mock permissions
                const originalQuery = window.navigator.permissions.query;
                window.navigator.permissions.query = (parameters) => (
                    parameters.name === 'notifications' ?
                        Promise.resolve({ state: 'default' }) :
                        originalQuery(parameters)
                );
            """)
            
            page = await context.new_page()
            
            try:
                yield page
            finally:
                await browser.close()

    async def _human_navigate(self, page, url: str):
        """Navigate like a human user."""
        await asyncio.sleep(random.uniform(1, 3))
        await page.goto(url, timeout=60000, wait_until='domcontentloaded')
        await asyncio.sleep(random.uniform(2, 4))

    async def _detect_and_handle_challenges(self, page) -> bool:
        """Detect and handle various challenges."""
        try:
            title = await page.title()
            if 'just a moment' in title.lower():
                logger.info("Detected Cloudflare challenge")
                
                # Wait for automatic resolution
                for _ in range(30):
                    await asyncio.sleep(1)
                    new_title = await page.title()
                    if 'just a moment' not in new_title.lower():
                        return True
                
                # Try to handle Turnstile if present
                return await self._handle_turnstile(page)
            
            return False
        except Exception as e:
            logger.warning(f"Challenge detection failed: {e}")
            return False

    async def _handle_turnstile(self, page) -> bool:
        """Handle Cloudflare Turnstile challenge."""
        try:
            # Look for Turnstile iframe
            iframe_selector = 'iframe[src*="challenges.cloudflare.com"]'
            await page.wait_for_selector(iframe_selector, timeout=10000)
            
            iframe = await page.query_selector(iframe_selector)
            if not iframe:
                return False
            
            # Get iframe position
            bbox = await iframe.bounding_box()
            if not bbox:
                return False
            
            # Calculate click position
            click_x = bbox['x'] + bbox['width'] / 9
            click_y = bbox['y'] + bbox['height'] / 2
            
            # Human-like mouse movement and click
            await page.mouse.move(click_x, click_y)
            await asyncio.sleep(random.uniform(0.5, 1.5))
            await page.mouse.click(click_x, click_y)
            
            # Wait for completion
            await asyncio.sleep(random.uniform(5, 10))
            
            return True
            
        except Exception as e:
            logger.warning(f"Turnstile handling failed: {e}")
            return False

    def _is_blocked_content(self, content: str) -> bool:
        """Check if content indicates blocking."""
        if len(content) < 1000:
            return True
        
        content_lower = content.lower()
        
        # Check for blocking patterns
        blocking_patterns = [
            ('cloudflare', 'just a moment'),
            ('cloudflare', 'checking your browser'),
            ('access denied', ''),
            ('forbidden', ''),
            ('rate limit', ''),
            ('suspicious activity', '')
        ]
        
        for pattern1, pattern2 in blocking_patterns:
            if pattern1 in content_lower and (not pattern2 or pattern2 in content_lower):
                return True
        
        return False

    def _build_url(self, target_date: datetime) -> str:
        """Build ForexFactory URL for the target date."""
        date_str = target_date.strftime("%b%d.%Y").lower()
        return f"{self.base_url}?day={date_str}"

<<<<<<< HEAD
    async def _fetch_page_content(self, page, url: str) -> str:
        for attempt in range(3):
            try:
                await page.goto(url, timeout=120000)
                # Wait for Cloudflare challenge if present
                if await page.query_selector('div#cf-spinner-please-wait'):
                    logger.info("Cloudflare challenge detected, waiting...")
                    await page.wait_for_selector('table.calendar__table', timeout=30000)
                else:
                    await page.wait_for_selector('table.calendar__table', timeout=10000)
                return await page.content()
            except PlaywrightTimeoutError as e:
                logger.warning(f"Timeout on attempt {attempt+1}: {e}")
                if attempt == 2:
                    logger.error("Failed to load page %s after 3 attempts: %s", url, e)
                    raise
                await asyncio.sleep(3)
            except Exception as e:
                logger.warning(f"Error on attempt {attempt+1}: {e}")
                if attempt == 2:
                    logger.error("Failed to load page %s after 3 attempts: %s", url, e)
                    raise
                await asyncio.sleep(3)

=======
>>>>>>> 6dcd4ab582115852787f9eea11fed6d0e1c219cd
    def _parse_news_from_html(self, html: str, impact_level: str) -> List[Dict[str, str]]:
        """Parse news from HTML content with enhanced selectors."""
        soup = BeautifulSoup(html, 'html.parser')
        
        # Enhanced row selectors
        row_selectors = [
            'table.calendar__table tr.calendar__row',
            'table.calendar tr.calendar__row',
            'tr.calendar__row',
            '.calendar__row',
            'tr[data-event-id]',
            'table tr',
            'tr'
        ]
        
        rows = []
        for selector in row_selectors:
            rows = soup.select(selector)
            if rows:
                logger.info(f"Found {len(rows)} rows with selector: {selector}")
                break
        
        if not rows:
            logger.warning("No news rows found")
            # Save for debugging
            with open('/tmp/forex_debug.html', 'w', encoding='utf-8') as f:
                f.write(html)
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
        """Check if news item should be included based on impact level."""
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
<<<<<<< HEAD
            return False

        classes = impact_element.get('class', [])
        is_high = 'icon--ff-impact-red' in classes
        is_medium = 'icon--ff-impact-orange' in classes
        is_low = 'icon--ff-impact-yellow' in classes

        # Handle different impact levels
=======
            # Fallback: check for meaningful content
            text_content = row.get_text(strip=True)
            if len(text_content) < 10:
                return False
            return any(keyword in text_content.lower() for keyword in ['usd', 'eur', 'gbp', 'jpy', 'cad', 'aud', 'nzd', 'chf'])
        
        classes = impact_element.get('class', [])
        class_str = ' '.join(classes).lower()
        
        is_high = 'icon--ff-impact-red' in classes or 'red' in class_str
        is_medium = 'icon--ff-impact-orange' in classes or 'orange' in class_str
        is_low = 'icon--ff-impact-yellow' in classes or 'yellow' in class_str
        
>>>>>>> 6dcd4ab582115852787f9eea11fed6d0e1c219cd
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
<<<<<<< HEAD
        time_elem = row.select_one('.calendar__time')
        time = time_elem.text.strip() if time_elem else "N/A"

        # Extract actual value with proper handling
        actual_elem = row.select_one('.calendar__actual')
        actual = "N/A"
        if actual_elem:
            actual_text = actual_elem.text.strip()
            if actual_text and actual_text != "":
                actual = actual_text

=======
        """Extract news data from a table row with enhanced fallbacks."""
        def get_text_with_fallbacks(selectors: List[str]) -> str:
            for selector in selectors:
                elem = row.select_one(selector)
                if elem:
                    text = elem.text.strip()
                    if text:
                        return text
            return "N/A"
        
        # Get all cell texts as fallback
        cells = row.find_all(['td', 'th'])
        cell_texts = [cell.get_text(strip=True) for cell in cells if cell.get_text(strip=True)]
        
        time = get_text_with_fallbacks([
            '.calendar__time', '.time', '[class*="time"]'
        ])
        if time == "N/A" and cell_texts:
            time = cell_texts[0] if len(cell_texts) > 0 else "N/A"
        
        currency = get_text_with_fallbacks([
            '.calendar__currency', '.currency', '[class*="currency"]'
        ])
        if currency == "N/A" and len(cell_texts) > 1:
            currency = cell_texts[1]
        
        event = get_text_with_fallbacks([
            '.calendar__event-title', '.event-title', '.calendar__event', '.event', '[class*="event"]'
        ])
        if event == "N/A" and cell_texts:
            event = max(cell_texts, key=len) if cell_texts else "N/A"
        
        actual = get_text_with_fallbacks([
            '.calendar__actual', '.actual', '[class*="actual"]'
        ])
        
        forecast = get_text_with_fallbacks([
            '.calendar__forecast', '.forecast', '[class*="forecast"]'
        ])
        
        previous = get_text_with_fallbacks([
            '.calendar__previous', '.previous', '[class*="previous"]'
        ])
        
>>>>>>> 6dcd4ab582115852787f9eea11fed6d0e1c219cd
        return {
            "time": escape_markdown_v2(time),
            "currency": escape_markdown_v2(currency),
            "event": escape_markdown_v2(event),
            "actual": escape_markdown_v2(actual),
            "forecast": escape_markdown_v2(forecast),
            "previous": escape_markdown_v2(previous),
        }


class MessageFormatter:
    """Handles formatting of news messages for Telegram with grouping."""

    @staticmethod
    def format_news_message(news_items: List[Dict[str, Any]], target_date: datetime, impact_level: str) -> str:
        date_str = target_date.strftime("%d.%m.%Y")
        date_escaped = escape_markdown_v2(date_str)
<<<<<<< HEAD
        header = f"🗓️ Forex News for {date_escaped} \\(CET\\):\n\n"

=======
        header = f"🗓️ Forex News for {date_escaped} \\\\(CET\\\\):\\n\\n"
        
>>>>>>> 6dcd4ab582115852787f9eea11fed6d0e1c219cd
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
<<<<<<< HEAD

            message_parts.append(f"{'-' * 30}\n\n")

=======
            
            message_parts.append(f"{'-' * 30}\\n\\n")
        
>>>>>>> 6dcd4ab582115852787f9eea11fed6d0e1c219cd
        return "".join(message_parts)

    @staticmethod
    def _group_events_by_currency_and_time(news_items: List[Dict[str, Any]]) -> Dict[tuple, List[Dict[str, Any]]]:
        """Group events by currency and time for better presentation."""
        grouped = defaultdict(list)

        for item in news_items:
            # Remove escape characters for grouping key
            currency = item['currency'].replace('\\\\\\\\', '')
            time = item['time'].replace('\\\\\\\\', '')
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
<<<<<<< HEAD
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

=======
                if ':' in time:
                    hour, minute = time.split(':')
                    return (int(hour), int(minute), currency)
                else:
                    return (50, 0, currency)  # Unknown time format
            except (ValueError, IndexError):
                return (50, 0, currency)  # Fallback for unparseable times
        
>>>>>>> 6dcd4ab582115852787f9eea11fed6d0e1c219cd
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
