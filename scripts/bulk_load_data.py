
#!/usr/bin/env python3
"""Bulk load data script for the Forex Bot application."""

import argparse
import sys
from datetime import datetime, date, timedelta
from pathlib import Path
from typing import Optional, List, Dict, Any
from loguru import logger
from tqdm import tqdm

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from app.database.connection import get_db
from app.services.news_service import NewsService
from app.scrapers.forex_factory_scraper import ForexFactoryScraper


def setup_logging(log_file: Optional[str] = None) -> None:
    """
    Setup logging configuration.
    
    Args:
        log_file: Optional log file path
    """
    logger.remove()  # Remove default handler
    
    # Console handler
    logger.add(
        sys.stdout,
        format="<green>{time:YYYY-MM-DD HH:mm:ss}</green> | <level>{level: <8}</level> | <cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> - <level>{message}</level>",
        level="INFO"
    )
    
    # File handler if specified
    if log_file:
        logger.add(
            log_file,
            format="{time:YYYY-MM-DD HH:mm:ss} | {level: <8} | {name}:{function}:{line} - {message}",
            level="DEBUG",
            rotation="10 MB",
            retention="7 days"
        )


def validate_date(date_string: str) -> date:
    """
    Validate and parse date string.
    
    Args:
        date_string: Date string in YYYY-MM-DD format
        
    Returns:
        Parsed date object
        
    Raises:
        ValueError: If date format is invalid
    """
    try:
        return datetime.strptime(date_string, '%Y-%m-%d').date()
    except ValueError:
        raise ValueError(f"Invalid date format: {date_string}. Expected YYYY-MM-DD")


def validate_currencies(currencies: List[str]) -> List[str]:
    """
    Validate currency codes.
    
    Args:
        currencies: List of currency codes
        
    Returns:
        List of validated currency codes
        
    Raises:
        ValueError: If any currency code is invalid
    """
    valid_currencies = {
        'USD', 'EUR', 'GBP', 'JPY', 'AUD', 'CAD', 'CHF', 'NZD',
        'CNY', 'SEK', 'NOK', 'DKK', 'PLN', 'CZK', 'HUF', 'TRY',
        'ZAR', 'MXN', 'BRL', 'RUB', 'INR', 'KRW', 'SGD', 'HKD'
    }
    
    validated = []
    for currency in currencies:
        currency_upper = currency.upper()
        if currency_upper not in valid_currencies:
            logger.warning(f"Unknown currency code: {currency_upper}")
        validated.append(currency_upper)
    
    return validated


def scrape_and_load_data(
    start_date: date,
    end_date: date,
    currencies: Optional[List[str]] = None,
    dry_run: bool = False,
    batch_size: int = 100
) -> Dict[str, Any]:
    """
    Scrape and load data from Forex Factory.
    
    Args:
        start_date: Start date for scraping
        end_date: End date for scraping
        currencies: List of currency codes to filter
        dry_run: If True, don't save to database
        batch_size: Number of events to process in each batch
        
    Returns:
        Dictionary with operation results
    """
    results = {
        'scraped_events': 0,
        'saved_events': 0,
        'errors': 0,
        'start_time': datetime.utcnow(),
        'end_time': None,
        'duration': None
    }
    
    try:
        # Initialize scraper
        logger.info("Initializing Forex Factory scraper...")
        scraper = ForexFactoryScraper()
        
        # Test connection
        if not scraper.test_connection():
            raise Exception("Failed to connect to Forex Factory")
        
        # Scrape events
        logger.info(f"Scraping events from {start_date} to {end_date}")
        if currencies:
            logger.info(f"Filtering for currencies: {', '.join(currencies)}")
        
        events = scraper.scrape_events(
            start_date=start_date,
            end_date=end_date,
            currencies=currencies
        )
        
        results['scraped_events'] = len(events)
        logger.info(f"Scraped {len(events)} events")
        
        if dry_run:
            logger.info("Dry run mode - not saving to database")
            return results
        
        # Save to database
        if events:
            logger.info("Saving events to database...")
            
            db = next(get_db())
            news_service = NewsService(db)
            
            # Process in batches with progress bar
            saved_count = 0
            error_count = 0
            
            with tqdm(total=len(events), desc="Saving events") as pbar:
                for i in range(0, len(events), batch_size):
                    batch = events[i:i + batch_size]
                    
                    for event_data in batch:
                        try:
                            # Convert date string to date object
                            event_date = datetime.strptime(event_data['date'], '%Y-%m-%d').date()
                            
                            # Convert time string to time object
                            event_time = None
                            if event_data.get('time'):
                                try:
                                    event_time = datetime.strptime(event_data['time'], '%H:%M').time()
                                except ValueError:
                                    logger.warning(f"Invalid time format: {event_data['time']}")
                            
                            # Create or update event
                            news_service.create_or_update_event(
                                event_date=event_date,
                                event_time=event_time,
                                currency_code=event_data.get('currency'),
                                event_name=event_data['event_name'],
                                impact_code=event_data.get('impact'),
                                forecast=event_data.get('forecast'),
                                previous=event_data.get('previous'),
                                actual=event_data.get('actual'),
                                source=event_data.get('source', 'forex_factory'),
                                source_url=event_data.get('source_url')
                            )
                            
                            saved_count += 1
                            
                        except Exception as e:
                            logger.error(f"Error saving event {event_data.get('event_name', 'Unknown')}: {e}")
                            error_count += 1
                        
                        pbar.update(1)
            
            results['saved_events'] = saved_count
            results['errors'] = error_count
            
            logger.info(f"Saved {saved_count} events, {error_count} errors")
        
        # Close scraper
        scraper.close()
        
    except Exception as e:
        logger.error(f"Error in scrape and load operation: {e}")
        results['errors'] += 1
        raise
    
    finally:
        results['end_time'] = datetime.utcnow()
        results['duration'] = (results['end_time'] - results['start_time']).total_seconds()
    
    return results


def main() -> int:
    """
    Main function.
    
    Returns:
        Exit code (0 for success, 1 for error)
    """
    parser = argparse.ArgumentParser(
        description="Bulk load economic calendar data from Forex Factory",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  %(prog)s --start-date 2025-01-01 --end-date 2025-01-31
  %(prog)s --start-date 2025-01-01 --end-date 2025-01-31 --currencies USD EUR GBP
  %(prog)s --start-date 2025-01-01 --end-date 2025-01-31 --dry-run
  %(prog)s --days-ahead 7 --currencies USD EUR
        """
    )
    
    # Date options
    date_group = parser.add_mutually_exclusive_group(required=True)
    date_group.add_argument(
        '--start-date',
        type=str,
        help='Start date in YYYY-MM-DD format'
    )
    date_group.add_argument(
        '--days-ahead',
        type=int,
        help='Number of days ahead from today to load'
    )
    
    parser.add_argument(
        '--end-date',
        type=str,
        help='End date in YYYY-MM-DD format (required with --start-date)'
    )
    
    parser.add_argument(
        '--currencies',
        nargs='+',
        help='Currency codes to filter (e.g., USD EUR GBP)'
    )
    
    parser.add_argument(
        '--dry-run',
        action='store_true',
        help='Scrape data but do not save to database'
    )
    
    parser.add_argument(
        '--batch-size',
        type=int,
        default=100,
        help='Number of events to process in each batch (default: 100)'
    )
    
    parser.add_argument(
        '--log-file',
        type=str,
        help='Log file path (optional)'
    )
    
    parser.add_argument(
        '--verbose',
        action='store_true',
        help='Enable verbose logging'
    )
    
    args = parser.parse_args()
    
    # Setup logging
    if not args.log_file:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        args.log_file = f"logs/bulk_load_{timestamp}.log"
    
    setup_logging(args.log_file)
    
    if args.verbose:
        logger.remove()
        logger.add(sys.stdout, level="DEBUG")
        if args.log_file:
            logger.add(args.log_file, level="DEBUG")
    
    try:
        # Determine date range
        if args.start_date:
            if not args.end_date:
                parser.error("--end-date is required when using --start-date")
            
            start_date = validate_date(args.start_date)
            end_date = validate_date(args.end_date)
            
            if start_date > end_date:
                parser.error("Start date must be before or equal to end date")
        
        else:  # args.days_ahead
            start_date = date.today()
            end_date = start_date + timedelta(days=args.days_ahead)
        
        # Validate currencies
        currencies = None
        if args.currencies:
            currencies = validate_currencies(args.currencies)
        
        # Validate batch size
        if args.batch_size <= 0:
            parser.error("Batch size must be positive")
        
        logger.info("Starting bulk load operation")
        logger.info(f"Date range: {start_date} to {end_date}")
        logger.info(f"Currencies: {currencies or 'All'}")
        logger.info(f"Dry run: {args.dry_run}")
        logger.info(f"Batch size: {args.batch_size}")
        
        # Run the operation
        results = scrape_and_load_data(
            start_date=start_date,
            end_date=end_date,
            currencies=currencies,
            dry_run=args.dry_run,
            batch_size=args.batch_size
        )
        
        # Print results
        logger.info("=== BULK LOAD RESULTS ===")
        logger.info(f"Scraped events: {results['scraped_events']}")
        logger.info(f"Saved events: {results['saved_events']}")
        logger.info(f"Errors: {results['errors']}")
        logger.info(f"Duration: {results['duration']:.2f} seconds")
        
        if results['errors'] > 0:
            logger.warning(f"Operation completed with {results['errors']} errors")
            return 1
        else:
            logger.success("Operation completed successfully")
            return 0
    
    except KeyboardInterrupt:
        logger.warning("Operation cancelled by user")
        return 1
    
    except Exception as e:
        logger.error(f"Operation failed: {e}")
        return 1


if __name__ == '__main__':
    sys.exit(main())
