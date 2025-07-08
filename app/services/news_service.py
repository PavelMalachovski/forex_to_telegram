
"""News service for managing economic calendar events."""

from datetime import datetime, date, time, timedelta
from typing import List, Optional, Dict, Any, Union
from sqlalchemy.orm import Session
from sqlalchemy import and_, or_, desc, asc, func
from loguru import logger

from app.database.models import NewsEvent, Currency, ImpactLevel
from app.utils.text_utils import clean_text


class NewsService:
    """Service for managing news events and economic calendar data."""
    
    def __init__(self, db: Session):
        """
        Initialize the news service.
        
        Args:
            db: Database session
        """
        self.db = db
    
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
    ) -> NewsEvent:
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
            NewsEvent object
        """
        try:
            # Clean the event name
            event_name = clean_text(event_name)
            
            # Get currency and impact level IDs
            currency_id = None
            if currency_code:
                currency = self._get_or_create_currency(currency_code)
                currency_id = currency.id
            
            impact_level_id = None
            if impact_code:
                impact_level = self._get_or_create_impact_level(impact_code)
                impact_level_id = impact_level.id
            
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
                    currency_id=currency_id,
                    event_name=event_name,
                    impact_level_id=impact_level_id,
                    forecast=clean_text(forecast) if forecast else None,
                    previous=clean_text(previous) if previous else None,
                    actual=clean_text(actual) if actual else None,
                    source=source,
                    source_url=source_url,
                    is_active=True,
                    created_at=datetime.utcnow()
                )
                
                self.db.add(new_event)
                self.db.commit()
                logger.debug(f"Created new event: {event_name} on {event_date}")
                return new_event
                
        except Exception as e:
            self.db.rollback()
            logger.error(f"Error creating/updating event {event_name}: {e}")
            raise
    
    def get_events_by_date_range(
        self,
        start_date: date,
        end_date: date,
        currency_codes: Optional[List[str]] = None,
        impact_levels: Optional[List[str]] = None,
        limit: Optional[int] = None
    ) -> List[NewsEvent]:
        """
        Get events within a date range.
        
        Args:
            start_date: Start date
            end_date: End date
            currency_codes: List of currency codes to filter by
            impact_levels: List of impact levels to filter by
            limit: Maximum number of events to return
            
        Returns:
            List of NewsEvent objects
        """
        query = self.db.query(NewsEvent).filter(
            and_(
                NewsEvent.event_date >= start_date,
                NewsEvent.event_date <= end_date,
                NewsEvent.is_active == True
            )
        )
        
        # Filter by currencies
        if currency_codes:
            currency_ids = [
                c.id for c in self.db.query(Currency).filter(
                    Currency.code.in_(currency_codes)
                ).all()
            ]
            if currency_ids:
                query = query.filter(NewsEvent.currency_id.in_(currency_ids))
        
        # Filter by impact levels
        if impact_levels:
            impact_ids = [
                i.id for i in self.db.query(ImpactLevel).filter(
                    ImpactLevel.code.in_(impact_levels)
                ).all()
            ]
            if impact_ids:
                query = query.filter(NewsEvent.impact_level_id.in_(impact_ids))
        
        # Order by date and time
        query = query.order_by(NewsEvent.event_date, NewsEvent.event_time)
        
        # Apply limit
        if limit:
            query = query.limit(limit)
        
        return query.all()
    
    def get_today_events(
        self,
        currency_codes: Optional[List[str]] = None,
        impact_levels: Optional[List[str]] = None
    ) -> List[NewsEvent]:
        """
        Get today's events.
        
        Args:
            currency_codes: List of currency codes to filter by
            impact_levels: List of impact levels to filter by
            
        Returns:
            List of NewsEvent objects
        """
        today = date.today()
        return self.get_events_by_date_range(
            start_date=today,
            end_date=today,
            currency_codes=currency_codes,
            impact_levels=impact_levels
        )
    
    def get_upcoming_events(
        self,
        days_ahead: int = 7,
        currency_codes: Optional[List[str]] = None,
        impact_levels: Optional[List[str]] = None,
        limit: Optional[int] = None
    ) -> List[NewsEvent]:
        """
        Get upcoming events.
        
        Args:
            days_ahead: Number of days to look ahead
            currency_codes: List of currency codes to filter by
            impact_levels: List of impact levels to filter by
            limit: Maximum number of events to return
            
        Returns:
            List of NewsEvent objects
        """
        start_date = date.today()
        end_date = start_date + timedelta(days=days_ahead)
        
        return self.get_events_by_date_range(
            start_date=start_date,
            end_date=end_date,
            currency_codes=currency_codes,
            impact_levels=impact_levels,
            limit=limit
        )
    
    def get_events_by_currency(
        self,
        currency_code: str,
        start_date: Optional[date] = None,
        end_date: Optional[date] = None,
        limit: Optional[int] = None
    ) -> List[NewsEvent]:
        """
        Get events for a specific currency.
        
        Args:
            currency_code: Currency code
            start_date: Start date (defaults to today)
            end_date: End date (defaults to 30 days from start)
            limit: Maximum number of events to return
            
        Returns:
            List of NewsEvent objects
        """
        if start_date is None:
            start_date = date.today()
        
        if end_date is None:
            end_date = start_date + timedelta(days=30)
        
        return self.get_events_by_date_range(
            start_date=start_date,
            end_date=end_date,
            currency_codes=[currency_code],
            limit=limit
        )
    
    def get_high_impact_events(
        self,
        start_date: Optional[date] = None,
        end_date: Optional[date] = None,
        limit: Optional[int] = None
    ) -> List[NewsEvent]:
        """
        Get high impact events.
        
        Args:
            start_date: Start date (defaults to today)
            end_date: End date (defaults to 7 days from start)
            limit: Maximum number of events to return
            
        Returns:
            List of NewsEvent objects
        """
        if start_date is None:
            start_date = date.today()
        
        if end_date is None:
            end_date = start_date + timedelta(days=7)
        
        return self.get_events_by_date_range(
            start_date=start_date,
            end_date=end_date,
            impact_levels=['HIGH'],
            limit=limit
        )
    
    def get_events_grouped_by_date(
        self,
        start_date: date,
        end_date: date,
        currency_codes: Optional[List[str]] = None,
        impact_levels: Optional[List[str]] = None
    ) -> Dict[str, List[NewsEvent]]:
        """
        Get events grouped by date.
        
        Args:
            start_date: Start date
            end_date: End date
            currency_codes: List of currency codes to filter by
            impact_levels: List of impact levels to filter by
            
        Returns:
            Dictionary with date strings as keys and lists of events as values
        """
        events = self.get_events_by_date_range(
            start_date=start_date,
            end_date=end_date,
            currency_codes=currency_codes,
            impact_levels=impact_levels
        )
        
        grouped_events: Dict[str, List[NewsEvent]] = {}
        
        for event in events:
            date_key = event.event_date.strftime('%Y-%m-%d')
            if date_key not in grouped_events:
                grouped_events[date_key] = []
            grouped_events[date_key].append(event)
        
        return grouped_events
    
    def search_events(
        self,
        search_term: str,
        start_date: Optional[date] = None,
        end_date: Optional[date] = None,
        limit: Optional[int] = 50
    ) -> List[NewsEvent]:
        """
        Search events by name.
        
        Args:
            search_term: Term to search for in event names
            start_date: Start date (optional)
            end_date: End date (optional)
            limit: Maximum number of events to return
            
        Returns:
            List of NewsEvent objects
        """
        query = self.db.query(NewsEvent).filter(
            and_(
                NewsEvent.event_name.ilike(f'%{search_term}%'),
                NewsEvent.is_active == True
            )
        )
        
        if start_date:
            query = query.filter(NewsEvent.event_date >= start_date)
        
        if end_date:
            query = query.filter(NewsEvent.event_date <= end_date)
        
        query = query.order_by(desc(NewsEvent.event_date), NewsEvent.event_time)
        
        if limit:
            query = query.limit(limit)
        
        return query.all()
    
    def get_event_statistics(self) -> Dict[str, Any]:
        """
        Get statistics about events in the database.
        
        Returns:
            Dictionary with statistics
        """
        try:
            total_events = self.db.query(NewsEvent).filter(NewsEvent.is_active == True).count()
            
            today = date.today()
            today_events = self.db.query(NewsEvent).filter(
                and_(
                    NewsEvent.event_date == today,
                    NewsEvent.is_active == True
                )
            ).count()
            
            upcoming_events = self.db.query(NewsEvent).filter(
                and_(
                    NewsEvent.event_date > today,
                    NewsEvent.event_date <= today + timedelta(days=7),
                    NewsEvent.is_active == True
                )
            ).count()
            
            # Events by impact level
            impact_stats = {}
            for impact in self.db.query(ImpactLevel).all():
                count = self.db.query(NewsEvent).filter(
                    and_(
                        NewsEvent.impact_level_id == impact.id,
                        NewsEvent.is_active == True
                    )
                ).count()
                impact_stats[impact.code] = count
            
            # Events by currency
            currency_stats = {}
            for currency in self.db.query(Currency).all():
                count = self.db.query(NewsEvent).filter(
                    and_(
                        NewsEvent.currency_id == currency.id,
                        NewsEvent.is_active == True
                    )
                ).count()
                if count > 0:
                    currency_stats[currency.code] = count
            
            return {
                'total_events': total_events,
                'today_events': today_events,
                'upcoming_events': upcoming_events,
                'impact_distribution': impact_stats,
                'currency_distribution': currency_stats,
                'last_updated': datetime.utcnow().isoformat()
            }
            
        except Exception as e:
            logger.error(f"Error getting event statistics: {e}")
            return {}
    
    def _get_or_create_currency(self, currency_code: str) -> Currency:
        """Get or create a currency."""
        currency = self.db.query(Currency).filter(
            Currency.code == currency_code.upper()
        ).first()
        
        if not currency:
            currency = Currency(
                code=currency_code.upper(),
                name=currency_code.upper(),  # Will be updated later with proper names
                is_active=True,
                created_at=datetime.utcnow()
            )
            self.db.add(currency)
            self.db.commit()
            logger.info(f"Created new currency: {currency_code}")
        
        return currency
    
    def _get_or_create_impact_level(self, impact_code: str) -> ImpactLevel:
        """Get or create an impact level."""
        impact_level = self.db.query(ImpactLevel).filter(
            ImpactLevel.code == impact_code.upper()
        ).first()
        
        if not impact_level:
            # Default impact level configurations
            impact_configs = {
                'LOW': {'name': 'Low Impact', 'color': '#28a745', 'priority': 1},
                'MEDIUM': {'name': 'Medium Impact', 'color': '#ffc107', 'priority': 2},
                'HIGH': {'name': 'High Impact', 'color': '#dc3545', 'priority': 3}
            }
            
            config = impact_configs.get(impact_code.upper(), {
                'name': impact_code.title(),
                'color': '#6c757d',
                'priority': 0
            })
            
            impact_level = ImpactLevel(
                code=impact_code.upper(),
                name=config['name'],
                color=config['color'],
                priority=config['priority'],
                is_active=True,
                created_at=datetime.utcnow()
            )
            self.db.add(impact_level)
            self.db.commit()
            logger.info(f"Created new impact level: {impact_code}")
        
        return impact_level
    
    def delete_old_events(self, days_old: int = 90) -> int:
        """
        Delete events older than specified days.
        
        Args:
            days_old: Number of days old to consider for deletion
            
        Returns:
            Number of events deleted
        """
        try:
            cutoff_date = date.today() - timedelta(days=days_old)
            
            deleted_count = self.db.query(NewsEvent).filter(
                NewsEvent.event_date < cutoff_date
            ).delete()
            
            self.db.commit()
            logger.info(f"Deleted {deleted_count} old events (older than {days_old} days)")
            return deleted_count
            
        except Exception as e:
            self.db.rollback()
            logger.error(f"Error deleting old events: {e}")
            return 0
    
    def bulk_create_events(self, events_data: List[Dict[str, Any]]) -> int:
        """
        Bulk create events from a list of event data.
        
        Args:
            events_data: List of event dictionaries
            
        Returns:
            Number of events created
        """
        created_count = 0
        
        try:
            for event_data in events_data:
                try:
                    self.create_or_update_event(**event_data)
                    created_count += 1
                except Exception as e:
                    logger.error(f"Error creating event from data {event_data}: {e}")
                    continue
            
            logger.info(f"Bulk created {created_count} events")
            return created_count
            
        except Exception as e:
            logger.error(f"Error in bulk create events: {e}")
            return created_count
