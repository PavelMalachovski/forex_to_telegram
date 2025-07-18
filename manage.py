
#!/usr/bin/env python3
"""
Management script for forex telegram bot
Usage:
    python manage.py scrape --from 2025-07-18 --to 2025-07-20
    python manage.py scrape --from 2025-07-18  # scrape from date to today
"""

import argparse
import sys
from datetime import datetime, date, timedelta
import logging
from bot.scraper import scrape_and_send_forex_data
from bot.database import get_db_manager

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def parse_date(date_string):
    """Parse date string in format YYYY-MM-DD"""
    try:
        return datetime.strptime(date_string, '%Y-%m-%d').date()
    except ValueError:
        raise argparse.ArgumentTypeError(f"Invalid date format: {date_string}. Use YYYY-MM-DD")

def scrape_command(args):
    """Handle scrape command"""
    start_date = args.from_date
    end_date = args.to_date if args.to_date else date.today()
    
    if start_date > end_date:
        logger.error("Start date cannot be after end date")
        return 1
        
    logger.info(f"Scraping forex data from {start_date} to {end_date}")
    
    try:
        # Check if data already exists
        db_manager = get_db_manager()
        if db_manager.check_data_exists(start_date, end_date):
            logger.info(f"Data already exists for {start_date} to {end_date}")
            response = input("Do you want to scrape anyway? (y/N): ")
            if response.lower() != 'y':
                logger.info("Scraping cancelled")
                return 0
        
        # Scrape and send data
        scrape_and_send_forex_data(start_date, end_date)
        logger.info("Scraping completed successfully")
        return 0
        
    except Exception as e:
        logger.error(f"Error during scraping: {e}")
        return 1

def main():
    parser = argparse.ArgumentParser(description='Forex Telegram Bot Management')
    subparsers = parser.add_subparsers(dest='command', help='Available commands')
    
    # Scrape command
    scrape_parser = subparsers.add_parser('scrape', help='Scrape forex data')
    scrape_parser.add_argument('--from', dest='from_date', type=parse_date, required=True,
                              help='Start date (YYYY-MM-DD)')
    scrape_parser.add_argument('--to', dest='to_date', type=parse_date,
                              help='End date (YYYY-MM-DD), defaults to today')
    scrape_parser.set_defaults(func=scrape_command)
    
    if len(sys.argv) == 1:
        parser.print_help()
        return 1
        
    args = parser.parse_args()
    
    if hasattr(args, 'func'):
        return args.func(args)
    else:
        parser.print_help()
        return 1

if __name__ == '__main__':
    sys.exit(main())
