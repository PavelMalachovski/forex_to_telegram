
"""
NewsAPI forex news source.
"""
import logging
import aiohttp
import asyncio
from typing import List, Dict, Any
from datetime import datetime, timedelta
import re

from . import NewsSource

logger = logging.getLogger(__name__)


class NewsAPISource(NewsSource):
    """NewsAPI forex news source."""
    
    def __init__(self, api_key: str = None):
        super().__init__(name="NewsAPI", priority=4, enabled=bool(api_key))
        self.api_key = api_key
        self.base_url = "https://newsapi.org/v2"
        self.rate_limit_delay = 1
    
    async def fetch_news(self, target_date: datetime, impact_level: str = "high") -> List[Dict[str, Any]]:
        """Fetch forex news from NewsAPI."""
        if not self.api_key:
            raise Exception("NewsAPI key not configured")
        
        try:
            logger.info(f"Fetching NewsAPI forex news for {target_date.date()}")
            
            # NewsAPI everything endpoint with forex keywords
            date_str = target_date.strftime('%Y-%m-%d')
            url = f"{self.base_url}/everything"
            
            # Forex-related keywords
            forex_query = 'forex OR "foreign exchange" OR "currency trading" OR "central bank" OR "interest rates" OR "economic data" OR GDP OR inflation OR unemployment'
            
            params = {
                'q': forex_query,
                'from': date_str,
                'to': date_str,
                'language': 'en',
                'sortBy': 'relevancy',
                'pageSize': 50,
                'apiKey': self.api_key
            }
            
            async with aiohttp.ClientSession() as session:
                async with session.get(url, params=params) as response:
                    if response.status != 200:
                        raise Exception(f"HTTP {response.status}: {await response.text()}")
                    
                    data = await response.json()
                    
                    if data.get('status') != 'ok':
                        raise Exception(f"API Error: {data.get('message', 'Unknown error')}")
                    
                    # Parse news articles
                    news_items = []
                    articles = data.get('articles', [])
                    
                    for article in articles:
                        title = article.get('title', '')
                        description = article.get('description', '')
                        published_at = article.get('publishedAt', '')
                        source_name = article.get('source', {}).get('name', 'Unknown')
                        
                        # Extract currency mentions from title and description
                        text = f"{title} {description}".upper()
                        currencies = self._extract_currencies(text)
                        
                        if currencies:
                            for currency in currencies:
                                normalized_item = {
                                    'source': 'NewsAPI',
                                    'time': self._parse_time(published_at),
                                    'currency': currency,
                                    'event': title[:100] + '...' if len(title) > 100 else title,
                                    'actual': 'N/A',
                                    'forecast': 'N/A',
                                    'previous': 'N/A',
                                    'impact': self._determine_impact(text),
                                    'analysis': f"Source: {source_name}",
                                    'date': target_date.date(),
                                    'raw_data': {
                                        'title': title,
                                        'description': description,
                                        'source': source_name,
                                        'published_at': published_at
                                    }
                                }
                                news_items.append(normalized_item)
            
            # Rate limiting
            await asyncio.sleep(self.rate_limit_delay)
            
            logger.info(f"NewsAPI returned {len(news_items)} news items")
            return news_items
            
        except Exception as e:
            logger.error(f"NewsAPI fetch failed: {e}")
            raise
    
    def _extract_currencies(self, text: str) -> List[str]:
        """Extract currency codes from text."""
        currencies = []
        currency_patterns = {
            'USD': ['USD', 'DOLLAR', 'US DOLLAR', 'GREENBACK'],
            'EUR': ['EUR', 'EURO', 'EUROPEAN'],
            'GBP': ['GBP', 'POUND', 'STERLING', 'BRITISH POUND'],
            'JPY': ['JPY', 'YEN', 'JAPANESE YEN'],
            'AUD': ['AUD', 'AUSTRALIAN DOLLAR'],
            'CAD': ['CAD', 'CANADIAN DOLLAR'],
            'CHF': ['CHF', 'SWISS FRANC', 'FRANC'],
            'NZD': ['NZD', 'NEW ZEALAND DOLLAR']
        }
        
        for currency, patterns in currency_patterns.items():
            if any(pattern in text for pattern in patterns):
                currencies.append(currency)
        
        return currencies[:2]  # Limit to 2 currencies per article
    
    def _determine_impact(self, text: str) -> str:
        """Determine impact level based on keywords."""
        high_impact_keywords = [
            'CENTRAL BANK', 'INTEREST RATE', 'FEDERAL RESERVE', 'ECB', 'BOJ',
            'GDP', 'INFLATION', 'UNEMPLOYMENT', 'CRISIS', 'EMERGENCY'
        ]
        
        if any(keyword in text for keyword in high_impact_keywords):
            return "high"
        else:
            return "medium"
    
    def _parse_time(self, time_str: str) -> str:
        """Parse NewsAPI time format."""
        try:
            # Format: 2024-01-01T12:00:00Z
            if 'T' in time_str:
                time_part = time_str.split('T')[1]
                return time_part[:5]  # HH:MM
            return "N/A"
        except:
            return "N/A"
    
    def is_available(self) -> bool:
        """Check if NewsAPI is available."""
        return bool(self.api_key)
