#!/usr/bin/env python3
"""
Tests for multi-source forex news system.
"""
import pytest
import asyncio
import os
import sys
from datetime import datetime, timedelta
from unittest.mock import Mock, patch, AsyncMock

# Add the parent directory to the path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from bot.config import Config
from bot.sources import get_source_manager, SourceManager, NewsSource
from bot.sources.forex_factory import ForexFactorySource
from bot.sources.alpha_vantage import AlphaVantageSource
from bot.sources.fmp import FMPSource
from bot.sources.newsapi import NewsAPISource
from bot.sources.rss import RSSSource
from bot.multi_source_scraper import MultiSourceForexScraper
from bot.utils.normalizer import NewsNormalizer


class MockNewsSource(NewsSource):
    """Mock news source for testing."""
    
    def __init__(self, name: str, priority: int = 100, enabled: bool = True, should_fail: bool = False):
        super().__init__(name, priority, enabled)
        self.should_fail = should_fail
        self.fetch_count = 0
    
    async def fetch_news(self, target_date: datetime, impact_level: str = "high"):
        self.fetch_count += 1
        
        if self.should_fail:
            raise Exception(f"Mock failure from {self.name}")
        
        # Return mock news items
        return [
            {
                'source': self.name,
                'time': '10:30',
                'currency': 'USD',
                'event': f'Mock Event from {self.name}',
                'actual': 'N/A',
                'forecast': 'N/A',
                'previous': 'N/A',
                'impact': impact_level,
                'analysis': f'Mock analysis from {self.name}',
                'date': target_date.date(),
                'raw_data': {'mock': True}
            }
        ]
    
    def is_available(self) -> bool:
        return True


class TestSourceManager:
    """Test the SourceManager class."""
    
    def test_source_registration(self):
        """Test source registration and priority ordering."""
        manager = SourceManager()
        
        # Register sources with different priorities
        source1 = MockNewsSource("Source1", priority=3)
        source2 = MockNewsSource("Source2", priority=1)
        source3 = MockNewsSource("Source3", priority=2)
        
        manager.register_source(source1)
        manager.register_source(source2)
        manager.register_source(source3)
        
        # Check that sources are ordered by priority
        assert len(manager.sources) == 3
        assert manager.sources[0].name == "Source2"  # Priority 1
        assert manager.sources[1].name == "Source3"  # Priority 2
        assert manager.sources[2].name == "Source1"  # Priority 3
    
    def test_available_sources_filtering(self):
        """Test filtering of available sources."""
        manager = SourceManager()
        
        # Register sources with different availability
        available_source = MockNewsSource("Available", enabled=True)
        disabled_source = MockNewsSource("Disabled", enabled=False)
        unhealthy_source = MockNewsSource("Unhealthy", enabled=True)
        unhealthy_source.consecutive_failures = 5  # Make it unhealthy
        
        manager.register_source(available_source)
        manager.register_source(disabled_source)
        manager.register_source(unhealthy_source)
        
        available = manager.get_available_sources()
        assert len(available) == 1
        assert available[0].name == "Available"
    
    @pytest.mark.asyncio
    async def test_fallback_logic(self):
        """Test fallback logic when sources fail."""
        manager = SourceManager()
        
        # Register sources: first fails, second succeeds
        failing_source = MockNewsSource("Failing", priority=1, should_fail=True)
        working_source = MockNewsSource("Working", priority=2, should_fail=False)
        
        manager.register_source(failing_source)
        manager.register_source(working_source)
        
        target_date = datetime.now()
        news_items = await manager.fetch_news(target_date, "high")
        
        # Should get news from working source
        assert len(news_items) == 1
        assert news_items[0]['source'] == 'Working'
        
        # Check failure tracking
        assert failing_source.consecutive_failures == 1
        assert working_source.consecutive_failures == 0
    
    @pytest.mark.asyncio
    async def test_all_sources_fail(self):
        """Test behavior when all sources fail."""
        manager = SourceManager()
        
        # Register only failing sources
        failing_source1 = MockNewsSource("Failing1", priority=1, should_fail=True)
        failing_source2 = MockNewsSource("Failing2", priority=2, should_fail=True)
        
        manager.register_source(failing_source1)
        manager.register_source(failing_source2)
        
        target_date = datetime.now()
        news_items = await manager.fetch_news(target_date, "high")
        
        # Should return empty list
        assert len(news_items) == 0
        
        # Both sources should have failure counts
        assert failing_source1.consecutive_failures == 1
        assert failing_source2.consecutive_failures == 1


class TestNewsNormalizer:
    """Test the NewsNormalizer class."""
    
    def test_normalize_events(self):
        """Test event normalization."""
        raw_events = [
            {
                'source': 'TestSource',
                'time': '10:30',
                'currency': 'USD',
                'event': 'Test Event',
                'actual': '1.5%',
                'forecast': '1.2%',
                'previous': '1.0%',
                'impact': 'high',
                'analysis': 'Test analysis',
                'date': datetime.now().date(),
                'raw_data': {}
            }
        ]
        
        normalized = NewsNormalizer.normalize_events(raw_events)
        
        assert len(normalized) == 1
        event = normalized[0]
        assert event['source'] == 'TestSource'
        assert event['time'] == '10:30'
        assert event['currency'] == 'USD'
        assert event['impact'] == 'high'
    
    def test_deduplicate_events(self):
        """Test event deduplication."""
        events = [
            {
                'currency': 'USD',
                'event': 'Same Event',
                'date': datetime.now().date(),
                'source': 'Source1'
            },
            {
                'currency': 'USD',
                'event': 'Same Event',
                'date': datetime.now().date(),
                'source': 'Source2'
            },
            {
                'currency': 'EUR',
                'event': 'Different Event',
                'date': datetime.now().date(),
                'source': 'Source1'
            }
        ]
        
        unique_events = NewsNormalizer.deduplicate_events(events)
        
        # Should have 2 unique events (USD event deduplicated)
        assert len(unique_events) == 2
    
    def test_filter_by_impact(self):
        """Test filtering by impact level."""
        events = [
            {'impact': 'high', 'event': 'High Impact'},
            {'impact': 'medium', 'event': 'Medium Impact'},
            {'impact': 'low', 'event': 'Low Impact'}
        ]
        
        # Filter for high impact only
        high_impact = NewsNormalizer.filter_by_impact(events, "high")
        assert len(high_impact) == 1
        assert high_impact[0]['impact'] == 'high'
        
        # Filter for medium and above
        medium_and_above = NewsNormalizer.filter_by_impact(events, "medium")
        assert len(medium_and_above) == 2


class TestMultiSourceScraper:
    """Test the MultiSourceForexScraper class."""
    
    def test_initialization(self):
        """Test scraper initialization."""
        # Mock config
        config = Mock()
        config.news_sources = {
            'forex_factory': {'enabled': True, 'priority': 1},
            'alpha_vantage': {'enabled': False, 'priority': 2, 'api_key': None},
            'fmp': {'enabled': False, 'priority': 3, 'api_key': None},
            'newsapi': {'enabled': False, 'priority': 4, 'api_key': None},
            'rss': {'enabled': True, 'priority': 5}
        }
        config.openai_api_key = None
        
        with patch('bot.multi_source_scraper.ForexFactorySource') as mock_ff, \
             patch('bot.multi_source_scraper.RSSSource') as mock_rss:
            
            scraper = MultiSourceForexScraper(config)
            
            # Should initialize enabled sources
            mock_ff.assert_called_once()
            mock_rss.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_scrape_news_success(self):
        """Test successful news scraping."""
        config = Mock()
        config.news_sources = {
            'forex_factory': {'enabled': True, 'priority': 1},
            'alpha_vantage': {'enabled': False, 'priority': 2, 'api_key': None},
            'fmp': {'enabled': False, 'priority': 3, 'api_key': None},
            'newsapi': {'enabled': False, 'priority': 4, 'api_key': None},
            'rss': {'enabled': False, 'priority': 5}
        }
        config.openai_api_key = None
        config.timezone = "UTC"
        
        with patch('bot.multi_source_scraper.ForexFactorySource') as mock_ff_class:
            # Mock the ForexFactory source
            mock_ff_instance = Mock()
            mock_ff_class.return_value = mock_ff_instance
            
            scraper = MultiSourceForexScraper(config)
            
            # Mock the source manager to return test data
            mock_news = [
                {
                    'source': 'ForexFactory',
                    'time': '10:30',
                    'currency': 'USD',
                    'event': 'Test Event',
                    'actual': 'N/A',
                    'forecast': 'N/A',
                    'previous': 'N/A',
                    'impact': 'high',
                    'analysis': '',
                    'date': datetime.now().date(),
                    'raw_data': {}
                }
            ]
            
            with patch.object(scraper.source_manager, 'fetch_news', return_value=mock_news):
                target_date = datetime.now()
                result = await scraper.scrape_news(target_date, "high")
                
                assert len(result) == 1
                assert result[0]['source'] == 'ForexFactory'


class TestIndividualSources:
    """Test individual news sources."""
    
    def test_forex_factory_source(self):
        """Test ForexFactory source initialization."""
        config = Mock()
        analyzer = Mock()
        
        source = ForexFactorySource(config, analyzer)
        
        assert source.name == "ForexFactory"
        assert source.priority == 1
        assert source.is_available() == True
    
    def test_alpha_vantage_source(self):
        """Test Alpha Vantage source initialization."""
        # Test with API key
        source_with_key = AlphaVantageSource("test_key")
        assert source_with_key.name == "AlphaVantage"
        assert source_with_key.is_available() == True
        
        # Test without API key
        source_without_key = AlphaVantageSource()
        assert source_without_key.is_available() == False
    
    def test_fmp_source(self):
        """Test FMP source initialization."""
        # Test with API key
        source_with_key = FMPSource("test_key")
        assert source_with_key.name == "FinancialModelingPrep"
        assert source_with_key.is_available() == True
        
        # Test without API key
        source_without_key = FMPSource()
        assert source_without_key.is_available() == False
    
    def test_newsapi_source(self):
        """Test NewsAPI source initialization."""
        # Test with API key
        source_with_key = NewsAPISource("test_key")
        assert source_with_key.name == "NewsAPI"
        assert source_with_key.is_available() == True
        
        # Test without API key
        source_without_key = NewsAPISource()
        assert source_without_key.is_available() == False
    
    def test_rss_source(self):
        """Test RSS source initialization."""
        source = RSSSource()
        assert source.name == "RSS_Feeds"
        assert source.is_available() == True  # RSS is always available


def test_graceful_degradation():
    """Test graceful degradation when all sources fail."""
    # This test simulates the scenario where ForexFactory is blocked
    # and all other sources are unavailable or failing
    
    manager = SourceManager()
    
    # Simulate ForexFactory being blocked (403 error)
    ff_source = MockNewsSource("ForexFactory", priority=1, should_fail=True)
    ff_source.last_error = "Access forbidden (403) - likely blocked by Cloudflare"
    
    # Simulate other sources being unavailable (no API keys)
    unavailable_sources = [
        MockNewsSource("AlphaVantage", priority=2, enabled=False),
        MockNewsSource("FMP", priority=3, enabled=False),
        MockNewsSource("NewsAPI", priority=4, enabled=False)
    ]
    
    # RSS source available but returns no data
    rss_source = MockNewsSource("RSS", priority=5, enabled=True)
    
    manager.register_source(ff_source)
    for source in unavailable_sources:
        manager.register_source(source)
    manager.register_source(rss_source)
    
    # Only RSS should be available
    available = manager.get_available_sources()
    assert len(available) == 2  # ForexFactory (before failure) and RSS
    
    # Get status
    status = manager.get_source_status()
    assert status['total_sources'] == 5
    assert status['available_sources'] == 2


if __name__ == "__main__":
    # Run tests
    pytest.main([__file__, "-v"])
