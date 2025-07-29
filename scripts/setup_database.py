#!/usr/bin/env python3
"""Database setup script for Forex News Bot."""

import os
import sys
from datetime import datetime
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker

# Add the parent directory to the Python path so we can import from bot
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))

from bot.models import Base, DatabaseManager, ForexNews, User
from bot.config import Config

def setup_database():
    """Setup the database with all required tables."""
    config = Config()

    # Get database URL
    database_url = config.get_database_url()
    if not database_url:
        print("❌ DATABASE_URL not configured. Please set the environment variable.")
        return False

    try:
        # Create database manager
        db_manager = DatabaseManager(database_url)

        # Create all tables
        print("🗄️ Creating database tables...")
        Base.metadata.create_all(bind=db_manager.engine)

        # Verify tables were created
        with db_manager.get_session() as session:
            # Check if forex_news table exists
            result = session.execute(text("""
                SELECT table_name
                FROM information_schema.tables
                WHERE table_schema = 'public'
                AND table_name IN ('forex_news', 'users')
            """))
            tables = [row[0] for row in result]

            if 'forex_news' in tables:
                print("✅ forex_news table created successfully")
            else:
                print("❌ forex_news table not found")

            if 'users' in tables:
                print("✅ users table created successfully")
            else:
                print("❌ users table not found")

            # Check table structures
            print("\n📋 Table structures:")

            # Check forex_news table structure
            result = session.execute(text("""
                SELECT column_name, data_type, is_nullable
                FROM information_schema.columns
                WHERE table_name = 'forex_news'
                ORDER BY ordinal_position
            """))
            print("forex_news table columns:")
            for row in result:
                nullable = "NULL" if row[2] == "YES" else "NOT NULL"
                print(f"  - {row[0]}: {row[1]} ({nullable})")

            # Check users table structure
            result = session.execute(text("""
                SELECT column_name, data_type, is_nullable
                FROM information_schema.columns
                WHERE table_name = 'users'
                ORDER BY ordinal_position
            """))
            print("\nusers table columns:")
            for row in result:
                nullable = "NULL" if row[2] == "YES" else "NOT NULL"
                print(f"  - {row[0]}: {row[1]} ({nullable})")

            # Check indexes
            print("\n🔍 Indexes:")
            result = session.execute(text("""
                SELECT indexname, tablename, indexdef
                FROM pg_indexes
                WHERE tablename IN ('forex_news', 'users')
                ORDER BY tablename, indexname
            """))
            for row in result:
                print(f"  - {row[0]} on {row[1]}")

        print("\n✅ Database setup completed successfully!")
        return True

    except Exception as e:
        print(f"❌ Database setup failed: {e}")
        return False

def test_database_connection():
    """Test database connection and basic operations."""
    config = Config()
    database_url = config.get_database_url()

    if not database_url:
        print("❌ DATABASE_URL not configured")
        return False

    try:
        db_manager = DatabaseManager(database_url)

        # Test basic operations
        with db_manager.get_session() as session:
            # Check if notification columns exist
            result = session.execute(text("""
                SELECT column_name
                FROM information_schema.columns
                WHERE table_name = 'users'
                AND column_name IN ('notifications_enabled', 'notification_minutes', 'notification_impact_levels')
            """))
            notification_columns = [row[0] for row in result]

            print(f"Available notification columns: {notification_columns}")

            # Create a minimal user without notification fields
            test_user_data = {
                'telegram_id': 123456789,
                'preferred_currencies': "USD,EUR,GBP",
                'impact_levels': "high,medium",
                'analysis_required': True,
                'digest_time': datetime.strptime("08:00", "%H:%M").time()
            }

            # Only add notification fields if columns exist
            if 'notifications_enabled' in notification_columns:
                test_user_data['notifications_enabled'] = False
            if 'notification_minutes' in notification_columns:
                test_user_data['notification_minutes'] = 30
            if 'notification_impact_levels' in notification_columns:
                test_user_data['notification_impact_levels'] = 'high'

            # Create user using raw SQL to avoid SQLAlchemy column issues
            columns = ', '.join(test_user_data.keys())
            placeholders = ', '.join([f':{key}' for key in test_user_data.keys()])

            insert_sql = f"""
                INSERT INTO users ({columns}, created_at, updated_at)
                VALUES ({placeholders}, NOW(), NOW())
                RETURNING id
            """

            result = session.execute(text(insert_sql), test_user_data)
            user_id = result.scalar()
            session.commit()

            if user_id:
                print("✅ User creation test passed")
                print(f"  - User ID: {user_id}")
                print(f"  - Telegram ID: {test_user_data['telegram_id']}")
                print(f"  - Currencies: {test_user_data['preferred_currencies']}")
                print(f"  - Impact levels: {test_user_data['impact_levels']}")
                print(f"  - Analysis required: {test_user_data['analysis_required']}")
                print(f"  - Digest time: {test_user_data['digest_time']}")

                # Check notification fields if they exist
                if 'notifications_enabled' in notification_columns:
                    print(f"  - Notifications enabled: {test_user_data.get('notifications_enabled')}")
                if 'notification_minutes' in notification_columns:
                    print(f"  - Notification minutes: {test_user_data.get('notification_minutes')}")
                if 'notification_impact_levels' in notification_columns:
                    print(f"  - Notification impacts: {test_user_data.get('notification_impact_levels')}")

                # Clean up test user
                session.execute(text("DELETE FROM users WHERE id = :user_id"), {'user_id': user_id})
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

        print("✅ All database tests passed!")
        return True

    except Exception as e:
        print(f"❌ Database test failed: {e}")
        return False

if __name__ == "__main__":
    print("🚀 Setting up Forex News Bot database...")
    print("=" * 50)

    # Setup database
    if setup_database():
        print("\n🧪 Testing database operations...")
        if test_database_connection():
            print("\n🎉 Database setup and testing completed successfully!")
            print("\n📝 Next steps:")
            print("1. Start the bot application")
            print("2. Users can use /settings to configure preferences")
            print("3. Daily digest will be sent based on user preferences")
        else:
            print("\n❌ Database testing failed!")
            sys.exit(1)
    else:
        print("\n❌ Database setup failed!")
        sys.exit(1)
