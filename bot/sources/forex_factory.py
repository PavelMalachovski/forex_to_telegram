
"""
ForexFactory news source (existing implementation).
"""
import logging
from typing import List, Dict, Any
from datetime import datetime

from . import NewsSource
from ..scraper import ForexNewsScraper, ChatGPTAnalyzer

logger = logging.getLogger(__name__)


class ForexFactorySource(NewsSource):
    """ForexFactory news source."""
    
    def __init__(self, config, analyzer: ChatGPTAnalyzer):
        super().__init__(name="ForexFactory", priority=1, enabled=True)  # Highest priority
        self.config = config
        self.analyzer = analyzer
        self.scraper = ForexNewsScraper(config, analyzer)
    
    async def fetch_news(self, target_date: datetime, impact_level: str = "high") -> List[Dict[str, Any]]:
        """Fetch news from ForexFactory."""
        try:
            logger.info(f"Fetching ForexFactory news for {target_date.date()}")
            news_items = await self.scraper.scrape_news(target_date, impact_level, debug=True)
            
            # Normalize the data format
            normalized_items = []
            for item in news_items:
                normalized_item = {
                    'source': 'ForexFactory',
                    'time': item.get('time', 'N/A'),
                    'currency': item.get('currency', 'N/A'),
                    'event': item.get('event', 'N/A'),
                    'actual': item.get('actual', 'N/A'),
                    'forecast': item.get('forecast', 'N/A'),
                    'previous': item.get('previous', 'N/A'),
                    'impact': impact_level,
                    'analysis': item.get('analysis', ''),
                    'date': target_date.date(),
                    'raw_data': item
                }
                normalized_items.append(normalized_item)
            
            return normalized_items
            
        except Exception as e:
            logger.error(f"ForexFactory fetch failed: {e}")
            raise
    
    def is_available(self) -> bool:
        """ForexFactory is always available (no API keys required)."""
        return True
