
"""
Multi-source forex news data providers with fallback system.
"""
import logging
from typing import List, Dict, Any, Optional
from datetime import datetime
from abc import ABC, abstractmethod

logger = logging.getLogger(__name__)


class NewsSource(ABC):
    """Abstract base class for news sources."""
    
    def __init__(self, name: str, priority: int = 100, enabled: bool = True):
        self.name = name
        self.priority = priority  # Lower number = higher priority
        self.enabled = enabled
        self.last_error = None
        self.consecutive_failures = 0
        self.max_failures = 3
    
    @abstractmethod
    async def fetch_news(self, target_date: datetime, impact_level: str = "high") -> List[Dict[str, Any]]:
        """Fetch news from this source."""
        pass
    
    @abstractmethod
    def is_available(self) -> bool:
        """Check if this source is available (has required config, etc.)."""
        pass
    
    def mark_success(self):
        """Mark this source as successful."""
        self.consecutive_failures = 0
        self.last_error = None
    
    def mark_failure(self, error: str):
        """Mark this source as failed."""
        self.consecutive_failures += 1
        self.last_error = error
        logger.warning(f"Source {self.name} failed: {error} (failures: {self.consecutive_failures})")
    
    def is_healthy(self) -> bool:
        """Check if source is healthy (not too many consecutive failures)."""
        return self.consecutive_failures < self.max_failures
    
    def should_use(self) -> bool:
        """Check if this source should be used."""
        return self.enabled and self.is_available() and self.is_healthy()


class SourceManager:
    """Manages multiple news sources with fallback logic."""
    
    def __init__(self):
        self.sources: List[NewsSource] = []
        self.last_successful_source = None
    
    def register_source(self, source: NewsSource):
        """Register a news source."""
        self.sources.append(source)
        # Sort by priority (lower number = higher priority)
        self.sources.sort(key=lambda s: s.priority)
        logger.info(f"Registered source: {source.name} (priority: {source.priority})")
    
    def get_available_sources(self) -> List[NewsSource]:
        """Get list of available sources."""
        return [source for source in self.sources if source.should_use()]
    
    async def fetch_news(self, target_date: datetime, impact_level: str = "high") -> List[Dict[str, Any]]:
        """Fetch news from sources with fallback logic."""
        available_sources = self.get_available_sources()
        
        if not available_sources:
            logger.error("No available news sources!")
            return []
        
        logger.info(f"Attempting to fetch news from {len(available_sources)} sources")
        
        # Try each source in priority order
        for source in available_sources:
            try:
                logger.info(f"Trying source: {source.name}")
                news_items = await source.fetch_news(target_date, impact_level)
                
                if news_items:
                    source.mark_success()
                    self.last_successful_source = source.name
                    logger.info(f"✅ Successfully fetched {len(news_items)} items from {source.name}")
                    return news_items
                else:
                    logger.warning(f"Source {source.name} returned no data")
                    
            except Exception as e:
                error_msg = f"Failed to fetch from {source.name}: {str(e)}"
                source.mark_failure(error_msg)
                logger.error(error_msg)
                continue
        
        logger.error("All news sources failed!")
        return []
    
    def get_source_status(self) -> Dict[str, Any]:
        """Get status of all sources."""
        status = {
            'total_sources': len(self.sources),
            'available_sources': len(self.get_available_sources()),
            'last_successful_source': self.last_successful_source,
            'sources': []
        }
        
        for source in self.sources:
            source_info = {
                'name': source.name,
                'priority': source.priority,
                'enabled': source.enabled,
                'available': source.is_available(),
                'healthy': source.is_healthy(),
                'consecutive_failures': source.consecutive_failures,
                'last_error': source.last_error
            }
            status['sources'].append(source_info)
        
        return status


# Global source manager instance
_source_manager = None

def get_source_manager() -> SourceManager:
    """Get the global source manager instance."""
    global _source_manager
    if _source_manager is None:
        _source_manager = SourceManager()
    return _source_manager
