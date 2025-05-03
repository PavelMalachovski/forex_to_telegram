

"""
News service for managing news events.
"""

from typing import List, Optional, Dict, Tuple
from datetime import date, datetime
from sqlalchemy.orm import Session, joinedload
from sqlalchemy import and_, or_

from app.database.models import NewsEvent, Currency, ImpactLevel, ScrapingLog
import logging

logger = logging.getLogger(__name__)

class NewsService:
    """Service for managing news events."""
    
    def __init__(self, db: Session):
        self.db = db
    
    def get_news_by_date_range(
        self, 
        start_date: date, 
        end_date: date, 
        impact_levels: Optional[List[str]] = None,
        currencies: Optional[List[str]] = None
    ) -> List[NewsEvent]:
        """
        Get news events by date range with optional filtering.
        
        Args:
            start_date: Start date for filtering
            end_date: End date for filtering
            impact_levels: List of impact level codes to filter by
            currencies: List of currency codes to filter by
            
        Returns:
            List of NewsEvent objects
        """
        query = self.db.query(NewsEvent).options(
            joinedload(NewsEvent.currency),
            joinedload(NewsEvent.impact_level)
        ).filter(
            NewsEvent.event_date.between(start_date, end_date)
        )
        
        if impact_levels:
            query = query.join(ImpactLevel).filter(
                ImpactLevel.code.in_(impact_levels)
            )
        
        if currencies:
            query = query.join(Currency).filter(
                Currency.code.in_(currencies)
            )
        
        return query.order_by(
            NewsEvent.event_date, 
            NewsEvent.event_time,
            NewsEvent.currency_id
        ).all()
    
    def get_news_by_date(
        self, 
        target_date: date, 
        impact_level: str = "HIGH"
    ) -> List[NewsEvent]:
        """
        Get news events for a specific date.
        
        Args:
            target_date: Date to get news for
            impact_level: Impact level filter ('HIGH', 'MEDIUM', etc.)
            
        Returns:
            List of NewsEvent objects
        """
        # ИСПРАВЛЕНИЕ 6: Исправить логику фильтрации "ALL" новостей
        if impact_level.upper() == "ALL":
            # Показать все новости за дату без фильтрации по уровню важности
            return self.get_news_by_date_range(
                start_date=target_date,
                end_date=target_date,
                impact_levels=None  # Не фильтровать по уровню важности
            )
        elif impact_level.upper() == "MEDIUM":
            # Include only MEDIUM impact events
            impact_levels = ["MEDIUM"]
        else:
            impact_levels = [impact_level.upper()]
        
        return self.get_news_by_date_range(
            start_date=target_date,
            end_date=target_date,
            impact_levels=impact_levels
        )
    
    def has_data_for_date(self, target_date: date) -> bool:
        """
        Check if data exists for the given date.
        
        Args:
            target_date: Date to check
            
        Returns:
            True if data exists, False otherwise
        """
        count = self.db.query(NewsEvent).filter(
            NewsEvent.event_date == target_date
        ).count()
        
        return count > 0
    
    async def get_or_scrape_news_by_date(
        self, 
        target_date: date, 
        impact_level: str = "HIGH"
    ) -> Tuple[List[NewsEvent], bool]:
        """
        Get news events for a specific date, triggering auto-scraping if needed.
        
        Args:
            target_date: Date to get news for
            impact_level: Impact level filter ('HIGH', 'MEDIUM', etc.)
            
        Returns:
            Tuple of (List of NewsEvent objects, was_scraped boolean)
        """
        # Check if data exists
        if self.has_data_for_date(target_date):
            events = self.get_news_by_date(target_date, impact_level)
            return events, False
        
        # Import here to avoid circular imports
        from app.services.auto_scraper_service import AutoScraperService
        
        # Data doesn't exist, use auto-scraper
        auto_scraper = AutoScraperService(self.db)
        
        # Determine impact levels for scraping
        if impact_level.upper() == "ALL":
            impact_levels = ["HIGH", "MEDIUM", "LOW"]
        elif impact_level.upper() == "MEDIUM":
            impact_levels = ["MEDIUM"]
        else:
            impact_levels = [impact_level.upper()]
        
        # Get or scrape events
        events = await auto_scraper.get_or_scrape_events(target_date, impact_levels)
        
        return events, True
    
    def group_events_by_time_and_currency(
        self, 
        events: List[NewsEvent]
    ) -> Dict[Tuple[str, str, str], List[NewsEvent]]:
        """
        Group events by date, time, and currency.
        
        Args:
            events: List of NewsEvent objects
            
        Returns:
            Dictionary with (date, time, currency) as key and list of events as value
        """
        grouped_events = {}
        
        for event in events:
            key = (
                event.event_date.strftime('%Y-%m-%d'),
                event.event_time.strftime('%H:%M'),
                event.currency.code
            )
            
            if key not in grouped_events:
                grouped_events[key] = []
            
            grouped_events[key].append(event)
        
        return grouped_events
    
    def create_or_update_event(
        self,
        event_date: date,
        event_time: str,
        currency_code: str,
        event_name: str,
        forecast: Optional[str] = None,
        previous_value: Optional[str] = None,
        actual_value: Optional[str] = None,
        impact_level_code: str = "LOW",
        analysis: Optional[str] = None,
        source_url: Optional[str] = None
    ) -> NewsEvent:
        """
        Create or update a news event.
        
        Args:
            event_date: Date of the event
            event_time: Time of the event (HH:MM format)
            currency_code: Currency code (e.g., 'USD')
            event_name: Name of the event
            forecast: Forecast value
            previous_value: Previous value
            actual_value: Actual value
            impact_level_code: Impact level code
            analysis: Analysis text
            source_url: Source URL
            
        Returns:
            NewsEvent object
        """
        # Get currency and impact level
        currency = self.db.query(Currency).filter(Currency.code == currency_code).first()
        if not currency:
            # Create currency if it doesn't exist
            currency = Currency(code=currency_code, name=currency_code)
            self.db.add(currency)
            self.db.flush()
        
        impact_level = self.db.query(ImpactLevel).filter(
            ImpactLevel.code == impact_level_code
        ).first()
        if not impact_level:
            # Create impact level if it doesn't exist
            impact_level = ImpactLevel(
                code=impact_level_code,
                name=impact_level_code.title(),
                priority=1
            )
            self.db.add(impact_level)
            self.db.flush()
        
        # Parse time
        time_obj = datetime.strptime(event_time, '%H:%M').time()
        
        # Check if event already exists
        existing_event = self.db.query(NewsEvent).filter(
            and_(
                NewsEvent.event_date == event_date,
                NewsEvent.event_time == time_obj,
                NewsEvent.currency_id == currency.id,
                NewsEvent.event_name == event_name
            )
        ).first()
        
        if existing_event:
            # Update existing event
            existing_event.forecast = forecast
            existing_event.previous_value = previous_value
            existing_event.actual_value = actual_value
            existing_event.impact_level_id = impact_level.id
            existing_event.analysis = analysis
            existing_event.source_url = source_url
            existing_event.updated_at = datetime.utcnow()
            
            return existing_event
        else:
            # Create new event
            new_event = NewsEvent(
                event_date=event_date,
                event_time=time_obj,
                currency_id=currency.id,
                impact_level_id=impact_level.id,
                event_name=event_name,
                forecast=forecast,
                previous_value=previous_value,
                actual_value=actual_value,
                analysis=analysis,
                source_url=source_url
            )
            
            self.db.add(new_event)
            self.db.flush()
            
            return new_event
    
    def log_scraping_session(
        self,
        start_date: date,
        end_date: date,
        events_scraped: int,
        events_updated: int,
        errors_count: int,
        duration_seconds: int,
        status: str,
        error_message: Optional[str] = None
    ) -> ScrapingLog:
        """
        Log a scraping session.
        
        Args:
            start_date: Start date of scraping
            end_date: End date of scraping
            events_scraped: Number of events scraped
            events_updated: Number of events updated
            errors_count: Number of errors encountered
            duration_seconds: Duration in seconds
            status: Status of scraping ('success', 'partial', 'failed')
            error_message: Error message if any
            
        Returns:
            ScrapingLog object
        """
        log_entry = ScrapingLog(
            start_date=start_date,
            end_date=end_date,
            events_scraped=events_scraped,
            events_updated=events_updated,
            errors_count=errors_count,
            duration_seconds=duration_seconds,
            status=status,
            error_message=error_message
        )
        
        self.db.add(log_entry)
        self.db.flush()
        
        return log_entry
