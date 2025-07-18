
"""
Financial Modeling Prep (FMP) economic calendar source.
"""
import logging
import aiohttp
import asyncio
from typing import List, Dict, Any
from datetime import datetime, timedelta

from . import NewsSource

logger = logging.getLogger(__name__)


class FMPSource(NewsSource):
    """Financial Modeling Prep economic calendar source."""
    
    def __init__(self, api_key: str = None):
        super().__init__(name="FinancialModelingPrep", priority=3, enabled=bool(api_key))
        self.api_key = api_key
        self.base_url = "https://financialmodelingprep.com/api/v3"
        self.rate_limit_delay = 1  # FMP allows more requests
    
    async def fetch_news(self, target_date: datetime, impact_level: str = "high") -> List[Dict[str, Any]]:
        """Fetch economic calendar from FMP."""
        if not self.api_key:
            raise Exception("FMP API key not configured")
        
        try:
            logger.info(f"Fetching FMP economic calendar for {target_date.date()}")
            
            # FMP economic calendar endpoint
            date_str = target_date.strftime('%Y-%m-%d')
            url = f"{self.base_url}/economic_calendar"
            params = {
                'from': date_str,
                'to': date_str,
                'apikey': self.api_key
            }
            
            async with aiohttp.ClientSession() as session:
                async with session.get(url, params=params) as response:
                    if response.status != 200:
                        raise Exception(f"HTTP {response.status}: {await response.text()}")
                    
                    data = await response.json()
                    
                    if isinstance(data, dict) and 'Error Message' in data:
                        raise Exception(f"API Error: {data['Error Message']}")
                    
                    # Parse economic events
                    news_items = []
                    
                    for event in data:
                        if not isinstance(event, dict):
                            continue
                        
                        # Extract event information
                        event_name = event.get('event', '')
                        country = event.get('country', '')
                        currency = self._country_to_currency(country)
                        
                        # Skip if no currency mapping
                        if not currency:
                            continue
                        
                        time_str = event.get('time', '')
                        actual = event.get('actual', '')
                        estimate = event.get('estimate', '')
                        previous = event.get('previous', '')
                        impact_level_fmp = event.get('impact', 'Medium')
                        
                        # Filter by impact level if specified
                        if impact_level == "high" and impact_level_fmp.lower() not in ['high', 'important']:
                            continue
                        
                        normalized_item = {
                            'source': 'FinancialModelingPrep',
                            'time': self._parse_time(time_str),
                            'currency': currency,
                            'event': event_name,
                            'actual': str(actual) if actual else 'N/A',
                            'forecast': str(estimate) if estimate else 'N/A',
                            'previous': str(previous) if previous else 'N/A',
                            'impact': impact_level_fmp.lower(),
                            'analysis': f"Country: {country}, Impact: {impact_level_fmp}",
                            'date': target_date.date(),
                            'raw_data': event
                        }
                        news_items.append(normalized_item)
            
            # Rate limiting
            await asyncio.sleep(self.rate_limit_delay)
            
            logger.info(f"FMP returned {len(news_items)} economic events")
            return news_items
            
        except Exception as e:
            logger.error(f"FMP fetch failed: {e}")
            raise
    
    def _country_to_currency(self, country: str) -> str:
        """Map country to currency code."""
        country_currency_map = {
            'US': 'USD', 'United States': 'USD', 'USA': 'USD',
            'EU': 'EUR', 'European Union': 'EUR', 'Eurozone': 'EUR', 'Germany': 'EUR', 'France': 'EUR',
            'UK': 'GBP', 'United Kingdom': 'GBP', 'Britain': 'GBP',
            'JP': 'JPY', 'Japan': 'JPY',
            'AU': 'AUD', 'Australia': 'AUD',
            'CA': 'CAD', 'Canada': 'CAD',
            'CH': 'CHF', 'Switzerland': 'CHF',
            'NZ': 'NZD', 'New Zealand': 'NZD'
        }
        return country_currency_map.get(country, '')
    
    def _parse_time(self, time_str: str) -> str:
        """Parse FMP time format."""
        try:
            if ':' in time_str:
                return time_str
            return "N/A"
        except:
            return "N/A"
    
    def is_available(self) -> bool:
        """Check if FMP is available."""
        return bool(self.api_key)
