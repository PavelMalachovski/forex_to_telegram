#!/usr/bin/env python3
"""Complete setup script with notification columns."""

import os
import sys
from datetime import datetime
from sqlalchemy import create_engine, text

# Add the bot directory to the path
sys.path.append(os.path.join(os.path.dirname(__file__), 'bot'))

from bot.config import Config
from bot.models import Base, DatabaseManager, ForexNews, User

def setup_database_with_notifications():
    """Setup database with notification columns included."""
    config = Config()
    database_url = config.get_database_url()

    if not database_url:
        print("❌ DATABASE_URL not configured. Please set the environment variable.")
        return False

    engine = create_engine(database_url)

    try:
        # First, create tables without notification columns
        print("🗄️ Creating base database tables...")
        Base.metadata.create_all(bind=engine)

        # Then add notification columns
        print("🔔 Adding notification columns...")
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

        # Now test the database with notification columns
        print("\n🧪 Testing database with notification columns...")
        db_manager = DatabaseManager(database_url)

        with db_manager.get_session() as session:
            # Test User operations with notification fields
            test_user = User(
                telegram_id=123456789,
                preferred_currencies="USD,EUR,GBP",
                impact_levels="high,medium",
                analysis_required=True,
                digest_time=datetime.strptime("08:00", "%H:%M").time(),
                notifications_enabled=False,
                notification_minutes=30,
                notification_impact_levels="high"
            )
            session.add(test_user)
            session.commit()

            # Verify user was created
            user = session.query(User).filter(User.telegram_id == 123456789).first()
            if user:
                print("✅ User creation test passed")
                print(f"  - Telegram ID: {user.telegram_id}")
                print(f"  - Currencies: {user.get_currencies_list()}")
                print(f"  - Impact levels: {user.get_impact_levels_list()}")
                print(f"  - Analysis required: {user.analysis_required}")
                print(f"  - Digest time: {user.digest_time}")
                print(f"  - Notifications enabled: {user.notifications_enabled}")
                print(f"  - Notification minutes: {user.notification_minutes}")
                print(f"  - Notification impacts: {user.get_notification_impact_levels_list()}")

                # Clean up test user
                session.delete(user)
                session.commit()
                print("✅ Test user cleaned up")
            else:
                print("❌ User creation test failed")
                return False

            # Test ForexNews operations
            test_news = ForexNews(
                date=datetime.now(),
                time="10:30",
                currency="USD",
                event="Test Event",
                actual="1.5",
                forecast="1.4",
                previous="1.3",
                impact_level="high"
            )
            session.add(test_news)
            session.commit()

            # Verify news was created
            news = session.query(ForexNews).filter(ForexNews.event == "Test Event").first()
            if news:
                print("✅ News creation test passed")
                print(f"  - Currency: {news.currency}")
                print(f"  - Event: {news.event}")
                print(f"  - Impact: {news.impact_level}")

                # Clean up test news
                session.delete(news)
                session.commit()
                print("✅ Test news cleaned up")
            else:
                print("❌ News creation test failed")
                return False

        print("\n✅ Database setup with notifications completed successfully!")
        return True

    except Exception as e:
        print(f"❌ Database setup failed: {e}")
        return False

if __name__ == "__main__":
    print("🚀 Setting up Forex News Bot database with notifications...")
    print("=" * 60)

    if setup_database_with_notifications():
        print("\n🎉 Database setup completed successfully!")
        print("\n📝 Next steps:")
        print("1. Start the bot application")
        print("2. Users can use /settings to configure preferences")
        print("3. Notification feature is fully enabled")
        print("4. Daily digest will be sent based on user preferences")
    else:
        print("\n❌ Database setup failed!")
        sys.exit(1)
