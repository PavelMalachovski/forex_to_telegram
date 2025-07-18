
"""
Alpha Vantage news source.
"""
import logging
import aiohttp
import asyncio
from typing import List, Dict, Any
from datetime import datetime, timedelta
import json

from . import NewsSource

logger = logging.getLogger(__name__)


class AlphaVantageSource(NewsSource):
    """Alpha Vantage news source."""
    
    def __init__(self, api_key: str = None):
        super().__init__(name="AlphaVantage", priority=2, enabled=bool(api_key))
        self.api_key = api_key
        self.base_url = "https://www.alphavantage.co/query"
        self.rate_limit_delay = 12  # Alpha Vantage free tier: 5 calls per minute
    
    async def fetch_news(self, target_date: datetime, impact_level: str = "high") -> List[Dict[str, Any]]:
        """Fetch news from Alpha Vantage."""
        if not self.api_key:
            raise Exception("Alpha Vantage API key not configured")
        
        try:
            logger.info(f"Fetching Alpha Vantage news for {target_date.date()}")
            
            # Alpha Vantage NEWS_SENTIMENT endpoint
            params = {
                'function': 'NEWS_SENTIMENT',
                'tickers': 'FOREX:USD,FOREX:EUR,FOREX:GBP,FOREX:JPY',
                'topics': 'financial_markets,economy_fiscal,economy_monetary',
                'time_from': target_date.strftime('%Y%m%dT0000'),
                'time_to': (target_date + timedelta(days=1)).strftime('%Y%m%dT0000'),
                'limit': 50,
                'apikey': self.api_key
            }
            
            async with aiohttp.ClientSession() as session:
                async with session.get(self.base_url, params=params) as response:
                    if response.status != 200:
                        raise Exception(f"HTTP {response.status}: {await response.text()}")
                    
                    data = await response.json()
                    
                    if 'Error Message' in data:
                        raise Exception(f"API Error: {data['Error Message']}")
                    
                    if 'Note' in data:
                        raise Exception(f"Rate limit: {data['Note']}")
                    
                    # Parse news items
                    news_items = []
                    feed = data.get('feed', [])
                    
                    for article in feed:
                        # Extract relevant forex information
                        title = article.get('title', '')
                        summary = article.get('summary', '')
                        time_published = article.get('time_published', '')
                        
                        # Parse sentiment and relevance
                        overall_sentiment = article.get('overall_sentiment_label', 'Neutral')
                        overall_score = float(article.get('overall_sentiment_score', 0))
                        
                        # Extract ticker sentiments for forex pairs
                        ticker_sentiment = article.get('ticker_sentiment', [])
                        forex_tickers = [t for t in ticker_sentiment if t.get('ticker', '').startswith('FOREX:')]
                        
                        if forex_tickers:
                            for ticker_info in forex_tickers:
                                currency = ticker_info.get('ticker', '').replace('FOREX:', '')
                                relevance = float(ticker_info.get('relevance_score', 0))
                                sentiment = ticker_info.get('ticker_sentiment_label', 'Neutral')
                                
                                # Only include high relevance items
                                if relevance > 0.3:
                                    normalized_item = {
                                        'source': 'AlphaVantage',
                                        'time': self._parse_time(time_published),
                                        'currency': currency,
                                        'event': title[:100] + '...' if len(title) > 100 else title,
                                        'actual': 'N/A',
                                        'forecast': 'N/A',
                                        'previous': 'N/A',
                                        'impact': self._determine_impact(relevance, abs(overall_score)),
                                        'analysis': f"Sentiment: {sentiment} ({overall_sentiment}), Relevance: {relevance:.2f}",
                                        'date': target_date.date(),
                                        'raw_data': {
                                            'title': title,
                                            'summary': summary,
                                            'sentiment': sentiment,
                                            'relevance': relevance,
                                            'overall_sentiment': overall_sentiment,
                                            'overall_score': overall_score
                                        }
                                    }
                                    news_items.append(normalized_item)
            
            # Rate limiting
            await asyncio.sleep(self.rate_limit_delay)
            
            logger.info(f"Alpha Vantage returned {len(news_items)} news items")
            return news_items
            
        except Exception as e:
            logger.error(f"Alpha Vantage fetch failed: {e}")
            raise
    
    def _parse_time(self, time_str: str) -> str:
        """Parse Alpha Vantage time format."""
        try:
            if len(time_str) >= 8:
                # Format: 20240101T120000
                return f"{time_str[9:11]}:{time_str[11:13]}"
            return "N/A"
        except:
            return "N/A"
    
    def _determine_impact(self, relevance: float, sentiment_score: float) -> str:
        """Determine impact level based on relevance and sentiment."""
        if relevance > 0.7 or sentiment_score > 0.5:
            return "high"
        elif relevance > 0.5 or sentiment_score > 0.3:
            return "medium"
        else:
            return "low"
    
    def is_available(self) -> bool:
        """Check if Alpha Vantage is available."""
        return bool(self.api_key)
