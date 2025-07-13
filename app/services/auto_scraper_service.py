
"""
Automatic scraper service for on-demand data fetching.
"""

import asyncio
import logging
import time
from datetime import date, datetime
from typing import List, Dict, Optional
from sqlalchemy.orm import Session

from app.scrapers.forex_factory_scraper import ForexFactoryScraper
from app.services.news_service import NewsService
from app.database.models import NewsEvent

logger = logging.getLogger(__name__)

class AutoScraperService:
    """Service for automatic scraping when data is missing."""
    
    def __init__(self, db: Session):
        self.db = db
        self.news_service = NewsService(db)
        self.scraper = ForexFactoryScraper()
    
    async def scrape_date_if_missing(self, target_date: date) -> Dict[str, any]:
        """
        Check if data exists for the given date, and scrape if missing.
        
        Args:
            target_date: Date to check and potentially scrape
            
        Returns:
            Dictionary with scraping results and status
        """
        logger.info(f"Checking data availability for {target_date}")
        
        try:
            # Check if data already exists
            existing_events = self.news_service.get_news_by_date_range(
                start_date=target_date,
                end_date=target_date
            )
            
            if existing_events:
                logger.info(f"Data already exists for {target_date}: {len(existing_events)} events")
                return {
                    'status': 'exists',
                    'events_count': len(existing_events),
                    'message': f'Data already available for {target_date.strftime("%Y-%m-%d")}',
                    'scraped': False,
                    'events': existing_events
                }
            
            # Data doesn't exist, start scraping
            logger.info(f"No data found for {target_date}, starting automatic scraping")
            
            # Start timing the scraping process
            start_time = time.time()
            
            # Test connection first
            if not self.scraper.test_connection():
                logger.error("Failed to connect to ForexFactory - scraping aborted")
                return {
                    'status': 'connection_error',
                    'events_count': 0,
                    'message': f'Unable to connect to ForexFactory for {target_date.strftime("%Y-%m-%d")}. Please try again later.',
                    'scraped': False,
                    'events': [],
                    'error': 'Connection failed'
                }
            
            # Run scraping in executor to avoid blocking
            loop = asyncio.get_event_loop()
            scraped_data = await loop.run_in_executor(
                None, 
                self._safe_scrape_single_date, 
                target_date
            )
            
            if scraped_data is None:
                logger.error(f"Scraping failed for {target_date} - returned None")
                return {
                    'status': 'scraping_error',
                    'events_count': 0,
                    'message': f'Scraping failed for {target_date.strftime("%Y-%m-%d")}. ForexFactory may be blocking requests.',
                    'scraped': False,
                    'events': [],
                    'error': 'Scraping returned None'
                }
            
            if not scraped_data:
                logger.warning(f"No data scraped for {target_date}")
                return {
                    'status': 'no_data',
                    'events_count': 0,
                    'message': f'No events found for {target_date.strftime("%Y-%m-%d")}',
                    'scraped': True,
                    'events': []
                }
            
            # Save scraped data to database
            duration_seconds = int(time.time() - start_time)
            saved_events = await self._save_scraped_data(scraped_data, duration_seconds)
            
            logger.info(f"Successfully scraped and saved {len(saved_events)} events for {target_date}")
            
            return {
                'status': 'scraped',
                'events_count': len(saved_events),
                'message': f'Successfully scraped {len(saved_events)} events for {target_date.strftime("%Y-%m-%d")}',
                'scraped': True,
                'events': saved_events
            }
            
        except Exception as e:
            logger.error(f"Error during automatic scraping for {target_date}: {e}")
            return {
                'status': 'error',
                'events_count': 0,
                'message': f'Error occurred while scraping data for {target_date.strftime("%Y-%m-%d")}: {str(e)}',
                'scraped': False,
                'events': [],
                'error': str(e)
            }
    
    def _safe_scrape_single_date(self, target_date: date) -> Optional[List[Dict]]:
        """
        Safely scrape a single date with proper error handling.
        
        Args:
            target_date: Date to scrape
            
        Returns:
            List of scraped events or None if failed
        """
        try:
            return self.scraper.scrape_single_date(target_date)
        except Exception as e:
            logger.error(f"Error in _safe_scrape_single_date for {target_date}: {e}")
            return None
    
    async def _save_scraped_data(self, scraped_data: List[Dict], duration_seconds: int) -> List[NewsEvent]:
        """
        Save scraped data to database.
        
        Args:
            scraped_data: List of scraped event dictionaries
            duration_seconds: Duration of the scraping process in seconds
            
        Returns:
            List of saved NewsEvent objects
        """
        saved_events = []
        
        try:
            for event_data in scraped_data:
                try:
                    # Parse date
                    event_date = datetime.strptime(event_data['date'], '%Y-%m-%d').date()
                    
                    # Convert time string to time object
                    event_time = None
                    if event_data['time']:
                        try:
                            event_time = datetime.strptime(event_data['time'], '%H:%M').time()
                        except ValueError:
                            logger.warning(f"Could not parse time: {event_data['time']}")
                    
                    # Create or update event
                    event = self.news_service.create_or_update_event(
                        event_date=event_date,
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
                    
                    saved_events.append(event)
                    
                except Exception as e:
                    logger.error(f"Error saving individual event: {e}")
                    continue
            
            # Commit all changes
            self.db.commit()
            
            # Log scraping session
            if saved_events:
                start_date = min(event.event_date for event in saved_events)
                end_date = max(event.event_date for event in saved_events)
                
                self.news_service.log_scraping_session(
                    start_date=start_date,
                    end_date=end_date,
                    events_scraped=len(saved_events),
                    events_updated=0,  # All are new in auto-scraping
                    errors_count=len(scraped_data) - len(saved_events),
                    duration_seconds=duration_seconds,
                    status='success'
                )
            
        except Exception as e:
            logger.error(f"Error saving scraped data: {e}")
            self.db.rollback()
            raise
        
        return saved_events
    
    def check_data_exists(self, target_date: date) -> bool:
        """
        Check if data exists for the given date.
        
        Args:
            target_date: Date to check
            
        Returns:
            True if data exists, False otherwise
        """
        existing_events = self.news_service.get_news_by_date_range(
            start_date=target_date,
            end_date=target_date
        )
        
        return len(existing_events) > 0
    
    async def get_or_scrape_events(
        self, 
        target_date: date, 
        impact_levels: Optional[List[str]] = None
    ) -> List[NewsEvent]:
        """
        Get events for a date, scraping if necessary.
        
        Args:
            target_date: Date to get events for
            impact_levels: List of impact levels to filter by
            
        Returns:
            List of NewsEvent objects
        """
        # First try to get existing data
        existing_events = self.news_service.get_news_by_date_range(
            start_date=target_date,
            end_date=target_date,
            impact_levels=impact_levels
        )
        
        if existing_events:
            return existing_events
        
        # No data exists, scrape it
        scrape_result = await self.scrape_date_if_missing(target_date)
        
        if scrape_result['status'] in ['scraped', 'exists']:
            # Get the events with proper filtering
            return self.news_service.get_news_by_date_range(
                start_date=target_date,
                end_date=target_date,
                impact_levels=impact_levels
            )
        
        # Return empty list if scraping failed
        return []
    
    async def scrape_date_range(self, start_date: date, end_date: date) -> int:
        """
        Scrape data for a date range.
        
        Args:
            start_date: Start date for scraping
            end_date: End date for scraping
            
        Returns:
            Number of events scraped and saved
        """
        logger.info(f"Starting date range scraping from {start_date} to {end_date}")
        
        total_scraped = 0
        current_date = start_date
        
        while current_date <= end_date:
            try:
                result = await self.scrape_date_if_missing(current_date)
                if result['status'] in ['scraped', 'exists']:
                    total_scraped += result['events_count']
                    logger.info(f"Processed {current_date}: {result['events_count']} events")
                else:
                    logger.warning(f"Failed to process {current_date}: {result.get('message', 'Unknown error')}")
                
                # Move to next date
                from datetime import timedelta
                current_date += timedelta(days=1)
                
                # Small delay to avoid overwhelming the source
                await asyncio.sleep(0.5)
                
            except Exception as e:
                logger.error(f"Error scraping {current_date}: {e}")
                from datetime import timedelta
                current_date += timedelta(days=1)
                continue
        
        logger.info(f"Completed date range scraping: {total_scraped} total events")
        return total_scraped
