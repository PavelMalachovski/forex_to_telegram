#!/usr/bin/env python3
"""
Bulk import script for forex news data.
Usage: python bulk_import.py --start-date 2025-01-01 --end-date 2025-01-31 --impact-level high
"""

import argparse
import asyncio
import logging
from datetime import datetime, date, timedelta
from typing import List, Optional

from bot.config import Config
from bot.scraper import ForexNewsScraper, ChatGPTAnalyzer
from bot.database_service import ForexNewsService
from bot.utils import setup_logging

logger = logging.getLogger(__name__)


async def bulk_import_news(
    start_date: date,
    end_date: date,
    impact_level: str = "high",
    database_url: Optional[str] = None
) -> None:
    """
    Bulk import forex news for a date range.

    Args:
        start_date: Start date for import
        end_date: End date for import
        impact_level: Impact level filter (high, medium, low, all)
        database_url: Optional database URL override
    """
    try:
        # Initialize services
        config = Config()
        analyzer = ChatGPTAnalyzer(config.chatgpt_api_key)
        scraper = ForexNewsScraper(config, analyzer)
        db_service = ForexNewsService(database_url or config.get_database_url())

        # Check database health
        if not db_service.health_check():
            logger.error("Database health check failed. Exiting.")
            return

        current_date = start_date
        total_imported = 0
        total_skipped = 0

        logger.info(f"Starting bulk import from {start_date} to {end_date} with impact level: {impact_level}")

        while current_date <= end_date:
            try:
                logger.info(f"Processing date: {current_date}")

                # Check if data already exists
                if db_service.has_news_for_date(current_date, impact_level):
                    logger.info(f"Data already exists for {current_date}, skipping...")
                    total_skipped += 1
                    current_date += timedelta(days=1)
                    continue

                # Scrape news for the current date
                logger.info(f"Scraping news for {current_date}...")
                news_items = await scraper.scrape_news(
                    target_date=datetime.combine(current_date, datetime.min.time()),
                    debug=False
                )

                if news_items:
                    # Store in database
                    success = db_service.store_news_items(news_items, current_date, impact_level)
                    if success:
                        logger.info(f"Imported {len(news_items)} items for {current_date}")
                        total_imported += len(news_items)
                    else:
                        logger.error(f"Failed to store news items for {current_date}")
                else:
                    logger.info(f"No news found for {current_date}")

                # Add delay to avoid rate limiting
                await asyncio.sleep(2)

            except Exception as e:
                logger.error(f"Error importing {current_date}: {e}")

            current_date += timedelta(days=1)

        logger.info(f"Bulk import completed. Total imported: {total_imported}")

    except Exception as e:
        logger.error(f"Bulk import failed: {e}")


def parse_date(date_str: str) -> date:
    """Parse date string in YYYY-MM-DD format."""
    try:
        return datetime.strptime(date_str, "%Y-%m-%d").date()
    except ValueError:
        raise argparse.ArgumentTypeError(f"Invalid date format: {date_str}. Use YYYY-MM-DD")


def main():
    """Main function for command line interface."""
    parser = argparse.ArgumentParser(description="Bulk import forex news data")
    parser.add_argument(
        "--start-date",
        type=parse_date,
        required=True,
        help="Start date in YYYY-MM-DD format"
    )
    parser.add_argument(
        "--end-date",
        type=parse_date,
        required=True,
        help="End date in YYYY-MM-DD format"
    )
    parser.add_argument(
        "--impact-level",
        choices=["high", "medium", "low", "all"],
        default="high",
        help="Impact level filter (default: high)"
    )
    parser.add_argument(
        "--database-url",
        help="Database URL override"
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Show what would be imported without actually importing"
    )

    args = parser.parse_args()

    # Setup logging
    setup_logging()

    if args.dry_run:
        logger.info("DRY RUN MODE - No data will be imported")
        logger.info(f"Would import news from {args.start_date} to {args.end_date}")
        logger.info(f"Impact level: {args.impact_level}")
        return

    # Run the bulk import
    asyncio.run(bulk_import_news(
        start_date=args.start_date,
        end_date=args.end_date,
        impact_level=args.impact_level,
        database_url=args.database_url
    ))


if __name__ == "__main__":
    main()
