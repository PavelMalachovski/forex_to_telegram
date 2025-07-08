
"""News service for managing economic calendar events."""

from datetime import datetime, date, time, timedelta
from typing import List, Optional, Dict, Any, Union, Tuple
from sqlalchemy.orm import Session
from sqlalchemy import and_, or_, desc, asc, func
import logging

from app.database.models import NewsEvent, Currency, ImpactLevel
from app.utils.text_utils import clean_text

logger = logging.getLogger(__name__)

class NewsService:
    """Service for managing news events and economic calendar data."""
    
    def __init__(self, db: Session):
        """
        Initialize the news service.
        
        Args:
            db: Database session (can be None for fallback mode)
        """
        self.db = db
        self.fallback_mode = db is None
        
        if self.fallback_mode:
            logger.warning("NewsService initialized in fallback mode - database unavailable")
    
    def _get_or_create_currency(self, currency_code: str) -> Optional[Currency]:
        """Get or create currency with proper error handling."""
        if self.fallback_mode:
            return None
            
        try:
            currency = self.db.query(Currency).filter(Currency.code == currency_code).first()
            if not currency:
                currency = Currency(code=currency_code, name=currency_code)
                self.db.add(currency)
                self.db.commit()
            return currency
        except Exception as e:
            logger.error(f"Error getting or creating currency {currency_code}: {e}")
            return None
    
    def _get_or_create_impact_level(self, impact_code: str) -> Optional[ImpactLevel]:
        """Get or create impact level with proper error handling."""
        if self.fallback_mode:
            return None
            
        try:
            impact_level = self.db.query(ImpactLevel).filter(ImpactLevel.code == impact_code).first()
            if not impact_level:
                impact_level = ImpactLevel(code=impact_code, name=impact_code)
                self.db.add(impact_level)
                self.db.commit()
            return impact_level
        except Exception as e:
            logger.error(f"Error getting or creating impact level {impact_code}: {e}")
            return None
    
    def create_or_update_event(
        self,
        event_date: date,
        event_name: str,
        event_time: Optional[time] = None,
        currency_code: Optional[str] = None,
        impact_code: Optional[str] = None,
        forecast: Optional[str] = None,
        previous: Optional[str] = None,
        actual: Optional[str] = None,
        source: Optional[str] = None,
        source_url: Optional[str] = None
    ) -> Optional[NewsEvent]:
        """
        Create or update a news event.
        
        Args:
            event_date: Date of the event
            event_name: Name of the event
            event_time: Time of the event (optional)
            currency_code: Currency code (optional)
            impact_code: Impact level code (optional)
            forecast: Forecast value (optional)
            previous: Previous value (optional)
            actual: Actual value (optional)
            source: Source of the data (optional)
            source_url: Source URL (optional)
            
        Returns:
            NewsEvent object or None if failed
        """
        if self.fallback_mode:
            logger.warning("Cannot create event - database unavailable")
            return None
            
        try:
            # Clean the event name
            event_name = clean_text(event_name) if event_name else ""
            
            # Get currency and impact level IDs
            currency_id = None
            if currency_code:
                currency = self._get_or_create_currency(currency_code)
                currency_id = currency.id if currency else None
            
            impact_level_id = None
            if impact_code:
                impact_level = self._get_or_create_impact_level(impact_code)
                impact_level_id = impact_level.id if impact_level else None
            
            # Check if event already exists
            existing_event = self.db.query(NewsEvent).filter(
                and_(
                    NewsEvent.event_date == event_date,
                    NewsEvent.event_name == event_name,
                    NewsEvent.currency_id == currency_id,
                    NewsEvent.event_time == event_time
                )
            ).first()
            
            if existing_event:
                # Update existing event
                existing_event.impact_level_id = impact_level_id
                existing_event.forecast = clean_text(forecast) if forecast else None
                existing_event.previous = clean_text(previous) if previous else None
                existing_event.actual = clean_text(actual) if actual else None
                existing_event.source = source
                existing_event.source_url = source_url
                existing_event.updated_at = datetime.utcnow()
                
                self.db.commit()
                logger.debug(f"Updated existing event: {event_name} on {event_date}")
                return existing_event
            else:
                # Create new event
                new_event = NewsEvent(
                    event_date=event_date,
                    event_time=event_time,
                    event_name=event_name,
                    currency_id=currency_id,
                    impact_level_id=impact_level_id,
                    forecast=clean_text(forecast) if forecast else None,
                    previous=clean_text(previous) if previous else None,
                    actual=clean_text(actual) if actual else None,
                    source=source,
                    source_url=source_url,
                    scraped_at=datetime.utcnow()
                )
                
                self.db.add(new_event)
                self.db.commit()
                logger.debug(f"Created new event: {event_name} on {event_date}")
                return new_event
                
        except Exception as e:
            logger.error(f"Error creating or updating event: {e}")
            if self.db:
                self.db.rollback()
            return None
    
    def get_news_by_date(
        self,
        target_date: date,
        impact_levels: Optional[List[str]] = None,
        currencies: Optional[List[str]] = None
    ) -> List[NewsEvent]:
        """
        Get news events for a specific date.
        
        Args:
            target_date: Date to get news for
            impact_levels: List of impact levels to filter by (optional)
            currencies: List of currency codes to filter by (optional)
            
        Returns:
            List of NewsEvent objects
        """
        if self.fallback_mode:
            logger.warning("Cannot get news - database unavailable")
            return []
            
        try:
            query = self.db.query(NewsEvent).filter(NewsEvent.event_date == target_date)
            
            # Filter by impact levels if provided
            if impact_levels:
                impact_level_ids = []
                for level in impact_levels:
                    impact_level = self.db.query(ImpactLevel).filter(ImpactLevel.code == level).first()
                    if impact_level:
                        impact_level_ids.append(impact_level.id)
                
                if impact_level_ids:
                    query = query.filter(NewsEvent.impact_level_id.in_(impact_level_ids))
            
            # Filter by currencies if provided
            if currencies:
                currency_ids = []
                for currency in currencies:
                    currency_obj = self.db.query(Currency).filter(Currency.code == currency).first()
                    if currency_obj:
                        currency_ids.append(currency_obj.id)
                
                if currency_ids:
                    query = query.filter(NewsEvent.currency_id.in_(currency_ids))
            
            # Order by time
            events = query.order_by(NewsEvent.event_time.asc()).all()
            return events
            
        except Exception as e:
            logger.error(f"Error getting news by date: {e}")
            return []
    
    def get_news_by_date_range(
        self,
        start_date: date,
        end_date: date,
        impact_levels: Optional[List[str]] = None,
        currencies: Optional[List[str]] = None
    ) -> List[NewsEvent]:
        """Alias for backward compatibility."""
        return self.get_events_by_date_range(start_date, end_date, impact_levels, currencies)
    
    def get_events_by_date_range(
        self,
        start_date: date,
        end_date: date,
        impact_levels: Optional[List[str]] = None,
        currencies: Optional[List[str]] = None
    ) -> List[NewsEvent]:
        """
        Get news events for a date range.
        
        Args:
            start_date: Start date
            end_date: End date
            impact_levels: List of impact levels to filter by (optional)
            currencies: List of currency codes to filter by (optional)
            
        Returns:
            List of NewsEvent objects
        """
        if self.fallback_mode:
            logger.warning("Cannot get news - database unavailable")
            return []
            
        try:
            query = self.db.query(NewsEvent).filter(
                and_(
                    NewsEvent.event_date >= start_date,
                    NewsEvent.event_date <= end_date
                )
            )
            
            # Filter by impact levels if provided
            if impact_levels:
                impact_level_ids = []
                for level in impact_levels:
                    impact_level = self.db.query(ImpactLevel).filter(ImpactLevel.code == level).first()
                    if impact_level:
                        impact_level_ids.append(impact_level.id)
                
                if impact_level_ids:
                    query = query.filter(NewsEvent.impact_level_id.in_(impact_level_ids))
            
            # Filter by currencies if provided
            if currencies:
                currency_ids = []
                for currency in currencies:
                    currency_obj = self.db.query(Currency).filter(Currency.code == currency).first()
                    if currency_obj:
                        currency_ids.append(currency_obj.id)
                
                if currency_ids:
                    query = query.filter(NewsEvent.currency_id.in_(currency_ids))
            
            # Order by date and time
            events = query.order_by(NewsEvent.event_date.asc(), NewsEvent.event_time.asc()).all()
            return events
            
        except Exception as e:
            logger.error(f"Error getting news by date range: {e}")
            return []
    
    def has_data_for_date(self, target_date: date) -> bool:
        """
        Check if we have data for a specific date.
        
        Args:
            target_date: Date to check
            
        Returns:
            True if data exists, False otherwise
        """
        if self.fallback_mode:
            return False
            
        try:
            count = self.db.query(NewsEvent).filter(NewsEvent.event_date == target_date).count()
            return count > 0
        except Exception as e:
            logger.error(f"Error checking data for date: {e}")
            return False
    
    async def get_or_scrape_news_by_date(
        self,
        target_date: date,
        impact_level: str = "HIGH"
    ) -> Tuple[List[NewsEvent], bool]:
        """
        Get news for a date, scraping if necessary.
        
        Args:
            target_date: Date to get news for
            impact_level: Impact level filter
            
        Returns:
            Tuple of (news_events, was_scraped)
        """
        if self.fallback_mode:
            logger.warning("Cannot get or scrape news - database unavailable")
            return [], False
            
        try:
            # First try to get existing data
            if impact_level == "ALL":
                news_events = self.get_news_by_date(target_date)
            else:
                news_events = self.get_news_by_date(target_date, impact_levels=[impact_level])
            
            # If we have data, return it
            if news_events:
                return news_events, False
            
            # If no data, try to scrape
            try:
                from app.services.auto_scraper_service import AutoScraperService
                scraper_service = AutoScraperService(self.db)
                
                # Scrape data for the date
                scraped_count = await scraper_service.scrape_date_range(target_date, target_date)
                
                if scraped_count > 0:
                    # Get the newly scraped data
                    if impact_level == "ALL":
                        news_events = self.get_news_by_date(target_date)
                    else:
                        news_events = self.get_news_by_date(target_date, impact_levels=[impact_level])
                    
                    return news_events, True
                else:
                    return [], True  # Scraped but no data found
                    
            except ImportError:
                logger.warning("AutoScraperService not available")
                return [], False
            except Exception as e:
                logger.error(f"Error during scraping: {e}")
                return [], False
                
        except Exception as e:
            logger.error(f"Error in get_or_scrape_news_by_date: {e}")
            return [], False
    
    def get_upcoming_events(
        self,
        hours_ahead: int = 24,
        impact_levels: Optional[List[str]] = None
    ) -> List[NewsEvent]:
        """
        Get upcoming events within specified hours.
        
        Args:
            hours_ahead: Number of hours to look ahead
            impact_levels: List of impact levels to filter by
            
        Returns:
            List of upcoming NewsEvent objects
        """
        if self.fallback_mode:
            logger.warning("Cannot get upcoming events - database unavailable")
            return []
            
        try:
            now = datetime.utcnow()
            future_time = now + timedelta(hours=hours_ahead)
            
            query = self.db.query(NewsEvent).filter(
                or_(
                    and_(
                        NewsEvent.event_date == now.date(),
                        NewsEvent.event_time >= now.time()
                    ),
                    and_(
                        NewsEvent.event_date > now.date(),
                        NewsEvent.event_date <= future_time.date()
                    )
                )
            )
            
            # Filter by impact levels if provided
            if impact_levels:
                impact_level_ids = []
                for level in impact_levels:
                    impact_level = self.db.query(ImpactLevel).filter(ImpactLevel.code == level).first()
                    if impact_level:
                        impact_level_ids.append(impact_level.id)
                
                if impact_level_ids:
                    query = query.filter(NewsEvent.impact_level_id.in_(impact_level_ids))
            
            events = query.order_by(NewsEvent.event_date.asc(), NewsEvent.event_time.asc()).all()
            return events
            
        except Exception as e:
            logger.error(f"Error getting upcoming events: {e}")
            return []
    
    def get_event_statistics(self) -> Dict[str, Any]:
        """Alias for backward compatibility."""
        return self.get_statistics()
    
    def get_statistics(self) -> Dict[str, Any]:
        """
        Get statistics about news events.
        
        Returns:
            Dictionary with statistics
        """
        if self.fallback_mode:
            return {"error": "Database unavailable"}
            
        try:
            stats = {}
            
            # Total events
            stats['total_events'] = self.db.query(NewsEvent).count()
            
            # Events by impact level
            impact_stats = self.db.query(
                ImpactLevel.code,
                func.count(NewsEvent.id)
            ).join(NewsEvent).group_by(ImpactLevel.code).all()
            
            stats['by_impact_level'] = dict(impact_stats)
            
            # Events by currency
            currency_stats = self.db.query(
                Currency.code,
                func.count(NewsEvent.id)
            ).join(NewsEvent).group_by(Currency.code).all()
            
            stats['by_currency'] = dict(currency_stats)
            
            # Recent events
            recent_events = self.db.query(NewsEvent).order_by(
                NewsEvent.scraped_at.desc()
            ).limit(5).all()
            
            stats['recent_events'] = [
                {
                    'date': event.event_date.isoformat(),
                    'name': event.event_name,
                    'currency': event.currency.code if event.currency else None,
                    'impact': event.impact_level.code if event.impact_level else None
                }
                for event in recent_events
            ]
            
            return stats
            
        except Exception as e:
            logger.error(f"Error getting statistics: {e}")
            return {"error": str(e)}
