#!/usr/bin/env python3
"""Add timezone column to users table."""

import os
import sys
from sqlalchemy import text
from bot.config import Config
from bot.database_service import ForexNewsService

def add_timezone_column():
    """Add timezone column to users table."""
    try:
        config = Config()
        db_service = ForexNewsService(config.get_database_url())

        with db_service.db_manager.get_session() as session:
            # Check if timezone column already exists
            result = session.execute(text("""
                SELECT column_name
                FROM information_schema.columns
                WHERE table_name = 'users'
                AND column_name = 'timezone'
            """))

            if result.fetchone():
                print("✅ Timezone column already exists")
                return True

            # Add timezone column
            session.execute(text("""
                ALTER TABLE users
                ADD COLUMN timezone VARCHAR(50) DEFAULT 'Europe/Prague'
            """))

            session.commit()
            print("✅ Timezone column added successfully")
            return True

    except Exception as e:
        print(f"❌ Error adding timezone column: {e}")
        return False

if __name__ == "__main__":
    success = add_timezone_column()
    sys.exit(0 if success else 1)
