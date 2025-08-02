#!/usr/bin/env python3
"""Run chart settings migration to add missing columns to users table."""

import os
import sys
from sqlalchemy import create_engine, text

# Add the parent directory to the Python path so we can import from bot
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))

from bot.config import Config

def run_chart_migration():
    """Add chart generation settings to users table."""

    config = Config()
    database_url = config.get_database_url()

    if not database_url:
        print("❌ DATABASE_URL not configured. Please set the environment variable.")
        return False

    try:
        engine = create_engine(database_url)

        with engine.connect() as conn:
            # Check if chart columns already exist
            result = conn.execute(text("""
                SELECT column_name
                FROM information_schema.columns
                WHERE table_name = 'users'
                AND column_name IN ('charts_enabled', 'chart_type', 'chart_window_hours')
            """))

            existing_columns = [row[0] for row in result]

            # Add charts_enabled column if it doesn't exist
            if 'charts_enabled' not in existing_columns:
                conn.execute(text("""
                    ALTER TABLE users
                    ADD COLUMN charts_enabled BOOLEAN DEFAULT FALSE
                """))
                print("✅ Added charts_enabled column")
            else:
                print("✅ charts_enabled column already exists")

            # Add chart_type column if it doesn't exist
            if 'chart_type' not in existing_columns:
                conn.execute(text("""
                    ALTER TABLE users
                    ADD COLUMN chart_type VARCHAR(20) DEFAULT 'single'
                """))
                print("✅ Added chart_type column")
            else:
                print("✅ chart_type column already exists")

            # Add chart_window_hours column if it doesn't exist
            if 'chart_window_hours' not in existing_columns:
                conn.execute(text("""
                    ALTER TABLE users
                    ADD COLUMN chart_window_hours INTEGER DEFAULT 2
                """))
                print("✅ Added chart_window_hours column")
            else:
                print("✅ chart_window_hours column already exists")

            conn.commit()
            print("\n✅ Chart settings migration completed successfully!")
            return True

    except Exception as e:
        print(f"❌ Chart settings migration failed: {e}")
        return False

if __name__ == "__main__":
    success = run_chart_migration()
    sys.exit(0 if success else 1)
