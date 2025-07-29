#!/usr/bin/env python3
"""Setup script with timezone support."""

import os
import sys
from sqlalchemy import text
from bot.config import Config
from bot.database_service import ForexNewsService

def setup_with_timezone():
    """Setup database with timezone support."""
    try:
        config = Config()
        db_service = ForexNewsService(config.get_database_url())

        with db_service.db_manager.get_session() as session:
            # Check if timezone column exists
            result = session.execute(text("""
                SELECT column_name
                FROM information_schema.columns
                WHERE table_name = 'users'
                AND column_name = 'timezone'
            """))

            if result.fetchone():
                print("✅ Timezone column already exists")
            else:
                # Add timezone column
                session.execute(text("""
                    ALTER TABLE users
                    ADD COLUMN timezone VARCHAR(50) DEFAULT 'Europe/Prague'
                """))
                session.commit()
                print("✅ Timezone column added successfully")

            # Check notification columns
            result = session.execute(text("""
                SELECT column_name
                FROM information_schema.columns
                WHERE table_name = 'users'
                AND column_name IN ('notifications_enabled', 'notification_minutes', 'notification_impact_levels')
            """))
            notification_columns = [row[0] for row in result]

            if len(notification_columns) == 3:
                print("✅ All notification columns exist")
            else:
                print("⚠️ Some notification columns missing")
                # Add missing notification columns
                if 'notifications_enabled' not in notification_columns:
                    session.execute(text("""
                        ALTER TABLE users
                        ADD COLUMN notifications_enabled BOOLEAN DEFAULT FALSE
                    """))
                    print("✅ Added notifications_enabled column")

                if 'notification_minutes' not in notification_columns:
                    session.execute(text("""
                        ALTER TABLE users
                        ADD COLUMN notification_minutes INTEGER DEFAULT 30
                    """))
                    print("✅ Added notification_minutes column")

                if 'notification_impact_levels' not in notification_columns:
                    session.execute(text("""
                        ALTER TABLE users
                        ADD COLUMN notification_impact_levels TEXT DEFAULT 'high'
                    """))
                    print("✅ Added notification_impact_levels column")

                session.commit()

            print("✅ Database setup with timezone support completed")
            return True

    except Exception as e:
        print(f"❌ Error setting up database with timezone: {e}")
        return False

if __name__ == "__main__":
    success = setup_with_timezone()
    sys.exit(0 if success else 1)
