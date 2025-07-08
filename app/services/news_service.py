
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
            db: Database session (can be None for fallback mode)
        """
        self.db = db
        self.fallback_mode = db is None
        
        if self.fallback_mode:
            logger.warning("NewsService initialized in fallback mode - database unavailable")
    
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
        if self.fallback_mode:
            logger.warning("Database unavailable - cannot get events by date range")
            return []
            
        try:
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
            
        except Exception as e:
            logger.error(f"Error getting events by date range: {e}")
            return []
    
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
        if self.fallback_mode:
            logger.warning("Database unavailable - cannot search events")
            return []
            
        try:
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
            
        except Exception as e:
            logger.error(f"Error searching events with term '{search_term}': {e}")
            return []
    
    def get_event_statistics(self) -> Dict[str, Any]:
        """
        Get statistics about events in the database.
        
        Returns:
            Dictionary with statistics
        """
        if self.fallback_mode:
            logger.warning("Database unavailable - cannot get event statistics")
            return {
                'total_events': 0,
                'today_events': 0,
                'upcoming_events': 0,
                'impact_distribution': {},
                'currency_distribution': {},
                'last_updated': datetime.utcnow().isoformat(),
                'status': 'database_unavailable'
            }
            
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
                'last_updated': datetime.utcnow().isoformat(),
                'status': 'success'
            }
            
        except Exception as e:
            logger.error(f"Error getting event statistics: {e}")
            return {
                'total_events': 0,
                'today_events': 0,
                'upcoming_events': 0,
                'impact_distribution': {},
                'currency_distribution': {},
                'last_updated': datetime.utcnow().isoformat(),
                'status': 'error',
                'error_message': str(e)
            }
    
    def _get_or_create_currency(self, currency_code: str) -> Currency:
        """Get or create a currency."""
        try:
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
            
        except Exception as e:
            logger.error(f"Error getting or creating currency {currency_code}: {e}")
            self.db.rollback()
            raise
    
    def _get_or_create_impact_level(self, impact_code: str) -> ImpactLevel:
        """Get or create an impact level."""
        try:
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
            
        except Exception as e:
            logger.error(f"Error getting or creating impact level {impact_code}: {e}")
            self.db.rollback()
            raise
    
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
    
    def has_data_for_date(self, target_date: date) -> bool:
        """
        Check if we have data for a specific date.
        
        Args:
            target_date: Date to check for data
            
        Returns:
            True if data exists for the date, False otherwise
        """
        if self.fallback_mode:
            logger.warning("Database unavailable - cannot check data for date")
            return False
            
        try:
            count = self.db.query(NewsEvent).filter(
                and_(
                    NewsEvent.event_date == target_date,
                    NewsEvent.is_active == True
                )
            ).count()
            
            return count > 0
            
        except Exception as e:
            logger.error(f"Error checking data for date {target_date}: {e}")
            return False
    
    async def get_or_scrape_news_by_date(self, target_date: date, impact_level: str = "HIGH"):
        """
        Get news for a specific date, scraping if necessary.
        
        Args:
            target_date: Date to get news for
            impact_level: Impact level filter
            
        Returns:
            Tuple of (news_events, was_scraped)
        """
        if self.fallback_mode:
            logger.warning("Database unavailable - cannot get or scrape news")
            return [], False
            
        try:
            # First try to get existing data
            existing_events = self.get_events_by_date_range(
                start_date=target_date,
                end_date=target_date,
                impact_levels=[impact_level] if impact_level != "ALL" else None
            )
            
            if existing_events:
                return existing_events, False
            
            # If no data exists, try to scrape
            logger.info(f"No data found for {target_date}, attempting to scrape...")
            
            # Import scraping service
            try:
                from app.services.scraping_service import ScrapingService
                scraping_service = ScrapingService(self.db)
                
                # Scrape data for the date
                scraped_events = await scraping_service.scrape_news_for_date(target_date)
                
                if scraped_events:
                    # Get the filtered events after scraping
                    filtered_events = self.get_events_by_date_range(
                        start_date=target_date,
                        end_date=target_date,
                        impact_levels=[impact_level] if impact_level != "ALL" else None
                    )
                    return filtered_events, True
                else:
                    return [], True
                    
            except ImportError:
                logger.warning("ScrapingService not available")
                return [], False
            except Exception as scrape_error:
                logger.error(f"Error during scraping: {scrape_error}")
                return [], False
                
        except Exception as e:
            logger.error(f"Error in get_or_scrape_news_by_date: {e}")
            return [], False
    
    def get_news_by_date_range(self, start_date: date, end_date: date, impact_levels: list = None):
        """
        Get news events by date range (alias for get_events_by_date_range).
        
        Args:
            start_date: Start date
            end_date: End date
            impact_levels: List of impact levels to filter by
            
        Returns:
            List of NewsEvent objects
        """
        return self.get_events_by_date_range(
            start_date=start_date,
            end_date=end_date,
            impact_levels=impact_levels
        )
    
    def get_news_by_date(self, target_date: date, impact_levels: list = None):
        """
        Get news events for a specific date.
        
        Args:
            target_date: Date to get news for
            impact_levels: List of impact levels to filter by
            
        Returns:
            List of NewsEvent objects
        """
        return self.get_events_by_date_range(
            start_date=target_date,
            end_date=target_date,
            impact_levels=impact_levels
        )
