import asyncio
import logging
from datetime import datetime
from typing import Optional, List, Dict, Any

from bs4 import BeautifulSoup
from pytz import timezone
from .config import Config
from .utils import escape_markdown_v2, send_long_message
import re

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
        if not self.api_key:
            logger.warning("ChatGPT API key not configured. Analysis will be skipped.")

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
            f"Analyze the following Forex news and predict its potential market :\n"
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
    # Centralized impact class mapping (support both '=' and '-')
    IMPACT_CLASS_MAP = {
        'icon--ff-impact=red': 'high',    # Red (equals)
        'icon--ff-impact=ora': 'medium', # Orange (equals)
        'icon--ff-impact=yel': 'low',    # Yellow (equals)
        'icon--ff-impact-red': 'high',   # Red (dash, fallback)
        'icon--ff-impact-ora': 'medium', # Orange (dash, fallback)
        'icon--ff-impact-yel': 'low',    # Yellow (dash, fallback)
    }

    def __init__(self, config: Config, analyzer: ChatGPTAnalyzer):
        self.config = config
        self.analyzer = analyzer
        self.base_url = "https://www.forexfactory.com/calendar"

    async def scrape_news(self, target_date: Optional[datetime] = None, analysis_required: bool = True, debug: bool = False) -> List[Dict[str, Any]]:
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

        news_items = self._parse_news_from_html(html)
        if analysis_required:
            # Group by (currency, time)
            grouped = {}
            for item in news_items:
                key = (item['currency'], item['time'])
                grouped.setdefault(key, []).append(item)
            for group_items in grouped.values():
                if len(group_items) > 1:
                    # Group event: create a single group analysis
                    group_prompt = {
                        'time': group_items[0]['time'],
                        'currency': group_items[0]['currency'],
                        'event': ", ".join([i['event'] for i in group_items]),
                        'actual': ", ".join([i['actual'] for i in group_items]),
                        'forecast': ", ".join([i['forecast'] for i in group_items]),
                        'previous': ", ".join([i['previous'] for i in group_items]),
                    }
                    group_analysis = self.analyzer.analyze_news(group_prompt)
                    for i in group_items:
                        i['analysis'] = group_analysis
                        i['group_analysis'] = True
                else:
                    group_items[0]['analysis'] = self.analyzer.analyze_news(group_items[0])
                    group_items[0]['group_analysis'] = False
        else:
            for item in news_items:
                item['analysis'] = None
                item['group_analysis'] = False
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

    def _parse_news_from_html(self, html: str) -> List[Dict[str, str]]:
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
        logger.debug(f"DEBUG: Found {len(rows)} rows to process for impact extraction.")
        if not rows:
            logger.warning("No news rows found with any selector. Saving HTML to /tmp/forex_debug.html for inspection.")
            try:
                with open("/tmp/forex_debug.html", "w", encoding="utf-8") as f:
                    f.write(html)
            except Exception as e:
                logger.warning(f"Failed to save debug HTML: {e}")
        # First pass: collect all news items and track times
        news_items: List[Dict[str, str]] = []
        current_time = "N/A"
        all_classes = []
        for row in rows:
            logger.debug(f"EXTRACTING NEWS DATA for row: {str(row)}")
            # Collect all impact classes for debugging
            impact_element = (
                row.select_one('.calendar__impact span.icon')
                or row.select_one('.impact span.icon')
            )
            if impact_element:
                classes = impact_element.get('class', [])
                all_classes.append(classes)
            news_item = self._extract_news_data(row)
            if news_item["time"] != "N/A" and news_item["time"].strip():
                current_time = news_item["time"]
            elif current_time != "N/A":
                news_item["time"] = current_time
            news_items.append(news_item)
        if not news_items:
            logger.warning(f"No news items collected. Impact classes found: {all_classes}")
        # Second pass: ensure all items have times and sort properly
        news_items = self._ensure_all_times_and_sort(news_items)
        return news_items

    def _ensure_all_times_and_sort(self, news_items: List[Dict[str, str]]) -> List[Dict[str, str]]:
        """Ensure all news items have proper times and sort by currency and time."""
        if not news_items:
            return news_items

        # Find the first valid time if any items are missing times
        first_valid_time = None
        for item in news_items:
            if item["time"] != "N/A" and item["time"].strip():
                first_valid_time = item["time"]
                break

        # If no valid time found, use a default
        if not first_valid_time:
            first_valid_time = "09:00"

        # Ensure all items have a time
        for item in news_items:
            if item["time"] == "N/A" or not item["time"].strip():
                item["time"] = first_valid_time

        # Sort by currency first, then by time
        def sort_key(item):
            currency = item['currency']
            time_str = item['time']

            # Convert time to sortable format
            try:
                # Handle various time formats
                if ":" in time_str:
                    if "am" in time_str.lower() or "pm" in time_str.lower():
                        # Handle 12-hour format
                        time_obj = datetime.strptime(time_str.lower().replace("am", " AM").replace("pm", " PM"), "%I:%M %p")
                    else:
                        # Handle 24-hour format
                        time_obj = datetime.strptime(time_str, "%H:%M")
                    time_minutes = time_obj.hour * 60 + time_obj.minute
                else:
                    # For non-standard time formats, use a default value
                    time_minutes = 0
            except:
                # If time parsing fails, use a default value
                time_minutes = 0

            return (currency, time_minutes)

        # Sort the items
        news_items.sort(key=sort_key)

        return news_items

    def _is_blocked_content(self, html: str) -> bool:
        """Check if the HTML content indicates blocked/bot detection."""
        if not html:
            return True

        html_lower = html.lower()

        # Check for common blocking indicators
        blocked_indicators = [
            "cloudflare",
            "just a moment",
            "access denied",
            "forbidden",
            "rate limit exceeded",
            "suspicious activity detected",
            "bot detection",
            "captcha",
            "challenge",
            "verifying you are human"
        ]

        for indicator in blocked_indicators:
            if indicator in html_lower:
                return True

        # Check if content is too short (likely blocked)
        if len(html.strip()) < 1000:
            return True

        return False

    def _should_include_news(self, row, impact_level: str) -> bool:
        # Deprecated: No longer used for filtering during scraping
        return True

    def _extract_news_data(self, row) -> Dict[str, str]:
        logger.debug(f"EXTRACTING NEWS DATA for row: {str(row)}")
        time_elem = row.select_one('.calendar__time')
        time = time_elem.text.strip() if time_elem else "N/A"
        # Robust time to 24h
        time_24 = time
        try:
            if time and time != "N/A":
                t = time.strip().lower().replace(' ', '')
                # Regex for e.g. 3:30am, 12:05pm, 09:00
                m = re.match(r'^(\d{1,2}):(\d{2})(am|pm)?$', t)
                if m:
                    hour, minute, ampm = m.group(1), m.group(2), m.group(3)
                    hour = int(hour)
                    if ampm == 'pm' and hour != 12:
                        hour += 12
                    if ampm == 'am' and hour == 12:
                        hour = 0
                    time_24 = f"{hour:02d}:{minute}"
                else:
                    # Try 24h format fallback
                    time_24 = datetime.strptime(t, "%H:%M").strftime("%H:%M")
        except Exception as e:
            logger.debug(f"Time parse failed for '{time}': {e}")
            time_24 = time  # fallback
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
        # Impact detection (robust)
        impact = "unknown"
        impact_element = (
            row.select_one('.calendar__impact span.icon')
            or row.select_one('.impact span.icon')
        )
        logger.debug(f"DEBUG: impact_element={impact_element}, row={str(row)}")
        if impact_element:
            classes = impact_element.get('class', [])
            if isinstance(classes, str):
                classes = classes.split()
            # Normalize to lowercase for robustness
            classes = [c.lower() for c in classes]
            logger.debug(f"DEBUG: classes={classes}, mapping_keys={list(self.IMPACT_CLASS_MAP.keys())}")
            for class_name, level in self.IMPACT_CLASS_MAP.items():
                # Accept both '-' and '=' in the class name for robustness
                if class_name in classes:
                    logger.debug(f"IMPACT MATCH: {class_name} -> {level}")
                    impact = level
                    break
            if impact == "unknown":
                # Try to match by replacing '-' with '=' and vice versa
                for c in classes:
                    c_eq = c.replace('-', '=')
                    c_dash = c.replace('=', '-')
                    if c_eq in self.IMPACT_CLASS_MAP:
                        logger.debug(f"IMPACT ALT MATCH: {c} as {c_eq} -> {self.IMPACT_CLASS_MAP[c_eq]}")
                        impact = self.IMPACT_CLASS_MAP[c_eq]
                        break
                    if c_dash in self.IMPACT_CLASS_MAP:
                        logger.debug(f"IMPACT ALT MATCH: {c} as {c_dash} -> {self.IMPACT_CLASS_MAP[c_dash]}")
                        impact = self.IMPACT_CLASS_MAP[c_dash]
                        break
            # If only 'icon' or empty, treat as tentative/no-impact
            if impact == "unknown":
                if (len(classes) == 1 and classes[0] == 'icon') or not classes:
                    if time_24.lower() in ['tentative', 'all day'] or time.lower() in ['tentative', 'all day']:
                        impact = "tentative"
                    else:
                        impact = "none"
        else:
            # No impact element at all
            if time_24.lower() in ['tentative', 'all day'] or time.lower() in ['tentative', 'all day']:
                impact = "tentative"
            else:
                impact = "none"
        if impact == "unknown":
            logger.warning(f"Impact unknown for row: {str(row)}")
        return {
            "time": escape_markdown_v2(time_24),
            "currency": escape_markdown_v2(currency),
            "event": escape_markdown_v2(event),
            "actual": escape_markdown_v2(actual),
            "forecast": escape_markdown_v2(forecast),
            "previous": escape_markdown_v2(previous),
            "impact": impact,
        }


class MessageFormatter:
    """Handles formatting of news messages for Telegram with grouping."""

    @staticmethod
    def format_news_message(news_items: List[Dict[str, Any]], target_date: datetime, impact_level: str, analysis_required: bool = True, currencies: Optional[List[str]] = None) -> str:
        date_str = target_date.strftime("%d.%m.%Y")

        # Filter by currencies if specified
        if currencies:
            filtered_items = [item for item in news_items if item.get('currency') in currencies]
            currency_filter_text = f" (Filtered: {', '.join(currencies)})"
        else:
            filtered_items = news_items
            currency_filter_text = ""

        header = f"🗓️ Forex News for {date_str} (CET){currency_filter_text}:\n\n"

        if not filtered_items:
            currency_msg = f" with currencies: {', '.join(currencies)}" if currencies else ""
            return (
                header
                + f"✅ No news found for {date_str} with impact: {impact_level}{currency_msg}\n"
                + "Please check the website for updates."
            )

        # Group by currency and time for group event detection
        grouped = {}
        for item in filtered_items:
            key = (item['currency'], item['time'])
            grouped.setdefault(key, []).append(item)

        message_parts = [header]
        last_currency = None
        for (currency, time), items in sorted(grouped.items()):
            if currency != last_currency:
                if last_currency is not None:
                    message_parts.append("\n" + "="*50 + "\n\n")
                # Currency name with catchy formatting
                message_parts.append(f'💎 <b>{currency}</b> 💎\n')
                last_currency = currency
            # Group event highlight
            if len(items) > 1:
                message_parts.append(f"<b>🚨 GROUP EVENT at {time} ({len(items)} events)</b>\n")
                if analysis_required and items[0].get('analysis'):
                    message_parts.append(f"🔍 <b>Group Analysis:</b> {items[0]['analysis']}\n")
            for idx, item in enumerate(items):
                impact_emoji = {
                    'high': '🔴',
                    'medium': '🟠',
                    'low': '🟡',
                    'tentative': '⏳',
                    'none': '⚪️',
                    'unknown': '❓',
                }.get(item.get('impact', 'unknown'), '❓')
                # Remove unnecessary backslashes in Actual, Forecast and Previous
                actual = str(item['actual']).replace('\\', '') if item['actual'] else 'N/A'
                forecast = str(item['forecast']).replace('\\', '') if item['forecast'] else 'N/A'
                previous = str(item['previous']).replace('\\', '') if item['previous'] else 'N/A'
                part = (
                    f"⏰ <b>{item['time']}</b> {impact_emoji} <b>Impact:</b> {item.get('impact', 'unknown').capitalize()}\n"
                    f"📰 <b>Event:</b> {item['event']}\n"
                    f"📊 <b>Actual:</b> {actual}\n"
                    f"📈 <b>Forecast:</b> {forecast}\n"
                    f"📉 <b>Previous:</b> {previous}\n"
                )
                if analysis_required and not item.get('group_analysis', False) and item.get('analysis'):
                    part += f"🔍 <b>Analysis:</b> {item['analysis']}\n"
                # Add separator between events in group, but not after the last one
                if len(items) > 1 and idx < len(items) - 1:
                    part += "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
                # Only add main separator if not a group event or not the last in group
                if len(items) == 1 or idx == len(items) - 1:
                    part += "------------------------------\n"
                message_parts.append(part)
        return "".join(message_parts)




async def process_forex_news(scraper: ForexNewsScraper, bot, config: Config, target_date: Optional[datetime] = None, impact_level: str = "high", debug: bool = False) -> Optional[List[Dict[str, Any]]]:
    if not bot or not config.telegram_chat_id:
        logger.error("Cannot process news: Bot or CHAT_ID not configured")
        return [] if debug else None
    try:
        if target_date is None:
            target_date = datetime.now(timezone(config.timezone))
        news_items = await scraper.scrape_news(target_date, debug)
        if debug:
            return news_items
        message = MessageFormatter.format_news_message(news_items, target_date, impact_level)
        if message.strip():
            send_long_message(bot, config.telegram_chat_id, message, parse_mode="HTML")
        else:
            logger.error("Generated message is empty")
        return news_items
    except Exception as e:
        logger.exception("Unexpected error in process_forex_news: %s", e)
        try:
            error_msg = f"⚠️ Error in Forex news scraping: {str(e)}"
            bot.send_message(config.telegram_chat_id, error_msg)
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
