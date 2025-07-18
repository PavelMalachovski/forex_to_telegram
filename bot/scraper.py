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
    """Production-ready browser context manager with enhanced Cloudflare bypass."""
    async with async_playwright() as playwright:
        browser = None
        context = None
        
        try:
            logger.info("Launching browser in headless production mode")
            
            # Advanced stealth browser configuration for Cloudflare bypass
            browser_args = [
                '--no-sandbox',
                '--disable-setuid-sandbox',
                '--disable-dev-shm-usage',
                '--disable-accelerated-2d-canvas',
                '--no-first-run',
                '--no-zygote',
                '--disable-gpu',
                '--disable-background-timer-throttling',
                '--disable-backgrounding-occluded-windows',
                '--disable-renderer-backgrounding',
                '--disable-features=TranslateUI',
                '--disable-ipc-flooding-protection',
                '--disable-hang-monitor',
                '--disable-prompt-on-repost',
                '--disable-sync',
                '--disable-extensions',
                '--disable-plugins',
                '--disable-web-security',
                '--disable-features=VizDisplayCompositor',
                '--force-color-profile=srgb',
                '--metrics-recording-only',
                '--safebrowsing-disable-auto-update',
                '--password-store=basic',
                '--use-mock-keychain',
                '--disable-blink-features=AutomationControlled',
                '--disable-component-extensions-with-background-pages',
                '--disable-default-apps',
                '--disable-domain-reliability',
                '--disable-background-networking',
                '--disable-client-side-phishing-detection',
                '--disable-features=VizDisplayCompositor,VizHitTestSurfaceLayer',
                '--disable-background-media-suspend',
                '--disable-low-res-tiling',
                '--disable-default-apps',
                '--disable-extensions-http-throttling',
                '--disable-features=Translate',
                '--hide-scrollbars',
                '--mute-audio',
                '--no-default-browser-check',
                '--no-pings',
                '--disable-logging',
                '--disable-permissions-api',
                '--ignore-certificate-errors',
                '--ignore-ssl-errors',
                '--ignore-certificate-errors-spki-list',
                '--user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36'
            ]
            
            browser = await playwright.chromium.launch(
                headless=True,  # ALWAYS headless for production
                args=browser_args,
                slow_mo=100  # Add slight delay to appear more human
            )
            
            # Advanced stealth context configuration
            context = await browser.new_context(
                viewport={'width': 1920, 'height': 1080},  # Full HD resolution
                user_agent='Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36',
                locale='en-US',
                timezone_id='America/New_York',
                java_script_enabled=True,
                bypass_csp=True,
                ignore_https_errors=True,
                extra_http_headers={
                    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7',
                    'Accept-Language': 'en-US,en;q=0.9',
                    'Accept-Encoding': 'gzip, deflate, br',
                    'Cache-Control': 'max-age=0',
                    'Sec-Ch-Ua': '"Not A(Brand";v="99", "Google Chrome";v="121", "Chromium";v="121"',
                    'Sec-Ch-Ua-Mobile': '?0',
                    'Sec-Ch-Ua-Platform': '"Windows"',
                    'Sec-Fetch-Dest': 'document',
                    'Sec-Fetch-Mode': 'navigate',
                    'Sec-Fetch-Site': 'none',
                    'Sec-Fetch-User': '?1',
                    'Upgrade-Insecure-Requests': '1',
                    'Connection': 'keep-alive',
                }
            )
            
            page = await context.new_page()
            
            # Advanced stealth and anti-detection scripts
            await page.add_init_script("""
                // Comprehensive webdriver removal
                Object.defineProperty(navigator, 'webdriver', {
                    get: () => undefined,
                });
                
                // Enhanced plugin mocking
                Object.defineProperty(navigator, 'plugins', {
                    get: () => {
                        return [
                            {
                                0: {type: "application/x-google-chrome-pdf", suffixes: "pdf", description: "Portable Document Format", enabledPlugin: Plugin},
                                description: "Portable Document Format",
                                filename: "internal-pdf-viewer",
                                length: 1,
                                name: "Chrome PDF Plugin"
                            },
                            {
                                0: {type: "application/pdf", suffixes: "pdf", description: "", enabledPlugin: Plugin},
                                description: "",
                                filename: "mhjfbmdgcfjbbpaeojofohoefgiehjai",
                                length: 1,
                                name: "Chrome PDF Viewer"
                            }
                        ];
                    },
                });
                
                // Enhanced language mocking
                Object.defineProperty(navigator, 'languages', {
                    get: () => ['en-US', 'en'],
                });
                
                // Mock platform
                Object.defineProperty(navigator, 'platform', {
                    get: () => 'Win32',
                });
                
                // Mock hardware concurrency
                Object.defineProperty(navigator, 'hardwareConcurrency', {
                    get: () => 4,
                });
                
                // Mock device memory
                Object.defineProperty(navigator, 'deviceMemory', {
                    get: () => 8,
                });
                
                // Enhanced permissions mocking
                const originalQuery = window.navigator.permissions.query;
                window.navigator.permissions.query = (parameters) => (
                    parameters.name === 'notifications' ?
                        Promise.resolve({ state: Notification.permission }) :
                        originalQuery(parameters)
                );
                
                // Comprehensive Chrome runtime mocking
                window.chrome = {
                    runtime: {
                        onConnect: undefined,
                        onMessage: undefined
                    },
                    loadTimes: function() {
                        return {
                            requestTime: Date.now() * 0.001,
                            startLoadTime: Date.now() * 0.001,
                            commitLoadTime: Date.now() * 0.001,
                            finishDocumentLoadTime: Date.now() * 0.001,
                            finishLoadTime: Date.now() * 0.001,
                            firstPaintTime: Date.now() * 0.001,
                            firstPaintAfterLoadTime: 0,
                            navigationType: 'Other',
                            wasFetchedViaSpdy: false,
                            wasNpnNegotiated: false,
                            npnNegotiatedProtocol: 'unknown',
                            wasAlternateProtocolAvailable: false,
                            connectionInfo: 'unknown'
                        };
                    },
                    csi: function() {
                        return {
                            startE: Date.now(),
                            onloadT: Date.now(),
                            pageT: Date.now(),
                            tran: 15
                        };
                    },
                    app: {
                        isInstalled: false,
                        InstallState: {
                            DISABLED: 'disabled',
                            INSTALLED: 'installed',
                            NOT_INSTALLED: 'not_installed'
                        },
                        RunningState: {
                            CANNOT_RUN: 'cannot_run',
                            READY_TO_RUN: 'ready_to_run',
                            RUNNING: 'running'
                        }
                    }
                };
                
                // Mock notification permission
                Object.defineProperty(Notification, 'permission', {
                    get: () => 'default'
                });
                
                // Remove all automation indicators
                delete window.cdc_adoQpoasnfa76pfcZLmcfl_Array;
                delete window.cdc_adoQpoasnfa76pfcZLmcfl_Promise;
                delete window.cdc_adoQpoasnfa76pfcZLmcfl_Symbol;
                delete window.cdc_adoQpoasnfa76pfcZLmcfl_JSON;
                delete window.cdc_adoQpoasnfa76pfcZLmcfl_Object;
                delete window.cdc_adoQpoasnfa76pfcZLmcfl_Proxy;
                delete window.cdc_adoQpoasnfa76pfcZLmcfl_Reflect;
                
                // Mock screen properties
                Object.defineProperty(screen, 'availHeight', {get: () => 1040});
                Object.defineProperty(screen, 'availWidth', {get: () => 1920});
                Object.defineProperty(screen, 'colorDepth', {get: () => 24});
                Object.defineProperty(screen, 'height', {get: () => 1080});
                Object.defineProperty(screen, 'pixelDepth', {get: () => 24});
                Object.defineProperty(screen, 'width', {get: () => 1920});
                
                // Mock connection
                Object.defineProperty(navigator, 'connection', {
                    get: () => ({
                        effectiveType: '4g',
                        rtt: 100,
                        downlink: 2.0
                    })
                });
                
                // Override toString methods to hide automation
                const originalToString = Function.prototype.toString;
                Function.prototype.toString = function() {
                    if (this === navigator.webdriver) {
                        return 'function webdriver() { [native code] }';
                    }
                    return originalToString.apply(this, arguments);
                };
            """)
            
            logger.info("Browser launched successfully in production headless mode")
            
            try:
                yield page
            finally:
                if context:
                    await context.close()
                if browser:
                    await browser.close()
                    
        except Exception as e:
            logger.error(f"Failed to launch browser in production environment: {e}")
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
            raise Exception(f"Production browser launch failed: {e}")


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
        """Fetch page content with enhanced Cloudflare bypass and robust error handling."""
        max_attempts = 5  # Increased attempts
        base_delay = 3
        
        for attempt in range(max_attempts):
            try:
                logger.info(f"Attempt {attempt + 1}/{max_attempts} to load {url}")
                
                # Set additional page settings for better compatibility
                await page.set_extra_http_headers({
                    'Referer': 'https://www.google.com/',
                    'Origin': 'https://www.forexfactory.com',
                    'X-Forwarded-For': '8.8.8.8',  # Use Google DNS IP
                    'X-Real-IP': '8.8.8.8'
                })
                
                # Add longer initial delay to avoid rate limiting
                if attempt > 0:
                    delay_time = 10 + (attempt * 5)  # Progressive delay
                    logger.info(f"Adding {delay_time}s delay before attempt {attempt + 1}")
                    await asyncio.sleep(delay_time)
                
                # Navigate with extended timeout and wait for network idle
                logger.info(f"Navigating to {url}...")
                response = await page.goto(
                    url, 
                    timeout=180000,  # 3 minutes timeout
                    wait_until='domcontentloaded'  # Changed from networkidle for faster loading
                )
                
                if response and response.status >= 400:
                    logger.warning(f"HTTP {response.status} response received")
                    if response.status == 403:
                        raise Exception(f"Access forbidden (403) - likely blocked by Cloudflare")
                    elif response.status >= 500:
                        raise Exception(f"Server error ({response.status})")
                
                # Initial human-like delay
                await asyncio.sleep(3)
                
                # Enhanced Cloudflare detection and handling
                await self._handle_cloudflare_challenge(page)
                
                # Simulate realistic human browsing behavior
                await self._simulate_human_behavior(page)
                
                # Modern ForexFactory selectors (updated for 2024/2025 structure)
                calendar_selectors = [
                    # Primary modern selectors
                    ('.calendar-container', 25000),
                    ('.calendar-wrapper', 25000),
                    ('.calendar', 20000),
                    
                    # Table-based selectors
                    ('table[class*="calendar"]', 20000),
                    ('table.calendar__table', 15000),
                    ('.calendar__table', 15000),
                    
                    # Event container selectors
                    ('.calendar-events', 15000),
                    ('.events-container', 15000),
                    ('[data-calendar]', 15000),
                    
                    # Fallback selectors
                    ('table[data-table="calendar"]', 10000),
                    ('[data-testid*="calendar"]', 10000),
                    ('table', 8000),
                    
                    # Last resort selectors
                    ('.fc-event-container', 5000),
                    ('[class*="event"]', 5000)
                ]
                
                calendar_found = False
                successful_selector = None
                
                # Try each selector with proper error handling
                for selector, timeout in calendar_selectors:
                    try:
                        logger.info(f"Trying calendar selector: {selector} (timeout: {timeout}ms)")
                        
                        # Wait for selector with timeout
                        await page.wait_for_selector(selector, timeout=timeout)
                        
                        # Verify the element actually contains content
                        element_count = await page.locator(selector).count()
                        if element_count > 0:
                            logger.info(f"✅ Found calendar with selector: {selector} ({element_count} elements)")
                            calendar_found = True
                            successful_selector = selector
                            break
                        else:
                            logger.warning(f"Selector {selector} found but no elements")
                            
                    except Exception as selector_e:
                        logger.debug(f"Selector {selector} failed: {selector_e}")
                        continue
                
                # Additional wait for dynamic content loading
                if calendar_found:
                    logger.info("Calendar found, waiting for content to load...")
                    await asyncio.sleep(5)
                    
                    # Wait for actual event rows to load
                    try:
                        await page.wait_for_function(
                            """() => {
                                const rows = document.querySelectorAll('tr[data-event-id], tr.calendar__row, .event-row, tr[class*="event"]');
                                return rows.length > 0;
                            }""",
                            timeout=15000
                        )
                        logger.info("Event rows detected and loaded")
                    except:
                        logger.warning("No event rows detected, but proceeding anyway")
                
                # Get page content and validate
                content = await page.content()
                page_title = await page.title()
                current_url = page.url
                
                logger.info(f"Page loaded - Title: '{page_title}', URL: {current_url}, Content size: {len(content)} chars")
                
                # Enhanced content validation
                if len(content) < 5000:
                    raise Exception(f"Page content too small ({len(content)} chars) - likely error or blocked")
                
                # Check for Cloudflare block indicators
                content_lower = content.lower()
                if any(indicator in content_lower for indicator in [
                    'just a moment', 'checking your browser', 'cloudflare', 'ray id',
                    'enable javascript', 'browser check', 'ddos protection'
                ]):
                    raise Exception("Still on Cloudflare challenge/block page")
                
                # Validate we're on the correct ForexFactory page
                if not any(indicator in content_lower for indicator in [
                    'forex factory', 'forexfactory', 'calendar', 'economic events'
                ]):
                    logger.warning(f"Unexpected page content - Title: {page_title}")
                    # Don't fail here, might still be valid content
                
                # Check for actual forex event content
                event_indicators = [
                    'usd', 'eur', 'gbp', 'jpy', 'aud', 'cad', 'chf', 'nzd',
                    'impact', 'forecast', 'actual', 'previous', 'event'
                ]
                
                has_forex_content = any(indicator in content_lower for indicator in event_indicators)
                if not has_forex_content and not calendar_found:
                    logger.warning("No forex event content detected")
                
                logger.info(f"✅ Successfully loaded ForexFactory page using selector: {successful_selector}")
                logger.info(f"Content validation: Calendar found={calendar_found}, Forex content={has_forex_content}")
                
                return content
                
            except Exception as e:
                delay = base_delay * (2 ** attempt)  # Exponential backoff
                logger.warning(f"❌ Attempt {attempt + 1}/{max_attempts} failed: {e}")
                
                if attempt == max_attempts - 1:
                    logger.error(f"🚨 Failed to load ForexFactory after {max_attempts} attempts")
                    logger.error(f"Final error: {e}")
                    raise Exception(f"ForexFactory scraping failed after {max_attempts} attempts: {e}")
                
                logger.info(f"⏳ Waiting {delay} seconds before retry {attempt + 2}...")
                await asyncio.sleep(delay)
    
    async def _handle_cloudflare_challenge(self, page):
        """Enhanced Cloudflare challenge detection and handling."""
        try:
            # Check for various Cloudflare indicators
            cf_indicators = [
                'title:has-text("Just a moment")',
                'title:has-text("Checking your browser")',
                'title:has-text("Please wait")',
                '[data-ray]',
                '.cf-browser-verification',
                '#challenge-form',
                '.cf-wrapper',
                '.cf-error-overview'
            ]
            
            challenge_detected = False
            for indicator in cf_indicators:
                try:
                    if await page.locator(indicator).count() > 0:
                        challenge_detected = True
                        logger.info(f"🛡️ Cloudflare challenge detected: {indicator}")
                        break
                except:
                    continue
            
            if challenge_detected:
                logger.info("⏳ Waiting for Cloudflare challenge completion...")
                
                # Wait for challenge to complete with multiple strategies
                try:
                    # Strategy 1: Wait for title change
                    await page.wait_for_function(
                        """() => {
                            const title = document.title.toLowerCase();
                            return !title.includes('just a moment') && 
                                   !title.includes('checking your browser') &&
                                   !title.includes('please wait');
                        }""",
                        timeout=45000
                    )
                    logger.info("✅ Cloudflare challenge completed (title changed)")
                    
                except:
                    try:
                        # Strategy 2: Wait for challenge elements to disappear
                        await page.wait_for_function(
                            """() => {
                                return !document.querySelector('[data-ray]') &&
                                       !document.querySelector('.cf-browser-verification') &&
                                       !document.querySelector('#challenge-form');
                            }""",
                            timeout=30000
                        )
                        logger.info("✅ Cloudflare challenge completed (elements removed)")
                        
                    except:
                        # Strategy 3: Fixed wait as fallback
                        logger.warning("⚠️ Using fallback wait for Cloudflare challenge")
                        await asyncio.sleep(15)
                
                # Additional wait after challenge completion
                await asyncio.sleep(5)
                logger.info("✅ Cloudflare challenge handling completed")
                
        except Exception as cf_e:
            logger.warning(f"⚠️ Cloudflare challenge handling error: {cf_e}")
    
    async def _simulate_human_behavior(self, page):
        """Simulate realistic human browsing behavior."""
        try:
            # Random mouse movements
            import random
            
            # Move mouse to random positions
            for _ in range(2):
                x = random.randint(100, 800)
                y = random.randint(100, 600)
                await page.mouse.move(x, y)
                await asyncio.sleep(random.uniform(0.3, 0.8))
            
            # Simulate scrolling behavior
            scroll_positions = [200, 400, 600, 300, 0]
            for pos in scroll_positions:
                await page.evaluate(f"window.scrollTo(0, {pos})")
                await asyncio.sleep(random.uniform(0.5, 1.2))
            
            # Random delay to appear more human
            await asyncio.sleep(random.uniform(1, 3))
            
        except Exception as e:
            logger.debug(f"Human behavior simulation failed: {e}")
            # Don't fail the whole process for this

    def _parse_news_from_html(self, html: str, impact_level: str) -> List[Dict[str, str]]:
        """Parse HTML content to extract forex news events with enhanced selectors."""
        soup = BeautifulSoup(html, 'html.parser')
        
        # Modern ForexFactory row selectors (updated for 2024/2025)
        row_selectors = [
            # Primary modern selectors with data attributes
            'tr[data-event-id]',
            'tr[data-event]',
            '.calendar tr[data-event-id]',
            '.calendar-container tr[data-event-id]',
            '.calendar-wrapper tr[data-event-id]',
            
            # Table-based selectors
            'table.calendar__table tr.calendar__row',
            'table.calendar__table tr[data-event-id]',
            'table[class*="calendar"] tr[data-event-id]',
            '.calendar__table tr.calendar__row',
            '.calendar__table tr[data-event-id]',
            
            # Event row selectors
            '.event-row',
            'tr.event-row',
            'tr[class*="event"]',
            'tr[class*="calendar"]',
            
            # Generic fallback selectors
            '.calendar tr',
            'table tr[data-event-id]',
            '[class*="calendar"] tr',
            '[data-calendar] tr'
        ]
        
        rows = []
        successful_selector = None
        
        # Try each selector in order of preference
        for selector in row_selectors:
            try:
                found_rows = soup.select(selector)
                if found_rows:
                    # Filter out header rows and empty rows
                    valid_rows = []
                    for row in found_rows:
                        # Skip header rows
                        if row.find('th'):
                            continue
                        # Skip rows with no meaningful content
                        if not row.find('td'):
                            continue
                        # Check if row has at least some forex-related content
                        row_text = row.get_text().strip().lower()
                        if len(row_text) > 10:  # Has some content
                            valid_rows.append(row)
                    
                    if valid_rows:
                        rows = valid_rows
                        successful_selector = selector
                        logger.info(f"✅ Found {len(rows)} valid event rows using selector: {selector}")
                        break
                        
            except Exception as e:
                logger.debug(f"Selector {selector} failed: {e}")
                continue
        
        # Enhanced fallback methods if no rows found
        if not rows:
            logger.warning("🔍 No event rows found with primary selectors, trying enhanced fallback methods")
            
            # Method 1: Look for tables with forex-like content
            tables = soup.select('table')
            for table in tables:
                table_text = table.get_text().lower()
                # Check if table contains forex indicators
                if any(indicator in table_text for indicator in [
                    'usd', 'eur', 'gbp', 'jpy', 'impact', 'forecast', 'actual', 'previous'
                ]):
                    potential_rows = table.select('tr')
                    for row in potential_rows:
                        # Skip header rows
                        if row.find('th'):
                            continue
                        
                        # Check if row has event-like content
                        has_event_content = (
                            # Look for specific forex factory classes
                            row.select('.calendar__currency') or 
                            row.select('.calendar__event-title') or
                            row.select('.calendar__impact') or
                            row.select('[class*="currency"]') or
                            row.select('[class*="event"]') or
                            row.select('[class*="impact"]') or
                            # Look for data attributes
                            row.get('data-event-id') or
                            row.get('data-event') or
                            # Check for minimum column count
                            (len(row.find_all('td')) >= 4)
                        )
                        
                        if has_event_content:
                            rows.append(row)
            
            logger.info(f"📊 Table-based fallback found {len(rows)} potential event rows")
            
            # Method 2: More aggressive content-based search
            if not rows:
                logger.warning("🔍 Trying aggressive content-based fallback")
                all_rows = soup.select('tr')
                
                for row in all_rows:
                    # Skip header rows
                    if row.find('th'):
                        continue
                    
                    cells = row.find_all('td')
                    if len(cells) >= 3:  # Minimum columns for potential forex event
                        row_text = row.get_text().strip().lower()
                        
                        # Check for forex indicators
                        has_forex_indicators = any(currency in row_text for currency in [
                            'usd', 'eur', 'gbp', 'jpy', 'aud', 'cad', 'chf', 'nzd'
                        ])
                        
                        # Check for time patterns (HH:MM format)
                        import re
                        has_time_pattern = bool(re.search(r'\d{1,2}:\d{2}', row_text))
                        
                        # Check for economic event keywords
                        has_event_keywords = any(keyword in row_text for keyword in [
                            'rate', 'gdp', 'inflation', 'employment', 'cpi', 'pmi', 
                            'retail', 'manufacturing', 'services', 'trade', 'balance'
                        ])
                        
                        if has_forex_indicators or (has_time_pattern and has_event_keywords):
                            rows.append(row)
                
                logger.info(f"🎯 Aggressive fallback found {len(rows)} potential rows")
        
        # Process found rows
        news_items: List[Dict[str, str]] = []
        processed_count = 0
        skipped_count = 0
        
        for i, row in enumerate(rows):
            try:
                # Check if row should be included based on impact level
                if self._should_include_news(row, impact_level):
                    news_item = self._extract_news_data(row)
                    
                    # Enhanced content validation
                    has_meaningful_content = (
                        news_item["event"] != "N/A" or 
                        news_item["currency"] != "N/A" or 
                        news_item["time"] != "N/A"
                    )
                    
                    if has_meaningful_content:
                        # Time tracking logic for rows without explicit time
                        if news_item["time"] != "N/A":
                            self.last_seen_time = news_item["time"]
                        elif self.last_seen_time != "N/A":
                            news_item["time"] = self.last_seen_time
                        
                        news_items.append(news_item)
                        processed_count += 1
                    else:
                        skipped_count += 1
                        logger.debug(f"Skipped row {i+1}: no meaningful content")
                else:
                    skipped_count += 1
                    logger.debug(f"Skipped row {i+1}: doesn't match impact level {impact_level}")
                    
            except Exception as e:
                logger.warning(f"❌ Error processing row {i+1}: {e}")
                skipped_count += 1
                continue
        
        logger.info(f"📈 Parsing complete: {len(news_items)} news items extracted")
        logger.info(f"📊 Processing stats: {processed_count} processed, {skipped_count} skipped, {len(rows)} total rows")
        logger.info(f"🎯 Successful selector: {successful_selector}")
        
        # Enhanced debug information if no news items found
        if not news_items:
            logger.warning("⚠️ No news items extracted - Debug information:")
            logger.warning(f"   Total rows found: {len(rows)}")
            logger.warning(f"   HTML content size: {len(html)} characters")
            logger.warning(f"   Impact level filter: {impact_level}")
            
            # Sample HTML structure analysis
            sample_tables = soup.select('table')[:3]  # First 3 tables
            for i, table in enumerate(sample_tables):
                table_classes = table.get('class', [])
                table_id = table.get('id', 'no-id')
                logger.warning(f"   Table {i+1}: classes={table_classes}, id={table_id}")
                
                sample_rows = table.select('tr')[:5]  # First 5 rows
                for j, row in enumerate(sample_rows):
                    row_classes = row.get('class', [])
                    cell_count = len(row.find_all(['td', 'th']))
                    row_text_sample = row.get_text().strip()[:100]  # First 100 chars
                    logger.warning(f"     Row {j+1}: classes={row_classes}, cells={cell_count}, text='{row_text_sample}...'")
            
            # Check for common ForexFactory elements
            ff_elements = {
                'calendar containers': soup.select('[class*="calendar"]'),
                'event elements': soup.select('[class*="event"]'),
                'impact elements': soup.select('[class*="impact"]'),
                'currency elements': soup.select('[class*="currency"]'),
                'data attributes': soup.select('[data-event-id], [data-event]')
            }
            
            for element_type, elements in ff_elements.items():
                logger.warning(f"   Found {len(elements)} {element_type}")
        
        return news_items

    def _should_include_news(self, row, impact_level: str) -> bool:
        """Determine if a news row should be included based on impact level."""
        
        # Enhanced impact selectors for modern ForexFactory
        impact_selectors = [
            # Modern impact selectors
            '.calendar__impact .icon',
            '.calendar__impact span.icon',
            '.impact .icon',
            '.impact span.icon',
            
            # Alternative impact selectors
            '[class*="impact"] .icon',
            '[class*="impact"] span',
            '.event-impact .icon',
            '.event-impact span',
            
            # Generic icon selectors
            'span.icon',
            '.icon',
            'i.icon',
            
            # Fallback selectors
            '[data-impact]',
            '[class*="bull"]',  # ForexFactory uses bull icons for impact
            '.ff-impact'
        ]
        
        impact_element = None
        impact_selector_used = None
        
        # Try each impact selector
        for selector in impact_selectors:
            impact_element = row.select_one(selector)
            if impact_element:
                impact_selector_used = selector
                break
        
        # If no impact element found, use fallback logic
        if not impact_element:
            logger.debug("No impact element found, using fallback logic")
            
            # For 'all' level, include any row with event content
            if impact_level == 'all':
                has_event_content = (
                    row.select_one('.calendar__event-title') or
                    row.select_one('.calendar__currency') or
                    row.select_one('[class*="event"]') or
                    row.select_one('[class*="currency"]') or
                    row.get('data-event-id') or
                    row.get('data-event') or
                    (len(row.find_all('td')) >= 4)  # Has enough columns
                )
                return bool(has_event_content)
            
            # For specific impact levels, be more conservative
            return False
        
        # Analyze impact element to determine impact level
        classes = impact_element.get('class', [])
        class_str = ' '.join(classes).lower()
        
        # Check element attributes and content
        data_impact = impact_element.get('data-impact', '').lower()
        title = impact_element.get('title', '').lower()
        text_content = impact_element.get_text().strip().lower()
        
        # Enhanced impact detection patterns
        is_high = any([
            # Class-based detection
            any(pattern in class_str for pattern in ['red', 'high', 'bull3', 'impact-high']),
            # Data attribute detection
            any(pattern in data_impact for pattern in ['high', '3', 'red']),
            # Title/tooltip detection
            any(pattern in title for pattern in ['high', 'red', 'important']),
            # Content-based detection (some sites use text)
            any(pattern in text_content for pattern in ['high', 'h', '●●●'])
        ])
        
        is_medium = any([
            # Class-based detection
            any(pattern in class_str for pattern in ['orange', 'medium', 'bull2', 'impact-medium', 'yellow']),
            # Data attribute detection
            any(pattern in data_impact for pattern in ['medium', '2', 'orange', 'yellow']),
            # Title/tooltip detection
            any(pattern in title for pattern in ['medium', 'orange', 'moderate']),
            # Content-based detection
            any(pattern in text_content for pattern in ['medium', 'm', '●●'])
        ])
        
        is_low = any([
            # Class-based detection
            any(pattern in class_str for pattern in ['gray', 'grey', 'low', 'bull1', 'impact-low']),
            # Data attribute detection
            any(pattern in data_impact for pattern in ['low', '1', 'gray', 'grey']),
            # Title/tooltip detection
            any(pattern in title for pattern in ['low', 'gray', 'minor']),
            # Content-based detection
            any(pattern in text_content for pattern in ['low', 'l', '●'])
        ])
        
        # Log impact detection for debugging
        if any([is_high, is_medium, is_low]):
            impact_type = 'high' if is_high else ('medium' if is_medium else 'low')
            logger.debug(f"Impact detected: {impact_type} using selector {impact_selector_used}")
            logger.debug(f"  Classes: {classes}")
            logger.debug(f"  Data-impact: {data_impact}")
            logger.debug(f"  Title: {title}")
        
        # Apply impact level filtering
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
        """Extract news data from a table row with enhanced selectors."""
        
        # Enhanced time selectors for modern ForexFactory
        time_selectors = [
            # Primary time selectors
            '.calendar__time',
            '.time',
            '.event-time',
            
            # Alternative time selectors
            '[class*="time"]',
            '[data-time]',
            '.ff-time',
            
            # Positional selectors (time is usually first column)
            'td:first-child',
            'td:nth-child(1)',
            
            # Generic fallbacks
            '.col-time',
            '.time-cell'
        ]
        time = self._get_text_with_fallback(row, time_selectors)
        
        # Enhanced currency selectors
        currency_selectors = [
            # Primary currency selectors
            '.calendar__currency',
            '.currency',
            '.event-currency',
            
            # Flag-based selectors (ForexFactory uses flag images)
            '.flag',
            '[class*="flag"]',
            '.currency-flag',
            
            # Alternative currency selectors
            '[class*="currency"]',
            '[data-currency]',
            '.ff-currency',
            
            # Positional selectors (currency usually second column)
            'td:nth-child(2)',
            
            # Generic fallbacks
            '.col-currency',
            '.currency-cell'
        ]
        currency = self._get_text_with_fallback(row, currency_selectors)
        
        # Enhanced event title selectors
        event_selectors = [
            # Primary event selectors
            '.calendar__event-title',
            '.event-title',
            '.event-name',
            '.event',
            
            # Alternative event selectors
            '[class*="event"]',
            '[data-event-title]',
            '[data-event-name]',
            '.ff-event',
            
            # Title-based selectors
            '.title',
            '[class*="title"]',
            '.event-description',
            
            # Positional selectors (event usually third column)
            'td:nth-child(3)',
            
            # Generic fallbacks
            '.col-event',
            '.event-cell'
        ]
        event = self._get_text_with_fallback(row, event_selectors)
        
        # Enhanced actual value selectors
        actual_selectors = [
            # Primary actual selectors
            '.calendar__actual',
            '.actual',
            '.event-actual',
            
            # Alternative actual selectors
            '[class*="actual"]',
            '[data-actual]',
            '.ff-actual',
            '.value-actual',
            '.result',
            '.released',
            
            # Positional selectors (actual usually fourth column)
            'td:nth-child(4)',
            
            # Generic fallbacks
            '.col-actual',
            '.actual-cell'
        ]
        actual = self._get_text_with_fallback(row, actual_selectors)
        
        # Enhanced forecast selectors
        forecast_selectors = [
            # Primary forecast selectors
            '.calendar__forecast',
            '.forecast',
            '.event-forecast',
            
            # Alternative forecast selectors
            '[class*="forecast"]',
            '[data-forecast]',
            '.ff-forecast',
            '.value-forecast',
            '.expected',
            '.consensus',
            
            # Positional selectors (forecast usually fifth column)
            'td:nth-child(5)',
            
            # Generic fallbacks
            '.col-forecast',
            '.forecast-cell'
        ]
        forecast = self._get_text_with_fallback(row, forecast_selectors)
        
        # Enhanced previous value selectors
        previous_selectors = [
            # Primary previous selectors
            '.calendar__previous',
            '.previous',
            '.event-previous',
            
            # Alternative previous selectors
            '[class*="previous"]',
            '[data-previous]',
            '.ff-previous',
            '.value-previous',
            '.prior',
            '.last',
            
            # Positional selectors (previous usually sixth column)
            'td:nth-child(6)',
            
            # Generic fallbacks
            '.col-previous',
            '.previous-cell'
        ]
        previous = self._get_text_with_fallback(row, previous_selectors)
        
        # Enhanced positional extraction fallback
        if all(val == "N/A" for val in [time, currency, event]):
            logger.debug("Primary selectors failed, trying positional extraction")
            cells = row.find_all(['td', 'th'])
            
            if len(cells) >= 3:  # Minimum required columns
                # Try to identify columns by content patterns
                for i, cell in enumerate(cells):
                    cell_text = cell.get_text().strip()
                    
                    # Time pattern detection (HH:MM format)
                    if time == "N/A" and self._is_time_format(cell_text):
                        time = cell_text
                        logger.debug(f"Found time in column {i+1}: {time}")
                    
                    # Currency pattern detection (3-letter codes)
                    elif currency == "N/A" and self._is_currency_format(cell_text):
                        currency = cell_text
                        logger.debug(f"Found currency in column {i+1}: {currency}")
                    
                    # Event pattern detection (longer text with economic terms)
                    elif event == "N/A" and self._is_event_format(cell_text):
                        event = cell_text
                        logger.debug(f"Found event in column {i+1}: {event}")
                    
                    # Numeric value detection for actual/forecast/previous
                    elif self._is_numeric_value(cell_text):
                        if actual == "N/A":
                            actual = cell_text
                            logger.debug(f"Found actual in column {i+1}: {actual}")
                        elif forecast == "N/A":
                            forecast = cell_text
                            logger.debug(f"Found forecast in column {i+1}: {forecast}")
                        elif previous == "N/A":
                            previous = cell_text
                            logger.debug(f"Found previous in column {i+1}: {previous}")
                
                # Final fallback: use positional extraction
                if time == "N/A" and len(cells) > 0:
                    time = cells[0].get_text().strip() or "N/A"
                if currency == "N/A" and len(cells) > 1:
                    currency = cells[1].get_text().strip() or "N/A"
                if event == "N/A" and len(cells) > 2:
                    event = cells[2].get_text().strip() or "N/A"
                if actual == "N/A" and len(cells) > 3:
                    actual = cells[3].get_text().strip() or "N/A"
                if forecast == "N/A" and len(cells) > 4:
                    forecast = cells[4].get_text().strip() or "N/A"
                if previous == "N/A" and len(cells) > 5:
                    previous = cells[5].get_text().strip() or "N/A"
        
        # Clean and validate extracted data
        time = self._clean_text(time)
        currency = self._clean_text(currency)
        event = self._clean_text(event)
        actual = self._clean_text(actual)
        forecast = self._clean_text(forecast)
        previous = self._clean_text(previous)
        
        return {
            "time": escape_markdown_v2(time),
            "currency": escape_markdown_v2(currency),
            "event": escape_markdown_v2(event),
            "actual": escape_markdown_v2(actual),
            "forecast": escape_markdown_v2(forecast),
            "previous": escape_markdown_v2(previous),
        }
    
    def _is_time_format(self, text: str) -> bool:
        """Check if text matches time format patterns."""
        import re
        time_patterns = [
            r'^\d{1,2}:\d{2}$',  # HH:MM
            r'^\d{1,2}:\d{2}[ap]m$',  # HH:MMam/pm
            r'^All Day$',  # All Day events
            r'^\d{1,2}:\d{2} [AP]M$'  # HH:MM AM/PM
        ]
        return any(re.match(pattern, text, re.IGNORECASE) for pattern in time_patterns)
    
    def _is_currency_format(self, text: str) -> bool:
        """Check if text matches currency format patterns."""
        currencies = ['USD', 'EUR', 'GBP', 'JPY', 'AUD', 'CAD', 'CHF', 'NZD', 'CNY', 'SEK', 'NOK', 'DKK']
        return text.upper() in currencies
    
    def _is_event_format(self, text: str) -> bool:
        """Check if text looks like an economic event."""
        if len(text) < 5:  # Too short to be an event
            return False
        
        event_keywords = [
            'rate', 'gdp', 'inflation', 'employment', 'cpi', 'pmi', 'retail', 
            'manufacturing', 'services', 'trade', 'balance', 'index', 'report',
            'data', 'sales', 'production', 'confidence', 'survey', 'announcement'
        ]
        
        text_lower = text.lower()
        return any(keyword in text_lower for keyword in event_keywords)
    
    def _is_numeric_value(self, text: str) -> bool:
        """Check if text contains numeric values typical of forex data."""
        import re
        # Match patterns like: 1.5%, -0.2, 125.5K, 2.3M, etc.
        numeric_patterns = [
            r'^-?\d+\.?\d*%?$',  # Simple numbers with optional % and decimal
            r'^-?\d+\.?\d*[KMB]$',  # Numbers with K/M/B suffixes
            r'^-?\d+\.?\d*[kmb]$',  # Numbers with lowercase suffixes
            r'^\d+\.?\d*$',  # Simple positive numbers
        ]
        return any(re.match(pattern, text.strip()) for pattern in numeric_patterns)
    
    def _clean_text(self, text: str) -> str:
        """Clean and normalize extracted text."""
        if not text or text == "N/A":
            return "N/A"
        
        # Remove extra whitespace and newlines
        text = ' '.join(text.split())
        
        # Remove common artifacts
        text = text.replace('\n', ' ').replace('\t', ' ')
        
        # If text is empty after cleaning, return N/A
        if not text.strip():
            return "N/A"
        
        return text.strip()

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
