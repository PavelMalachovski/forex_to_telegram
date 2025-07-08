
"""
Service for loading forex data from external sources.
"""

import logging
from datetime import datetime, timedelta
from sqlalchemy.orm import Session

from app.services.news_service import NewsService
from app.scrapers.forex_factory_scraper import ForexFactoryScraper
from app.utils.timezone_utils import get_current_time

logger = logging.getLogger(__name__)

class DataLoaderService:
    """Service for loading forex data."""
    
    def __init__(self, db: Session):
        self.db = db
        self.news_service = NewsService(db)
        self.scraper = ForexFactoryScraper()
    
    def load_data_from_previous_day(self, days_ahead: int = 5) -> dict:
        """
        Load forex data starting from previous day for updating actual impact values.
        
        Args:
            days_ahead: Number of days ahead to load data for
            
        Returns:
            Dictionary with loading results
        """
        logger.info(f"Starting data loading from previous day for {days_ahead} days ahead")
        
        try:
            # Calculate date range: yesterday + days_ahead
            start_date = (get_current_time() - timedelta(days=1)).date()
            end_date = start_date + timedelta(days=days_ahead)
            
            logger.info(f"Loading data for date range: {start_date} to {end_date}")
            
            return self._load_data_for_range(start_date, end_date)
            
        except Exception as e:
            logger.error(f"Data loading from previous day failed: {e}")
            return {
                'status': 'failed',
                'events_loaded': 0,
                'errors_count': 1,
                'error_message': str(e)
            }
    
    def load_data_for_today(self) -> dict:
        """
        Load forex data for today only.
        
        Returns:
            Dictionary with loading results
        """
        logger.info("Starting data loading for today")
        
        try:
            today = get_current_time().date()
            return self._load_data_for_range(today, today)
            
        except Exception as e:
            logger.error(f"Data loading for today failed: {e}")
            return {
                'status': 'failed',
                'events_loaded': 0,
                'errors_count': 1,
                'error_message': str(e)
            }
    
    def _load_data_for_range(self, start_date, end_date) -> dict:
        """
        Load data for a specific date range.
        
        Args:
            start_date: Start date for loading
            end_date: End date for loading
            
        Returns:
            Dictionary with loading results
        """
        # Track loading metrics
        start_time = get_current_time()
        events_loaded = 0
        events_updated = 0
        errors_count = 0
        error_message = None
        
        try:
            # Scrape events for the date range
            scraped_events = self.scraper.scrape_date_range(start_date, end_date)
            
            # Process and save events
            for event_data in scraped_events:
                try:
                    # Convert time string to time object
                    event_time = None
                    if event_data['time']:
                        try:
                            event_time = datetime.strptime(event_data['time'], '%H:%M').time()
                        except ValueError:
                            logger.warning(f"Could not parse time: {event_data['time']}")
                    
                    self.news_service.create_or_update_event(
                        event_date=datetime.strptime(event_data['date'], '%Y-%m-%d').date(),
                        event_time=event_time,
                        currency_code=event_data['currency'],
                        event_name=event_data['event_name'],
                        forecast=event_data.get('forecast'),
                        previous_value=event_data.get('previous_value'),
                        actual_value=event_data.get('actual_value'),
                        impact_level_code=event_data.get('impact_level', 'LOW'),
                        analysis=event_data.get('analysis'),
                        source_url=event_data.get('source_url')
                    )
                    events_loaded += 1
                    
                except Exception as e:
                    logger.error(f"Error processing event: {e}")
                    errors_count += 1
            
            self.db.commit()
            
            # Determine status
            if errors_count == 0:
                status = "success"
            elif events_loaded > 0:
                status = "partial"
            else:
                status = "failed"
                error_message = f"No events loaded, {errors_count} errors"
            
        except Exception as e:
            logger.error(f"Data loading failed: {e}")
            status = "failed"
            error_message = str(e)
            errors_count += 1
        
        # Calculate duration
        duration_seconds = int((get_current_time() - start_time).total_seconds())
        
        # Log scraping session
        self.news_service.log_scraping_session(
            start_date=start_date,
            end_date=end_date,
            events_scraped=events_loaded,
            events_updated=events_updated,
            errors_count=errors_count,
            duration_seconds=duration_seconds,
            status=status,
            error_message=error_message
        )
        
        logger.info(f"Data loading completed: {status}, {events_loaded} events, {errors_count} errors, {duration_seconds}s")
        
        return {
            'status': status,
            'events_loaded': events_loaded,
            'errors_count': errors_count,
            'duration_seconds': duration_seconds,
            'start_date': start_date.isoformat(),
            'end_date': end_date.isoformat()
        }
