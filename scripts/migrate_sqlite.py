
#!/usr/bin/env python3
"""
Script to migrate data from SQLite to PostgreSQL.
"""

import os
import sys
import sqlite3
from datetime import datetime
from pathlib import Path

# Add parent directory to path to import app modules
sys.path.insert(0, str(Path(__file__).parent.parent))

from app.utils.logging_config import setup_logging
from app.database.connection import init_database, get_db
from app.database.models import Currency, ImpactLevel
from app.services import NewsService
import logging

# Setup logging
setup_logging()
logger = logging.getLogger(__name__)

def migrate_sqlite_data(sqlite_db_path: str):
    """
    Migrate data from SQLite database to PostgreSQL.
    
    Args:
        sqlite_db_path: Path to the SQLite database file
    """
    if not os.path.exists(sqlite_db_path):
        logger.error(f"SQLite database not found: {sqlite_db_path}")
        return False
    
    logger.info(f"Starting migration from {sqlite_db_path}")
    
    # Initialize PostgreSQL database
    try:
        init_database()
        logger.info("PostgreSQL database initialized")
    except Exception as e:
        logger.error(f"PostgreSQL initialization failed: {e}")
        return False
    
    # Connect to SQLite
    try:
        sqlite_conn = sqlite3.connect(sqlite_db_path)
        sqlite_cursor = sqlite_conn.cursor()
        logger.info("Connected to SQLite database")
    except Exception as e:
        logger.error(f"Failed to connect to SQLite: {e}")
        return False
    
    try:
        db = next(get_db())
        news_service = NewsService(db)
        
        # Get existing currencies from PostgreSQL
        existing_currencies = {curr.code: curr.id for curr in db.query(Currency).all()}
        
        # Migrate currencies
        logger.info("Migrating currencies...")
        sqlite_cursor.execute("SELECT DISTINCT currency FROM news WHERE currency IS NOT NULL AND currency != ''")
        currency_rows = sqlite_cursor.fetchall()
        
        for (currency_code,) in currency_rows:
            if currency_code not in existing_currencies:
                currency = Currency(code=currency_code, name=currency_code)
                db.add(currency)
                db.flush()
                existing_currencies[currency_code] = currency.id
                logger.info(f"Added currency: {currency_code}")
        
        db.commit()
        
        # Map old impact values to new ones
        impact_mapping = {
            'HIGH': 'HIGH',
            'MEDIUM': 'MEDIUM', 
            'LOW': 'LOW',
            'NON-ECONOMIC': 'NON_ECONOMIC',
            'N/A': 'LOW',
            '': 'LOW',
            None: 'LOW'
        }
        
        # Migrate news events
        logger.info("Migrating news events...")
        sqlite_cursor.execute("""
            SELECT date, time, currency, event, forecast, previous, actual, impact, analysis
            FROM news
            ORDER BY date, time
        """)
        
        migrated_count = 0
        error_count = 0
        
        for row in sqlite_cursor.fetchall():
            try:
                date_str, time_str, currency, event, forecast, previous, actual, impact, analysis = row
                
                # Skip if essential data is missing
                if not date_str or not time_str or not currency or not event:
                    logger.warning(f"Skipping row with missing essential data: {row}")
                    error_count += 1
                    continue
                
                # Parse date and time
                try:
                    event_date = datetime.strptime(date_str, '%Y-%m-%d').date()
                except ValueError:
                    logger.warning(f"Invalid date format: {date_str}")
                    error_count += 1
                    continue
                
                try:
                    # Handle various time formats
                    if ':' in time_str:
                        event_time = time_str
                    else:
                        logger.warning(f"Invalid time format: {time_str}")
                        error_count += 1
                        continue
                except ValueError:
                    logger.warning(f"Invalid time format: {time_str}")
                    error_count += 1
                    continue
                
                # Map impact level
                impact_code = impact_mapping.get(impact, 'LOW')
                
                # Clean up values
                forecast = forecast if forecast and forecast != 'N/A' else None
                previous = previous if previous and previous != 'N/A' else None
                actual = actual if actual and actual != 'N/A' else None
                analysis = analysis if analysis else None
                
                # Create or update event
                news_service.create_or_update_event(
                    event_date=event_date,
                    event_time=event_time,
                    currency_code=currency,
                    event_name=event,
                    forecast=forecast,
                    previous_value=previous,
                    actual_value=actual,
                    impact_level_code=impact_code,
                    analysis=analysis,
                    source_url=f"https://www.forexfactory.com/calendar?day={date_str}"
                )
                
                migrated_count += 1
                
                if migrated_count % 100 == 0:
                    logger.info(f"Migrated {migrated_count} events...")
                    db.commit()
                
            except Exception as e:
                logger.error(f"Error migrating row {row}: {e}")
                error_count += 1
        
        # Final commit
        db.commit()
        
        logger.info(f"Migration completed: {migrated_count} events migrated, {error_count} errors")
        
        return error_count == 0
        
    except Exception as e:
        logger.error(f"Migration failed: {e}")
        return False
    finally:
        sqlite_conn.close()
        db.close()

def main():
    """Main function."""
    import argparse
    
    parser = argparse.ArgumentParser(description='Migrate data from SQLite to PostgreSQL')
    parser.add_argument(
        'sqlite_path',
        help='Path to the SQLite database file'
    )
    parser.add_argument(
        '--dry-run',
        action='store_true',
        help='Perform a dry run without actually migrating data'
    )
    
    args = parser.parse_args()
    
    if args.dry_run:
        logger.info("DRY RUN MODE - No data will be migrated")
        # In dry run mode, we would just analyze the SQLite database
        if os.path.exists(args.sqlite_path):
            try:
                conn = sqlite3.connect(args.sqlite_path)
                cursor = conn.cursor()
                cursor.execute("SELECT COUNT(*) FROM news")
                count = cursor.fetchone()[0]
                logger.info(f"SQLite database contains {count} news events")
                conn.close()
            except Exception as e:
                logger.error(f"Error reading SQLite database: {e}")
        else:
            logger.error(f"SQLite database not found: {args.sqlite_path}")
        return
    
    # Run migration
    success = migrate_sqlite_data(args.sqlite_path)
    
    if success:
        logger.info("Migration completed successfully")
        sys.exit(0)
    else:
        logger.error("Migration completed with errors")
        sys.exit(1)

if __name__ == "__main__":
    main()
