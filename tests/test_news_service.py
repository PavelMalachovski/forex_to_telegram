
"""
Tests for the NewsService.
"""

import pytest
from datetime import date, time, datetime
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.database.models import Base, Currency, ImpactLevel, NewsEvent
from app.services.news_service import NewsService

@pytest.fixture
def db_session():
    """Create a test database session."""
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    SessionLocal = sessionmaker(bind=engine)
    session = SessionLocal()
    
    # Create test data
    currency = Currency(code="USD", name="US Dollar")
    impact = ImpactLevel(code="HIGH", name="High Impact", priority=3)
    session.add_all([currency, impact])
    session.commit()
    
    yield session
    session.close()

def test_create_event(db_session):
    """Test creating a news event."""
    news_service = NewsService(db_session)
    
    event = news_service.create_or_update_event(
        event_date=date(2025, 6, 15),
        event_time="14:30",
        currency_code="USD",
        event_name="Test Event",
        forecast="100",
        previous_value="95",
        impact_level_code="HIGH"
    )
    
    assert event.event_name == "Test Event"
    assert event.forecast == "100"
    assert event.previous_value == "95"
    assert event.currency.code == "USD"
    assert event.impact_level.code == "HIGH"

def test_get_news_by_date(db_session):
    """Test getting news by date."""
    news_service = NewsService(db_session)
    
    # Create test event
    news_service.create_or_update_event(
        event_date=date(2025, 6, 15),
        event_time="14:30",
        currency_code="USD",
        event_name="Test Event",
        impact_level_code="HIGH"
    )
    
    # Get news for the date
    events = news_service.get_news_by_date(date(2025, 6, 15), "HIGH")
    
    assert len(events) == 1
    assert events[0].event_name == "Test Event"

def test_get_news_by_date_range(db_session):
    """Test getting news by date range."""
    news_service = NewsService(db_session)
    
    # Create test events
    news_service.create_or_update_event(
        event_date=date(2025, 6, 15),
        event_time="14:30",
        currency_code="USD",
        event_name="Event 1",
        impact_level_code="HIGH"
    )
    
    news_service.create_or_update_event(
        event_date=date(2025, 6, 16),
        event_time="10:00",
        currency_code="USD",
        event_name="Event 2",
        impact_level_code="HIGH"
    )
    
    # Get news for the date range
    events = news_service.get_news_by_date_range(
        start_date=date(2025, 6, 15),
        end_date=date(2025, 6, 16),
        impact_levels=["HIGH"]
    )
    
    assert len(events) == 2
    assert events[0].event_name == "Event 1"
    assert events[1].event_name == "Event 2"
