
"""Forex Factory scraper for economic calendar events."""

import re
import time
import random
from datetime import datetime, date, timedelta
from typing import List, Dict, Any, Optional, Union
from urllib.parse import urljoin

import requests
from bs4 import BeautifulSoup, Tag
from loguru import logger
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type

from app.scrapers.base import BaseScraper


class ForexFactoryScraper(BaseScraper):
    """Scraper for Forex Factory economic calendar."""
    
    # Default headers to mimic a real browser
    DEFAULT_HEADERS = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
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
        'Cache-Control': 'max-age=0',
    }
    
    def __init__(self, base_url: str = "https://www.forexfactory.com"):
        """
        Initialize the scraper.
        
        Args:
            base_url: Base URL for Forex Factory
        """
        super().__init__()
        self.base_url = base_url
        self.session = requests.Session()
        self.session.headers.update(self.DEFAULT_HEADERS)
        
        # Add some randomization to avoid detection
        self.session.headers['User-Agent'] = self._get_random_user_agent()
        
        # Set timeout and retry configuration
        self.timeout = 30
        self.max_retries = 3
        self.retry_delay = 2
    
    def _get_random_user_agent(self) -> str:
        """Get a random user agent string."""
        user_agents = [
            'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36',
            'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.1 Safari/605.1.15',
            'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
        ]
        return random.choice(user_agents)
        
    def scrape_events(
        self,
        start_date: Optional[date] = None,
        end_date: Optional[date] = None,
        currencies: Optional[List[str]] = None
    ) -> List[Dict[str, Any]]:
        """
        Scrape economic events from Forex Factory.
        
        Args:
            start_date: Start date for scraping (defaults to today)
            end_date: End date for scraping (defaults to start_date + 7 days)
            currencies: List of currency codes to filter (optional)
            
        Returns:
            List of event dictionaries
        """
        if start_date is None:
            start_date = date.today()
        
        if end_date is None:
            end_date = start_date + timedelta(days=7)
        
        logger.info(f"Scraping Forex Factory events from {start_date} to {end_date}")
        
        events: List[Dict[str, Any]] = []
        current_date = start_date
        
        while current_date <= end_date:
            try:
                daily_events = self._scrape_daily_events(current_date)
                
                # Filter by currencies if specified
                if currencies:
                    daily_events = [
                        event for event in daily_events
                        if event.get('currency') in currencies
                    ]
                
                events.extend(daily_events)
                logger.info(f"Scraped {len(daily_events)} events for {current_date}")
                
                # Rate limiting
                time.sleep(1)
                
            except Exception as e:
                logger.error(f"Error scraping events for {current_date}: {e}")
            
            current_date += timedelta(days=1)
        
        logger.info(f"Total events scraped: {len(events)}")
        return events
    
    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=10),
        retry=retry_if_exception_type((requests.RequestException, requests.Timeout, requests.ConnectionError))
    )
    def _make_request_with_retry(self, url: str) -> requests.Response:
        """
        Make HTTP request with retry mechanism.
        
        Args:
            url: URL to request
            
        Returns:
            Response object
            
        Raises:
            requests.RequestException: If all retries fail
        """
        # Add some randomization to headers for each request
        headers = self.session.headers.copy()
        headers['User-Agent'] = self._get_random_user_agent()
        
        # Add random delay to avoid rate limiting
        time.sleep(random.uniform(1, 3))
        
        logger.debug(f"Making request to: {url}")
        response = self.session.get(url, timeout=self.timeout, headers=headers)
        
        # Check for specific error responses
        if response.status_code == 403:
            logger.warning(f"403 Forbidden received for {url}. Retrying with different headers...")
            # Try with different headers
            headers.update({
                'Referer': 'https://www.forexfactory.com/',
                'Origin': 'https://www.forexfactory.com',
                'Sec-Ch-Ua': '"Not_A Brand";v="8", "Chromium";v="120", "Google Chrome";v="120"',
                'Sec-Ch-Ua-Mobile': '?0',
                'Sec-Ch-Ua-Platform': '"Windows"',
            })
            time.sleep(random.uniform(3, 6))  # Longer delay for 403
            response = self.session.get(url, timeout=self.timeout, headers=headers)
        
        response.raise_for_status()
        return response
    
    def _scrape_daily_events(self, target_date: date) -> List[Dict[str, Any]]:
        """
        Scrape events for a specific date.
        
        Args:
            target_date: Date to scrape events for
            
        Returns:
            List of event dictionaries
        """
        # Format date for URL
        date_str = target_date.strftime("%Y-%m-%d")
        url = f"{self.base_url}/calendar?day={date_str}"
        
        try:
            logger.info(f"Scraping events for {target_date} from {url}")
            response = self._make_request_with_retry(url)
            
            if not response.content:
                logger.warning(f"Empty response received for {target_date}")
                return []
            
            soup = BeautifulSoup(response.content, 'html.parser')
            events = self._parse_calendar_page(soup, target_date)
            
            logger.info(f"Successfully scraped {len(events)} events for {target_date}")
            return events
            
        except requests.exceptions.HTTPError as e:
            if e.response.status_code == 403:
                logger.error(f"403 Forbidden error for {target_date}. ForexFactory may be blocking requests.")
                logger.error(f"URL: {url}")
                logger.error(f"Headers used: {dict(self.session.headers)}")
            else:
                logger.error(f"HTTP error {e.response.status_code} for {target_date}: {e}")
            return []
        except requests.RequestException as e:
            logger.error(f"Request error for {target_date}: {e}")
            return []
        except Exception as e:
            logger.error(f"Unexpected error scraping {target_date}: {e}")
            return []
    
    def _parse_calendar_page(self, soup: BeautifulSoup, target_date: date) -> List[Dict[str, Any]]:
        """
        Parse the calendar page HTML.
        
        Args:
            soup: BeautifulSoup object of the page
            target_date: Date being parsed
            
        Returns:
            List of event dictionaries
        """
        events: List[Dict[str, Any]] = []
        
        # Find the calendar table
        calendar_table = soup.find('table', class_='calendar__table')
        if not calendar_table:
            logger.warning(f"No calendar table found for {target_date}")
            return events
        
        # Find all event rows
        event_rows = calendar_table.find_all('tr', class_='calendar__row')
        
        for row in event_rows:
            try:
                event_data = self._parse_event_row(row, target_date)
                if event_data:
                    events.append(event_data)
            except Exception as e:
                logger.error(f"Error parsing event row: {e}")
                continue
        
        return events
    
    def _parse_event_row(self, row: Tag, target_date: date) -> Optional[Dict[str, Any]]:
        """
        Parse a single event row.
        
        Args:
            row: BeautifulSoup Tag object for the row
            target_date: Date of the event
            
        Returns:
            Event dictionary or None if parsing fails
        """
        try:
            # Extract time
            time_cell = row.find('td', class_='calendar__time')
            event_time = self._parse_time(time_cell) if time_cell else None
            
            # Extract currency
            currency_cell = row.find('td', class_='calendar__currency')
            currency = self._parse_currency(currency_cell) if currency_cell else None
            
            # Extract impact
            impact_cell = row.find('td', class_='calendar__impact')
            impact = self._parse_impact(impact_cell) if impact_cell else None
            
            # Extract event name
            event_cell = row.find('td', class_='calendar__event')
            event_name = self._parse_event_name(event_cell) if event_cell else None
            
            # Extract forecast, previous, actual
            detail_cell = row.find('td', class_='calendar__detail')
            forecast, previous, actual = self._parse_details(detail_cell) if detail_cell else (None, None, None)
            
            # Skip if no event name
            if not event_name:
                return None
            
            return {
                'date': target_date.strftime('%Y-%m-%d'),
                'time': event_time,
                'currency': currency,
                'impact': impact,
                'event_name': event_name.strip(),
                'forecast': forecast,
                'previous': previous,
                'actual': actual,
                'source': 'forex_factory',
                'source_url': f"{self.base_url}/calendar?day={target_date.strftime('%Y-%m-%d')}"
            }
            
        except Exception as e:
            logger.error(f"Error parsing event row: {e}")
            return None
    
    def _parse_time(self, time_cell: Tag) -> Optional[str]:
        """Parse time from time cell."""
        if not time_cell:
            return None
        
        time_text = time_cell.get_text(strip=True)
        
        # Handle "All Day" events
        if not time_text or time_text.lower() in ['', 'all day', 'tentative']:
            return None
        
        # Parse time format (e.g., "8:30am", "12:00pm")
        time_match = re.search(r'(\d{1,2}):(\d{2})(am|pm)', time_text.lower())
        if time_match:
            hour = int(time_match.group(1))
            minute = int(time_match.group(2))
            period = time_match.group(3)
            
            # Convert to 24-hour format
            if period == 'pm' and hour != 12:
                hour += 12
            elif period == 'am' and hour == 12:
                hour = 0
            
            return f"{hour:02d}:{minute:02d}"
        
        return None
    
    def _parse_currency(self, currency_cell: Tag) -> Optional[str]:
        """Parse currency from currency cell."""
        if not currency_cell:
            return None
        
        currency_text = currency_cell.get_text(strip=True)
        
        # Common currency codes
        valid_currencies = {
            'USD', 'EUR', 'GBP', 'JPY', 'AUD', 'CAD', 'CHF', 'NZD',
            'CNY', 'SEK', 'NOK', 'DKK', 'PLN', 'CZK', 'HUF', 'TRY',
            'ZAR', 'MXN', 'BRL', 'RUB', 'INR', 'KRW', 'SGD', 'HKD'
        }
        
        if currency_text.upper() in valid_currencies:
            return currency_text.upper()
        
        return None
    
    def _parse_impact(self, impact_cell: Tag) -> Optional[str]:
        """Parse impact level from impact cell."""
        if not impact_cell:
            return None
        
        # Look for impact icons or classes
        impact_spans = impact_cell.find_all('span', class_=re.compile(r'calendar__impact-icon'))
        
        if impact_spans:
            # Count the number of impact icons
            icon_count = len(impact_spans)
            
            if icon_count >= 3:
                return 'HIGH'
            elif icon_count == 2:
                return 'MEDIUM'
            elif icon_count == 1:
                return 'LOW'
        
        # Fallback: check for text indicators
        impact_text = impact_cell.get_text(strip=True).lower()
        
        if 'high' in impact_text or 'red' in impact_text:
            return 'HIGH'
        elif 'medium' in impact_text or 'orange' in impact_text:
            return 'MEDIUM'
        elif 'low' in impact_text or 'yellow' in impact_text:
            return 'LOW'
        
        return 'LOW'  # Default to LOW if unclear
    
    def _parse_event_name(self, event_cell: Tag) -> Optional[str]:
        """Parse event name from event cell."""
        if not event_cell:
            return None
        
        # Get text content, removing extra whitespace
        event_text = event_cell.get_text(separator=' ', strip=True)
        
        # Clean up the text
        event_text = re.sub(r'\s+', ' ', event_text)
        event_text = event_text.strip()
        
        return event_text if event_text else None
    
    def _parse_details(self, detail_cell: Tag) -> tuple[Optional[str], Optional[str], Optional[str]]:
        """Parse forecast, previous, and actual values from detail cell."""
        if not detail_cell:
            return None, None, None
        
        forecast = None
        previous = None
        actual = None
        
        # Look for specific spans or divs with forecast/previous/actual data
        forecast_elem = detail_cell.find(attrs={'data-forecast': True})
        if forecast_elem:
            forecast = forecast_elem.get('data-forecast', '').strip()
        
        previous_elem = detail_cell.find(attrs={'data-previous': True})
        if previous_elem:
            previous = previous_elem.get('data-previous', '').strip()
        
        actual_elem = detail_cell.find(attrs={'data-actual': True})
        if actual_elem:
            actual = actual_elem.get('data-actual', '').strip()
        
        # Fallback: parse from text content
        if not any([forecast, previous, actual]):
            detail_text = detail_cell.get_text(strip=True)
            
            # Try to extract numbers/percentages
            numbers = re.findall(r'[-+]?\d*\.?\d+%?[KMB]?', detail_text)
            
            if len(numbers) >= 3:
                forecast, previous, actual = numbers[:3]
            elif len(numbers) == 2:
                previous, actual = numbers
            elif len(numbers) == 1:
                actual = numbers[0]
        
        # Clean up values
        def clean_value(value: Optional[str]) -> Optional[str]:
            if not value or value.strip() == '':
                return None
            return value.strip()
        
        return clean_value(forecast), clean_value(previous), clean_value(actual)
    
    def test_connection(self) -> bool:
        """
        Test connection to Forex Factory.
        
        Returns:
            True if connection is successful
        """
        try:
            logger.info("Testing connection to Forex Factory...")
            response = self._make_request_with_retry(self.base_url)
            
            # Check if we got a valid page
            soup = BeautifulSoup(response.content, 'html.parser')
            title = soup.find('title')
            
            if title and 'forex factory' in title.get_text().lower():
                logger.info("Forex Factory connection test successful")
                return True
            else:
                logger.warning("Forex Factory connection test failed: unexpected page content")
                logger.debug(f"Page title: {title.get_text() if title else 'No title found'}")
                return False
                
        except requests.exceptions.HTTPError as e:
            if e.response.status_code == 403:
                logger.error("403 Forbidden: Forex Factory is blocking our requests")
                logger.error("Try using a VPN or different IP address")
            else:
                logger.error(f"HTTP error during connection test: {e}")
            return False
        except Exception as e:
            logger.error(f"Forex Factory connection test failed: {e}")
            return False
    
    def get_available_currencies(self) -> List[str]:
        """
        Get list of available currencies from Forex Factory.
        
        Returns:
            List of currency codes
        """
        try:
            url = f"{self.base_url}/calendar"
            response = self.session.get(url, timeout=30)
            response.raise_for_status()
            
            soup = BeautifulSoup(response.content, 'html.parser')
            
            # Look for currency filter options
            currency_options = soup.find_all('option', value=re.compile(r'^[A-Z]{3}$'))
            
            currencies = []
            for option in currency_options:
                currency = option.get('value', '').strip().upper()
                if currency and len(currency) == 3:
                    currencies.append(currency)
            
            # Remove duplicates and sort
            currencies = sorted(list(set(currencies)))
            
            logger.info(f"Found {len(currencies)} available currencies")
            return currencies
            
        except Exception as e:
            logger.error(f"Error getting available currencies: {e}")
            return ['USD', 'EUR', 'GBP', 'JPY', 'AUD', 'CAD', 'CHF', 'NZD']  # Default list
    
    def scrape_date_range(self, start_date: date, end_date: date) -> List[Dict[str, Any]]:
        """
        Scrape data for a date range.
        
        Args:
            start_date: Start date for scraping
            end_date: End date for scraping
            
        Returns:
            List of scraped event dictionaries
        """
        return self.scrape_events(start_date, end_date)
    
    def scrape_single_date(self, target_date: date) -> List[Dict[str, Any]]:
        """
        Scrape data for a single date.
        
        Args:
            target_date: Date to scrape
            
        Returns:
            List of scraped event dictionaries
        """
        return self._scrape_daily_events(target_date)
    
    def close(self) -> None:
        """Close the session."""
        if self.session:
            self.session.close()
            logger.debug("Forex Factory scraper session closed")
