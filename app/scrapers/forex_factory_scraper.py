
"""
Forex Factory scraper implementation.
"""

import time
import random
from datetime import datetime, timedelta, date
from typing import List, Dict, Optional
from playwright.sync_api import sync_playwright, TimeoutError as PlaywrightTimeoutError
from bs4 import BeautifulSoup

from .base import BaseScraper
from app.config import config
from app.services.analysis_service import AnalysisService
import logging

logger = logging.getLogger(__name__)

class ForexFactoryScraper(BaseScraper):
    """Scraper for ForexFactory.com news events."""
    
    def __init__(self):
        super().__init__()
        self.analysis_service = AnalysisService()
        self.base_url = "https://www.forexfactory.com/calendar"
    
    def scrape_date_range(self, start_date: date, end_date: date) -> List[Dict]:
        """
        Scrape Forex news from ForexFactory for the given date range.
        
        Args:
            start_date: Start date for scraping
            end_date: End date for scraping
            
        Returns:
            List of scraped event dictionaries
        """
        logger.info(f"Scraping Forex news for range: {start_date} to {end_date}")
        scraped_events = []
        
        with sync_playwright() as p:
            browser = p.chromium.launch(
                headless=True,
                args=[
                    "--disable-blink-features=AutomationControlled",
                    "--no-sandbox",
                    "--disable-dev-shm-usage",
                    "--disable-gpu",
                ]
            )
            
            try:
                current = start_date
                while current <= end_date:
                    events = self._scrape_single_date_with_browser(browser, current)
                    scraped_events.extend(events)
                    current += timedelta(days=1)
                    
                    # Add delay between dates to avoid being blocked
                    time.sleep(random.uniform(2, 4))
                    
            except Exception as e:
                logger.error(f"Scraping failed overall: {e}")
            finally:
                browser.close()
                logger.info("Browser closed.")
        
        return scraped_events
    
    def scrape_single_date(self, target_date: date) -> List[Dict]:
        """
        Scrape data for a single date.
        
        Args:
            target_date: Date to scrape
            
        Returns:
            List of scraped event dictionaries
        """
        with sync_playwright() as p:
            browser = p.chromium.launch(
                headless=True,
                args=[
                    "--disable-blink-features=AutomationControlled",
                    "--no-sandbox",
                    "--disable-dev-shm-usage",
                    "--disable-gpu",
                ]
            )
            
            try:
                return self._scrape_single_date_with_browser(browser, target_date)
            finally:
                browser.close()
    
    def _scrape_single_date_with_browser(self, browser, target_date: date) -> List[Dict]:
        """Scrape a single date using an existing browser instance."""
        date_str = target_date.strftime("%Y-%m-%d")
        logger.info(f"Scraping data for date: {date_str}")
        
        context = browser.new_context(
            user_agent=random.choice(config.USER_AGENTS),
            viewport={"width": 1280, "height": 720},
            java_script_enabled=True,
            bypass_csp=True,
        )
        
        context.set_extra_http_headers({
            "Accept-Language": "en-US,en;q=0.9",
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
            "Connection": "keep-alive",
            "Upgrade-Insecure-Requests": "1",
        })
        
        page = context.new_page()
        events = []
        
        try:
            # Format URL for ForexFactory
            url = f"{self.base_url}?day={target_date.strftime('%b')}{target_date.day}.{target_date.year}"
            logger.debug(f"Navigating to URL: {url}")
            
            # Navigate to page
            try:
                page.goto(url, timeout=60000)
                page.wait_for_load_state("networkidle", timeout=60000)
            except PlaywrightTimeoutError as e:
                logger.warning(f"Networkidle failed on {date_str}: {e}. Falling back to domcontentloaded.")
                try:
                    page.wait_for_load_state("domcontentloaded", timeout=60000)
                except PlaywrightTimeoutError as e:
                    logger.error(f"Failed loading {date_str}: {e}. Skipping.")
                    return events
            
            # Wait and check for blocking
            time.sleep(random.uniform(3, 5))
            html = page.content()
            
            if "Just a moment..." in html or "Checking your browser" in html:
                logger.error(f"Blocked by CAPTCHA/Cloudflare on {date_str}. Skipping.")
                return events
            
            # Parse the page
            events = self._parse_calendar_page(html, target_date, url)
            
        except Exception as e:
            logger.error(f"Error scraping {date_str}: {e}")
        finally:
            page.close()
        
        return events
    
    def _parse_calendar_page(self, html: str, target_date: date, source_url: str) -> List[Dict]:
        """Parse the calendar page HTML and extract events."""
        soup = BeautifulSoup(html, "html.parser")
        table = soup.find("table", class_="calendar__table")
        
        if not table:
            logger.error(f"No calendar table found for {target_date}. Skipping.")
            return []
        
        rows = table.find_all("tr", class_=lambda c: c and "calendar__row" in c)
        rows = [r for r in rows if r.get("data-event-id")]
        
        logger.info(f"Found {len(rows)} events for {target_date}")
        
        events = []
        last_time = None  # Track the last seen time for events with missing times
        
        for row in rows:
            try:
                event_data = self._parse_event_row(row, target_date, source_url, last_time)
                if event_data:
                    events.append(event_data)
                    # Update last_time if this event had a time
                    if event_data.get('time'):
                        last_time = event_data['time']
            except Exception as e:
                logger.error(f"Error parsing event row: {e}")
                continue
        
        return events
    
    def _parse_event_row(self, row, target_date: date, source_url: str, last_time: Optional[str]) -> Optional[Dict]:
        """Parse a single event row from the calendar table."""
        # Extract time
        time_cell = row.find("td", class_=lambda c: c and ("calendar__time" in c or "--time" in c))
        raw_time = time_cell.text.strip() if time_cell else ""
        
        # Handle invalid time (e.g., "All Day", "Tentative")
        if raw_time.lower() in ["all day", "tentative", ""]:
            if last_time:
                event_time = last_time
                logger.debug(f"Using last seen time {event_time} for event with missing/invalid time")
            else:
                logger.debug(f"Skipping event due to invalid time: {raw_time}")
                return None
        else:
            try:
                event_time = datetime.strptime(raw_time, "%I:%M%p").strftime("%H:%M")
                logger.debug(f"Parsed time: {event_time}")
            except ValueError:
                logger.debug(f"Failed to parse time {raw_time}, skipping event")
                return None
        
        # Extract currency
        currency_td = row.find("td", class_=lambda c: c and "calendar__currency" in c)
        currency = currency_td.text.strip() if currency_td else ""
        if not currency:
            logger.debug("Skipping event due to missing currency")
            return None
        
        # Extract event name
        event_td = row.find("td", class_=lambda c: c and "calendar__event" in c)
        event_name = event_td.text.strip() if event_td else ""
        if not event_name:
            logger.debug("Skipping event due to missing event name")
            return None
        
        # Extract forecast, previous, actual values
        forecast = self._extract_cell_text(row, "calendar__forecast")
        previous = self._extract_cell_text(row, "calendar__previous")
        actual = self._extract_cell_text(row, "calendar__actual")
        
        # Extract impact level
        impact = self._extract_impact_level(row)
        
        # Generate analysis
        analysis = self.analysis_service.analyze_single_event(
            currency=currency,
            event_name=event_name,
            forecast=forecast,
            previous=previous,
            actual=actual
        )
        
        return {
            'date': target_date.strftime('%Y-%m-%d'),
            'time': event_time,
            'currency': currency,
            'event_name': event_name,
            'forecast': forecast,
            'previous_value': previous,
            'actual_value': actual,
            'impact_level': impact,
            'analysis': analysis,
            'source_url': source_url
        }
    
    def _extract_cell_text(self, row, class_name: str) -> str:
        """Extract text from a table cell with the given class name."""
        cell = row.find("td", class_=lambda c: c and class_name in c)
        text = cell.text.strip() if cell else "N/A"
        return text if text and text != "" else "N/A"
    
    def _extract_impact_level(self, row) -> str:
        """Extract impact level from the row."""
        impact = "LOW"  # Default to LOW instead of N/A
        impact_td = row.find("td", class_=lambda c: c and "calendar__impact" in c)
        
        if impact_td:
            span = impact_td.find("span", class_=lambda cl: cl and cl.startswith("icon--ff-impact-"))
            if span:
                cls = next((cl for cl in span["class"] if cl.startswith("icon--ff-impact-")), "")
                code = cls.rsplit("-", 1)[-1] if cls else ""
                impact = config.IMPACT_MAP.get(code, "LOW")
        
        return impact
