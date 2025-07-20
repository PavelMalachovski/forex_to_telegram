import asyncio
import logging
from datetime import datetime
from typing import Optional, List, Dict, Any
from collections import defaultdict
from bs4 import BeautifulSoup
from pytz import timezone
from .config import Config
from .utils import escape_markdown_v2, send_long_message

logger = logging.getLogger(__name__)

# New: undetected-chromedriver
import undetected_chromedriver as uc
from selenium.webdriver.common.by import By
from selenium.webdriver.common.action_chains import ActionChains
from selenium.webdriver.common.keys import Keys
import random
import time
import os

class CloudflareBypassError(Exception):
    """Custom exception for Cloudflare challenge detection."""
    pass

class ChatGPTAnalyzer:
    """Handles ChatGPT API integration for news analysis."""

    def __init__(self, api_key: Optional[str]):
        self.api_key = api_key
        self.api_url = "https://api.openai.com/v1/chat/completions"

    def analyze_news(self, news_item: Dict[str, str]) -> str:
        if not self.api_key:
            return "⚠️ ChatGPT analysis skipped: API key not configured."

        try:
            import requests
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

class ForexNewsScraper:
    """Handles scraping of forex news from ForexFactory using undetected-chromedriver."""
    def __init__(self, config: Config, analyzer: ChatGPTAnalyzer):
        self.config = config
        self.analyzer = analyzer
        self.base_url = "https://www.forexfactory.com/calendar"
        self.last_seen_time = "N/A"

    async def scrape_news(self, target_date: Optional[datetime] = None, impact_level: str = "high", debug: bool = False) -> List[Dict[str, Any]]:
        if target_date is None:
            target_date = datetime.now(timezone(self.config.timezone))
        url = self._build_url(target_date)
        logger.info(f"Fetching URL: {url}")

        # Try the new Selenium approach with Cloudflare challenge handling
        try:
            html = await self._scrape_with_selenium(url)
            logger.info("Successfully scraped with Selenium")
        except Exception as e:
            logger.error(f"Selenium scraping failed: {e}")
            # Fallback to the old method if Selenium fails
            try:
                logger.info("Trying fallback method...")
                html = await asyncio.to_thread(self._fetch_with_undetected_chromedriver, url)
                logger.info("Successfully scraped with fallback method")
            except Exception as fallback_e:
                logger.error(f"Fallback method also failed: {fallback_e}")
                raise CloudflareBypassError(f"All scraping methods failed: {e}, fallback: {fallback_e}")

        news_items = self._parse_news_from_html(html, impact_level)
        for item in news_items:
            item["analysis"] = self.analyzer.analyze_news(item)
        logger.info("Collected %s news items", len(news_items))
        return news_items

    def _build_url(self, target_date: datetime) -> str:
        date_str = target_date.strftime("%b%d.%Y").lower()
        return f"{self.base_url}?day={date_str}"

    async def _scrape_with_selenium(self, url: str) -> str:
        """Scrape using undetected-chromedriver with human-like behavior."""
        try:
            # Find Chrome binary
            chrome_paths = [
                "/usr/bin/google-chrome-stable",
                "/usr/bin/google-chrome",
                "/usr/bin/chromium-browser",
                "/usr/bin/chromium",
            ]
            chrome_binary = None
            for path in chrome_paths:
                if os.path.exists(path):
                    chrome_binary = path
                    break

            if not chrome_binary:
                raise CloudflareBypassError("Chrome binary not found")

            logger.info(f"Using Chrome binary: {chrome_binary}")

            options = uc.ChromeOptions()
            options.binary_location = chrome_binary
            options.add_argument("--no-sandbox")
            options.add_argument("--disable-dev-shm-usage")
            options.add_argument("--disable-gpu")
            options.add_argument("--disable-web-security")
            options.add_argument("--disable-features=VizDisplayCompositor")
            options.add_argument("--disable-extensions")
            options.add_argument("--disable-plugins")
            # Don't disable images and JavaScript for Cloudflare challenge
            # options.add_argument("--disable-images")
            # options.add_argument("--disable-javascript")
            options.add_argument("--disable-default-apps")
            options.add_argument("--disable-sync")
            options.add_argument("--disable-translate")
            options.add_argument("--disable-background-timer-throttling")
            options.add_argument("--disable-backgrounding-occluded-windows")
            options.add_argument("--disable-renderer-backgrounding")
            options.add_argument("--disable-field-trial-config")
            options.add_argument("--disable-ipc-flooding-protection")
            options.add_argument("--no-first-run")
            options.add_argument("--no-default-browser-check")
            options.add_argument("--disable-blink-features=AutomationControlled")
            # Add headless mode
            options.add_argument("--headless")
            # Add user agent
            options.add_argument("--user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36")
            # Remove problematic experimental options
            # options.add_experimental_option("excludeSwitches", ["enable-automation"])
            # options.add_experimental_option("useAutomationExtension", False)

            driver = uc.Chrome(options=options)
            driver.execute_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")

            try:
                logger.info(f"Navigating to {url}")
                driver.get(url)

                # Wait for page to load and check for Cloudflare challenge
                max_wait = 30
                wait_time = 0
                while wait_time < max_wait:
                    page_source = driver.page_source

                    # Check if we're still on Cloudflare challenge page
                    if "just a moment" in page_source.lower() or "verifying you are human" in page_source.lower():
                        logger.info("Cloudflare challenge detected, waiting...")
                        await asyncio.sleep(2)
                        wait_time += 2
                        continue

                    # Check if we have actual content
                    if "calendar" in page_source.lower() and ("forexfactory" in page_source.lower() or "forex factory" in page_source.lower()):
                        logger.info("Page loaded successfully")
                        break

                    logger.info("Waiting for page to load...")
                    await asyncio.sleep(1)
                    wait_time += 1

                if wait_time >= max_wait:
                    logger.warning("Timeout waiting for page to load")

                # Add human-like behavior
                self._add_human_behavior(driver)

                # Get final page source
                page_source = driver.page_source

                # Final check for Cloudflare challenge
                if "just a moment" in page_source.lower() or "verifying you are human" in page_source.lower():
                    logger.warning("Still on Cloudflare challenge page after waiting")
                    return page_source

                logger.info("Scraping completed successfully")
                return page_source

            finally:
                driver.quit()

        except Exception as e:
            logger.error(f"Selenium scraping failed: {e}")
            raise CloudflareBypassError(f"Selenium error: {e}")

    def _add_human_behavior(self, driver):
        """Add human-like behavior to avoid detection."""
        try:
            # Random mouse movements
            for _ in range(random.randint(2, 5)):
                x = random.randint(100, 800)
                y = random.randint(100, 600)
                action = ActionChains(driver)
                action.move_by_offset(x, y).perform()
                time.sleep(random.uniform(0.1, 0.3))

            # Scroll down and up
            driver.execute_script("window.scrollTo(0, document.body.scrollHeight/2);")
            time.sleep(random.uniform(0.5, 1.0))
            driver.execute_script("window.scrollTo(0, 0);")
            time.sleep(random.uniform(0.3, 0.7))

            # Random key presses
            body = driver.find_element(By.TAG_NAME, "body")
            for _ in range(random.randint(1, 3)):
                body.send_keys(Keys.PAGE_DOWN)
                time.sleep(random.uniform(0.2, 0.5))
                body.send_keys(Keys.PAGE_UP)
                time.sleep(random.uniform(0.2, 0.5))

        except Exception as e:
            logger.warning(f"Human behavior simulation failed: {e}")

    def _fetch_with_undetected_chromedriver(self, url: str) -> str:
        import os
        options = uc.ChromeOptions()
        options.add_argument("--no-sandbox")
        options.add_argument("--disable-blink-features=AutomationControlled")
        options.add_argument("--disable-dev-shm-usage")
        options.add_argument("--disable-gpu")
        options.add_argument("--disable-infobars")
        options.add_argument("--disable-extensions")
        options.add_argument("--start-maximized")
        options.add_argument("--headless=new")  # Always headless in Docker/cloud
        options.add_argument("--disable-software-rasterizer")
        options.add_argument("--disable-setuid-sandbox")
        options.add_argument("--remote-debugging-port=9222")
        # Set Google Chrome Stable binary location for Docker/Render.com
        chrome_path = os.environ.get("CHROME_BINARY", "/usr/bin/google-chrome")
        options.binary_location = chrome_path
        logger.info(f"Launching Google Chrome with binary: {options.binary_location}")
        logger.info(f"ChromeOptions: {options.arguments}")
        logger.info("use_subprocess set to False for compatibility")
        driver = uc.Chrome(options=options, use_subprocess=False)
        try:
            driver.get(url)
            actions = ActionChains(driver)
            # Human-like actions: mouse movement, scrolling, key presses, random waits
            for _ in range(random.randint(3, 7)):
                # Move mouse to random positions
                x = random.randint(100, 1200)
                y = random.randint(100, 700)
                actions.move_by_offset(x, y).perform()
                time.sleep(random.uniform(0.2, 0.7))
                actions.move_by_offset(-x, -y).perform()
                time.sleep(random.uniform(0.2, 0.7))
                # Scroll randomly
                scroll_amount = random.randint(100, 800)
                driver.execute_script(f"window.scrollBy(0, {scroll_amount});")
                time.sleep(random.uniform(0.2, 0.7))
                driver.execute_script(f"window.scrollBy(0, {-scroll_amount});")
                time.sleep(random.uniform(0.2, 0.7))
                # Random key press
                if random.random() < 0.5:
                    actions.send_keys(random.choice([Keys.ARROW_DOWN, Keys.ARROW_UP, Keys.PAGE_DOWN, Keys.PAGE_UP])).perform()
                    time.sleep(random.uniform(0.2, 0.7))
            # Click somewhere on the page
            body = driver.find_element(By.TAG_NAME, "body")
            actions.move_to_element(body).click().perform()
            time.sleep(random.uniform(0.5, 1.5))
            # Wait for the calendar table
            for _ in range(60):  # up to 60 seconds
                try:
                    table = driver.find_element(By.CSS_SELECTOR, 'table.calendar__table')
                    if table.is_displayed():
                        break
                except Exception:
                    pass
                time.sleep(1)
            html = driver.page_source
            return html
        finally:
            driver.quit()

    def _parse_news_from_html(self, html: str, impact_level: str) -> List[Dict[str, str]]:
        soup = BeautifulSoup(html, 'html.parser')
        # Cloudflare/fallback detection
        if "cloudflare" in html.lower() or "just a moment" in html.lower() or "attention required" in html.lower():
            logger.warning("Cloudflare or fallback content detected in page source!")
        # Try multiple selectors for event rows
        selectors = [
            'table.calendar__table tr.calendar__row[data-event-id]',
            'table.calendar__table tr.calendar__row',
            'tr.calendar__row[data-event-id]',
            'tr.calendar__row',
            'table.calendar tr.event',
            'tr.event',
        ]
        rows = []
        for selector in selectors:
            rows = soup.select(selector)
            if rows:
                logger.info(f"Found {len(rows)} rows with selector: {selector}")
                break
        if not rows:
            logger.warning("No news rows found with any selector. Saving HTML to /tmp/forex_debug.html for inspection.")
            try:
                with open("/tmp/forex_debug.html", "w", encoding="utf-8") as f:
                    f.write(html)
            except Exception as e:
                logger.warning(f"Failed to save debug HTML: {e}")
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
        actual_elem = row.select_one('.calendar__actual')
        actual = "N/A"
        if actual_elem:
            actual_text = actual_elem.text.strip()
            if actual_text and actual_text != "":
                actual = actual_text
        currency_elem = row.select_one('.calendar__currency')
        currency = currency_elem.text.strip() if currency_elem else "N/A"
        event_elem = row.select_one('.calendar__event-title')
        event = event_elem.text.strip() if event_elem else "N/A"
        forecast_elem = row.select_one('.calendar__forecast')
        forecast = forecast_elem.text.strip() if forecast_elem else "N/A"
        previous_elem = row.select_one('.calendar__previous')
        previous = previous_elem.text.strip() if previous_elem else "N/A"
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
        header = f"🗓️ Forex News for {date_escaped} \\(CET\\):\n\n"

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
