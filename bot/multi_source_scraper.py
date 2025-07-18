"""
Multi-source forex news scraper with fallback system.
"""
import logging
import asyncio
from typing import List, Dict, Any, Optional
from datetime import datetime

from .config import Config
from .scraper import ChatGPTAnalyzer
from .sources import get_source_manager, NewsSource
from .sources.forex_factory import ForexFactorySource
from .sources.alpha_vantage import AlphaVantageSource
from .sources.fmp import FMPSource
from .sources.newsapi import NewsAPISource
from .sources.rss import RSSSource
from .utils.normalizer import NewsNormalizer

logger = logging.getLogger(__name__)


class MultiSourceForexScraper:
    """Multi-source forex news scraper with intelligent fallback."""
    
    def __init__(self, config: Config):
        self.config = config
        self.analyzer = ChatGPTAnalyzer(config.openai_api_key)
        self.source_manager = get_source_manager()
        self._initialize_sources()
    
    def _initialize_sources(self):
        """Initialize all available news sources."""
        logger.info("Initializing news sources...")
        
        # Initialize ForexFactory source
        if self.config.news_sources['forex_factory']['enabled']:
            ff_source = ForexFactorySource(self.config, self.analyzer)
            ff_source.priority = self.config.news_sources['forex_factory']['priority']
            self.source_manager.register_source(ff_source)
        
        # Initialize Alpha Vantage source
        if self.config.news_sources['alpha_vantage']['enabled']:
            av_api_key = self.config.news_sources['alpha_vantage']['api_key']
            if av_api_key:
                av_source = AlphaVantageSource(av_api_key)
                av_source.priority = self.config.news_sources['alpha_vantage']['priority']
                self.source_manager.register_source(av_source)
            else:
                logger.warning("Alpha Vantage enabled but no API key provided")
        
        # Initialize FMP source
        if self.config.news_sources['fmp']['enabled']:
            fmp_api_key = self.config.news_sources['fmp']['api_key']
            if fmp_api_key:
                fmp_source = FMPSource(fmp_api_key)
                fmp_source.priority = self.config.news_sources['fmp']['priority']
                self.source_manager.register_source(fmp_source)
            else:
                logger.warning("FMP enabled but no API key provided")
        
        # Initialize NewsAPI source
        if self.config.news_sources['newsapi']['enabled']:
            newsapi_key = self.config.news_sources['newsapi']['api_key']
            if newsapi_key:
                newsapi_source = NewsAPISource(newsapi_key)
                newsapi_source.priority = self.config.news_sources['newsapi']['priority']
                self.source_manager.register_source(newsapi_source)
            else:
                logger.warning("NewsAPI enabled but no API key provided")
        
        # Initialize RSS source
        if self.config.news_sources['rss']['enabled']:
            rss_source = RSSSource()
            rss_source.priority = self.config.news_sources['rss']['priority']
            self.source_manager.register_source(rss_source)
        
        available_sources = self.source_manager.get_available_sources()
        logger.info(f"Initialized {len(available_sources)} available news sources")
        
        for source in available_sources:
            logger.info(f"  - {source.name} (priority: {source.priority})")
    
    async def scrape_news(self, target_date: Optional[datetime] = None, impact_level: str = "high", debug: bool = False) -> List[Dict[str, Any]]:
        """Scrape news from multiple sources with fallback."""
        if target_date is None:
            from pytz import timezone
            target_date = datetime.now(timezone(self.config.timezone))
        
        logger.info(f"Starting multi-source news scraping for {target_date.date()}")
        
        try:
            # Get raw news from sources
            raw_news = await self.source_manager.fetch_news(target_date, impact_level)
            
            if not raw_news:
                logger.warning("No news items retrieved from any source")
                return []
            
            logger.info(f"Retrieved {len(raw_news)} raw news items")
            
            # Normalize the data
            normalized_news = NewsNormalizer.normalize_events(raw_news)
            logger.info(f"Normalized to {len(normalized_news)} events")
            
            # Remove duplicates
            unique_news = NewsNormalizer.deduplicate_events(normalized_news)
            logger.info(f"Deduplicated to {len(unique_news)} unique events")
            
            # Filter by impact level
            filtered_news = NewsNormalizer.filter_by_impact(unique_news, impact_level)
            logger.info(f"Filtered to {len(filtered_news)} events with impact >= {impact_level}")
            
            # Add ChatGPT analysis to high-impact events
            if self.analyzer.api_key and filtered_news:
                await self._add_analysis_to_events(filtered_news)
            
            # Sort by time and impact
            sorted_news = self._sort_events(filtered_news)
            
            logger.info(f"✅ Multi-source scraping completed: {len(sorted_news)} final events")
            
            if debug:
                self._log_source_breakdown(sorted_news)
            
            return sorted_news
            
        except Exception as e:
            logger.error(f"Multi-source scraping failed: {e}")
            return []
    
    async def _add_analysis_to_events(self, events: List[Dict[str, Any]]):
        """Add ChatGPT analysis to high-impact events."""
        logger.info("Adding ChatGPT analysis to events...")
        
        # Only analyze high-impact events to save API calls
        high_impact_events = [e for e in events if e.get('impact') == 'high']
        
        for event in high_impact_events[:5]:  # Limit to 5 events to control costs
            try:
                # Convert to format expected by analyzer
                analysis_item = {
                    'time': event['time'],
                    'currency': event['currency'],
                    'event': event['event'],
                    'actual': event['actual'],
                    'forecast': event['forecast'],
                    'previous': event['previous']
                }
                
                analysis = self.analyzer.analyze_news(analysis_item)
                if analysis and analysis != "⚠️ ChatGPT analysis skipped: API key not configured.":
                    event['analysis'] = f"{event.get('analysis', '')} | AI: {analysis}"
                
            except Exception as e:
                logger.warning(f"Failed to add analysis to event: {e}")
                continue
    
    def _sort_events(self, events: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Sort events by impact and time."""
        impact_priority = {'high': 3, 'medium': 2, 'low': 1}
        
        def sort_key(event):
            impact_score = impact_priority.get(event.get('impact', 'medium'), 2)
            time_str = event.get('time', 'N/A')
            
            # Convert time to sortable format
            if time_str != 'N/A' and ':' in time_str:
                try:
                    hour, minute = map(int, time_str.split(':')[:2])
                    time_score = hour * 60 + minute
                except:
                    time_score = 9999  # Put invalid times at end
            else:
                time_score = 9999
            
            return (-impact_score, time_score)  # Negative impact for descending order
        
        return sorted(events, key=sort_key)
    
    def _log_source_breakdown(self, events: List[Dict[str, Any]]):
        """Log breakdown of events by source."""
        source_counts = {}
        for event in events:
            source = event.get('source', 'Unknown')
            source_counts[source] = source_counts.get(source, 0) + 1
        
        logger.info("Source breakdown:")
        for source, count in sorted(source_counts.items()):
            logger.info(f"  - {source}: {count} events")
    
    def get_source_status(self) -> Dict[str, Any]:
        """Get status of all sources."""
        return self.source_manager.get_source_status()
    
    def reset_source_failures(self):
        """Reset failure counts for all sources."""
        for source in self.source_manager.sources:
            source.consecutive_failures = 0
            source.last_error = None
        logger.info("Reset failure counts for all sources")


# Convenience function for backward compatibility
async def scrape_forex_news_multi_source(config: Config, target_date: Optional[datetime] = None, impact_level: str = "high", debug: bool = False) -> List[Dict[str, Any]]:
    """Scrape forex news using multi-source approach."""
    scraper = MultiSourceForexScraper(config)
    return await scraper.scrape_news(target_date, impact_level, debug)
