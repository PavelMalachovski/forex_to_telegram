#!/usr/bin/env python3
"""Add notification columns to existing database."""

import os
import sys
from sqlalchemy import create_engine, text

# Add the bot directory to the path
sys.path.append(os.path.join(os.path.dirname(__file__), 'bot'))

from bot.config import Config

def add_notification_columns():
    """Add notification columns to the users table."""
    config = Config()
    database_url = config.get_database_url()

    if not database_url:
        print("❌ DATABASE_URL not configured. Please set the environment variable.")
        return False

    engine = create_engine(database_url)

    try:
        with engine.connect() as conn:
            # Check if columns already exist
            result = conn.execute(text("""
                SELECT column_name
                FROM information_schema.columns
                WHERE table_name = 'users'
                AND column_name IN ('notifications_enabled', 'notification_minutes', 'notification_impact_levels')
            """))

            existing_columns = [row[0] for row in result]
            print(f"Existing notification columns: {existing_columns}")

            # Add notifications_enabled column if it doesn't exist
            if 'notifications_enabled' not in existing_columns:
                conn.execute(text("""
                    ALTER TABLE users
                    ADD COLUMN notifications_enabled BOOLEAN DEFAULT FALSE
                """))
                print("✅ Added notifications_enabled column")
            else:
                print("ℹ️ notifications_enabled column already exists")

            # Add notification_minutes column if it doesn't exist
            if 'notification_minutes' not in existing_columns:
                conn.execute(text("""
                    ALTER TABLE users
                    ADD COLUMN notification_minutes INTEGER DEFAULT 30
                """))
                print("✅ Added notification_minutes column")
            else:
                print("ℹ️ notification_minutes column already exists")

            # Add notification_impact_levels column if it doesn't exist
            if 'notification_impact_levels' not in existing_columns:
                conn.execute(text("""
                    ALTER TABLE users
                    ADD COLUMN notification_impact_levels TEXT DEFAULT 'high'
                """))
                print("✅ Added notification_impact_levels column")
            else:
                print("ℹ️ notification_impact_levels column already exists")

            conn.commit()

            # Verify the columns were added
            result = conn.execute(text("""
                SELECT column_name, data_type, column_default
                FROM information_schema.columns
                WHERE table_name = 'users'
                AND column_name IN ('notifications_enabled', 'notification_minutes', 'notification_impact_levels')
                ORDER BY column_name
            """))

            print("\n📋 Notification columns in users table:")
            for row in result:
                print(f"  - {row[0]}: {row[1]} (default: {row[2]})")

            print("\n✅ Notification columns added successfully!")
            return True

    except Exception as e:
        print(f"❌ Error adding notification columns: {e}")
        return False

if __name__ == "__main__":
    print("🔔 Adding notification columns to database...")
    print("=" * 50)

    if add_notification_columns():
        print("\n🎉 Notification columns added successfully!")
        print("\n📝 Next steps:")
        print("1. Restart the bot application")
        print("2. Users can now use /settings to configure notifications")
        print("3. Notification scheduler will start automatically")
    else:
        print("\n❌ Failed to add notification columns!")
        sys.exit(1)
