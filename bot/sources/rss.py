
"""
RSS feed forex news sources.
"""
import logging
import aiohttp
import asyncio
import feedparser
from typing import List, Dict, Any
from datetime import datetime, timedelta
import re
from io import StringIO

from . import NewsSource

logger = logging.getLogger(__name__)


class RSSSource(NewsSource):
    """RSS feed forex news source."""
    
    def __init__(self):
        super().__init__(name="RSS_Feeds", priority=5, enabled=True)
        self.feeds = [
            {
                'name': 'Investing.com Forex',
                'url': 'https://www.investing.com/rss/news_25.rss',
                'currency_mapping': self._extract_currencies_from_text
            },
            {
                'name': 'FXStreet',
                'url': 'https://www.fxstreet.com/rss/news',
                'currency_mapping': self._extract_currencies_from_text
            },
            {
                'name': 'DailyFX',
                'url': 'https://www.dailyfx.com/feeds/market-news',
                'currency_mapping': self._extract_currencies_from_text
            },
            {
                'name': 'ForexLive',
                'url': 'https://www.forexlive.com/feed/',
                'currency_mapping': self._extract_currencies_from_text
            }
        ]
        self.rate_limit_delay = 2
    
    async def fetch_news(self, target_date: datetime, impact_level: str = "high") -> List[Dict[str, Any]]:
        """Fetch news from RSS feeds."""
        try:
            logger.info(f"Fetching RSS forex news for {target_date.date()}")
            
            all_news_items = []
            
            for feed_info in self.feeds:
                try:
                    logger.info(f"Fetching from RSS feed: {feed_info['name']}")
                    
                    # Fetch RSS feed
                    async with aiohttp.ClientSession() as session:
                        async with session.get(feed_info['url'], timeout=30) as response:
                            if response.status != 200:
                                logger.warning(f"RSS feed {feed_info['name']} returned {response.status}")
                                continue
                            
                            content = await response.text()
                    
                    # Parse RSS feed
                    feed = feedparser.parse(content)
                    
                    if not feed.entries:
                        logger.warning(f"No entries found in RSS feed: {feed_info['name']}")
                        continue
                    
                    # Process entries
                    for entry in feed.entries:
                        # Check if entry is from target date
                        if not self._is_target_date(entry, target_date):
                            continue
                        
                        title = entry.get('title', '')
                        description = entry.get('description', '') or entry.get('summary', '')
                        published = entry.get('published', '')
                        link = entry.get('link', '')
                        
                        # Extract currencies from title and description
                        text = f"{title} {description}"
                        currencies = self._extract_currencies_from_text(text)
                        
                        if currencies:
                            for currency in currencies:
                                normalized_item = {
                                    'source': f"RSS_{feed_info['name'].replace(' ', '_')}",
                                    'time': self._parse_time(published),
                                    'currency': currency,
                                    'event': title[:100] + '...' if len(title) > 100 else title,
                                    'actual': 'N/A',
                                    'forecast': 'N/A',
                                    'previous': 'N/A',
                                    'impact': self._determine_impact(text),
                                    'analysis': f"RSS: {feed_info['name']}",
                                    'date': target_date.date(),
                                    'raw_data': {
                                        'title': title,
                                        'description': description,
                                        'published': published,
                                        'link': link,
                                        'feed_name': feed_info['name']
                                    }
                                }
                                all_news_items.append(normalized_item)
                    
                    # Rate limiting between feeds
                    await asyncio.sleep(self.rate_limit_delay)
                    
                except Exception as e:
                    logger.warning(f"Failed to fetch RSS feed {feed_info['name']}: {e}")
                    continue
            
            logger.info(f"RSS feeds returned {len(all_news_items)} news items")
            return all_news_items
            
        except Exception as e:
            logger.error(f"RSS fetch failed: {e}")
            raise
    
    def _is_target_date(self, entry: dict, target_date: datetime) -> bool:
        """Check if RSS entry is from target date."""
        try:
            published = entry.get('published', '')
            if not published:
                return True  # Include if no date info
            
            # Parse various date formats
            import dateutil.parser
            entry_date = dateutil.parser.parse(published)
            
            # Check if same date (allowing some timezone flexibility)
            date_diff = abs((entry_date.date() - target_date.date()).days)
            return date_diff <= 1
            
        except Exception:
            return True  # Include if can't parse date
    
    def _extract_currencies_from_text(self, text: str) -> List[str]:
        """Extract currency codes from text."""
        currencies = []
        text_upper = text.upper()
        
        currency_patterns = {
            'USD': ['USD', 'DOLLAR', 'US DOLLAR', 'GREENBACK', 'DXY'],
            'EUR': ['EUR', 'EURO', 'EUROPEAN', 'EURUSD', 'EURJPY', 'EURGBP'],
            'GBP': ['GBP', 'POUND', 'STERLING', 'BRITISH POUND', 'GBPUSD', 'GBPJPY'],
            'JPY': ['JPY', 'YEN', 'JAPANESE YEN', 'USDJPY', 'EURJPY', 'GBPJPY'],
            'AUD': ['AUD', 'AUSTRALIAN DOLLAR', 'AUDUSD', 'AUDCAD', 'AUDJPY'],
            'CAD': ['CAD', 'CANADIAN DOLLAR', 'USDCAD', 'AUDCAD', 'CADJPY'],
            'CHF': ['CHF', 'SWISS FRANC', 'FRANC', 'USDCHF', 'EURCHF'],
            'NZD': ['NZD', 'NEW ZEALAND DOLLAR', 'NZDUSD', 'NZDJPY']
        }
        
        for currency, patterns in currency_patterns.items():
            if any(pattern in text_upper for pattern in patterns):
                currencies.append(currency)
        
        return list(set(currencies))[:3]  # Limit to 3 currencies per article
    
    def _determine_impact(self, text: str) -> str:
        """Determine impact level based on keywords."""
        text_upper = text.upper()
        
        high_impact_keywords = [
            'CENTRAL BANK', 'INTEREST RATE', 'FEDERAL RESERVE', 'ECB', 'BOJ', 'BOE',
            'GDP', 'INFLATION', 'CPI', 'PPI', 'UNEMPLOYMENT', 'NFP', 'FOMC',
            'CRISIS', 'EMERGENCY', 'BREAKING', 'ALERT'
        ]
        
        medium_impact_keywords = [
            'ECONOMIC', 'TRADE', 'RETAIL', 'MANUFACTURING', 'SERVICES',
            'HOUSING', 'CONSUMER', 'BUSINESS', 'SENTIMENT'
        ]
        
        if any(keyword in text_upper for keyword in high_impact_keywords):
            return "high"
        elif any(keyword in text_upper for keyword in medium_impact_keywords):
            return "medium"
        else:
            return "low"
    
    def _parse_time(self, time_str: str) -> str:
        """Parse RSS time format."""
        try:
            import dateutil.parser
            dt = dateutil.parser.parse(time_str)
            return dt.strftime('%H:%M')
        except:
            return "N/A"
    
    def is_available(self) -> bool:
        """RSS feeds are always available."""
        return True
