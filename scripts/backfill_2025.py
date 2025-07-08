
#!/usr/bin/env python3
"""
Script to backfill forex news data starting from January 1, 2025.
"""

import sys
from datetime import date, datetime, timedelta
from pathlib import Path

# Add parent directory to path to import app modules
sys.path.insert(0, str(Path(__file__).parent.parent))

from app.utils.logging_config import setup_logging
from app.database.connection import init_database, get_db
from app.scrapers import ForexFactoryScraper
from app.services import NewsService
import logging

# Setup logging
setup_logging()
logger = logging.getLogger(__name__)

def backfill_data(start_date: date, end_date: date = None):
    """
    Backfill forex news data for the specified date range.
    
    Args:
        start_date: Start date for backfilling
        end_date: End date for backfilling (defaults to today)
    """
    if end_date is None:
        end_date = date.today()
    
    logger.info(f"Starting backfill from {start_date} to {end_date}")
    
    # Initialize database
    try:
        init_database()
        logger.info("Database initialized")
    except Exception as e:
        logger.error(f"Database initialization failed: {e}")
        return False
    
    # Initialize scraper
    scraper = ForexFactoryScraper()
    
    # Process data in chunks to avoid overwhelming the server
    chunk_size = 7  # Process 7 days at a time
    current_start = start_date
    total_events = 0
    total_errors = 0
    
    while current_start <= end_date:
        current_end = min(current_start + timedelta(days=chunk_size - 1), end_date)
        
        logger.info(f"Processing chunk: {current_start} to {current_end}")
        
        try:
            db = next(get_db())
            news_service = NewsService(db)
            
            # Scrape events for this chunk
            scraped_events = scraper.scrape_date_range(current_start, current_end)
            
            chunk_events = 0
            chunk_errors = 0
            
            # Process and save events
            for event_data in scraped_events:
                try:
                    news_service.create_or_update_event(
                        event_date=datetime.strptime(event_data['date'], '%Y-%m-%d').date(),
                        event_time=event_data['time'],
                        currency_code=event_data['currency'],
                        event_name=event_data['event_name'],
                        forecast=event_data.get('forecast'),
                        previous_value=event_data.get('previous_value'),
                        actual_value=event_data.get('actual_value'),
                        impact_level_code=event_data.get('impact_level', 'LOW'),
                        analysis=event_data.get('analysis'),
                        source_url=event_data.get('source_url')
                    )
                    chunk_events += 1
                    
                except Exception as e:
                    logger.error(f"Error processing event: {e}")
                    chunk_errors += 1
            
            # Commit chunk
            db.commit()
            
            # Log chunk results
            news_service.log_scraping_session(
                start_date=current_start,
                end_date=current_end,
                events_scraped=chunk_events,
                errors_count=chunk_errors,
                status="success" if chunk_errors == 0 else ("partial" if chunk_events > 0 else "failed")
            )
            
            total_events += chunk_events
            total_errors += chunk_errors
            
            logger.info(f"Chunk completed: {chunk_events} events, {chunk_errors} errors")
            
        except Exception as e:
            logger.error(f"Chunk processing failed: {e}")
            total_errors += 1
        finally:
            db.close()
        
        # Move to next chunk
        current_start = current_end + timedelta(days=1)
        
        # Add delay between chunks to be respectful to the server
        import time
        time.sleep(5)
    
    logger.info(f"Backfill completed: {total_events} total events, {total_errors} total errors")
    return total_errors == 0

def main():
    """Main function."""
    import argparse
    
    parser = argparse.ArgumentParser(description='Backfill forex news data')
    parser.add_argument(
        '--start-date',
        type=str,
        default='2025-01-01',
        help='Start date for backfilling (YYYY-MM-DD format, default: 2025-01-01)'
    )
    parser.add_argument(
        '--end-date',
        type=str,
        help='End date for backfilling (YYYY-MM-DD format, default: today)'
    )
    parser.add_argument(
        '--dry-run',
        action='store_true',
        help='Perform a dry run without actually saving data'
    )
    
    args = parser.parse_args()
    
    # Parse dates
    try:
        start_date = datetime.strptime(args.start_date, '%Y-%m-%d').date()
        end_date = datetime.strptime(args.end_date, '%Y-%m-%d').date() if args.end_date else None
    except ValueError as e:
        logger.error(f"Invalid date format: {e}")
        sys.exit(1)
    
    # Validate date range
    if end_date and start_date > end_date:
        logger.error("Start date must be before or equal to end date")
        sys.exit(1)
    
    if args.dry_run:
        logger.info("DRY RUN MODE - No data will be saved")
        # In dry run mode, we would just log what would be done
        logger.info(f"Would backfill data from {start_date} to {end_date or date.today()}")
        return
    
    # Run backfill
    success = backfill_data(start_date, end_date)
    
    if success:
        logger.info("Backfill completed successfully")
        sys.exit(0)
    else:
        logger.error("Backfill completed with errors")
        sys.exit(1)

if __name__ == "__main__":
    main()
