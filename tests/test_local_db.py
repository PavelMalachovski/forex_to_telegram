#!/usr/bin/env python3
"""
Test script to set up a local SQLite database for testing.
"""

import sys
import os
import logging
from datetime import datetime

# Add the parent directory to the path to import bot modules
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from bot.models import DatabaseManager, Base, ForexNews, User
from sqlalchemy import text

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(name)s: %(message)s'
)

def test_local_database():
    """Test setting up a local SQLite database."""

    print("Testing local SQLite database...")
    print("=" * 50)

    # Use local SQLite database
    database_url = "sqlite:///./forex_bot.db"

    # Test 1: Create database manager
    print("1. Creating database manager...")
    try:
        db_manager = DatabaseManager(database_url)
        print("   ✅ Database manager created successfully")
    except Exception as e:
        print(f"   ❌ Database manager creation failed: {e}")
        return False

    # Test 2: Create tables
    print("\n2. Creating tables...")
    try:
        db_manager.create_tables()
        print("   ✅ Tables created successfully")
    except Exception as e:
        print(f"   ❌ Table creation failed: {e}")
        return False

    # Test 3: Verify tables exist
    print("\n3. Verifying tables...")
    try:
        with db_manager.get_session() as session:
            # Check if forex_news table exists
            result = session.execute(text("""
                SELECT name FROM sqlite_master
                WHERE type='table' AND name='forex_news'
            """))
            forex_news_exists = result.fetchone() is not None

            # Check if users table exists
            result = session.execute(text("""
                SELECT name FROM sqlite_master
                WHERE type='table' AND name='users'
            """))
            users_exists = result.fetchone() is not None

            print(f"   forex_news table exists: {'✅' if forex_news_exists else '❌'}")
            print(f"   users table exists: {'✅' if users_exists else '❌'}")

            if forex_news_exists and users_exists:
                print("   ✅ All tables created successfully")
            else:
                print("   ❌ Some tables are missing")
                return False

    except Exception as e:
        print(f"   ❌ Error verifying tables: {e}")
        return False

    # Test 4: Test database operations
    print("\n4. Testing database operations...")
    try:
        with db_manager.get_session() as session:
            # Test inserting a sample forex news record
            sample_news = ForexNews(
                date=datetime.now(),
                time="10:00",
                currency="USD",
                event="Test Event",
                impact_level="high",
                analysis="Test analysis"
            )
            session.add(sample_news)
            session.commit()
            print("   ✅ Sample forex news record inserted successfully")

            # Test inserting a sample user record
            sample_user = User(
                telegram_id=123456789,
                preferred_currencies="USD,EUR",
                impact_levels="high,medium"
            )
            session.add(sample_user)
            session.commit()
            print("   ✅ Sample user record inserted successfully")

            # Test querying records
            news_count = session.query(ForexNews).count()
            users_count = session.query(User).count()
            print(f"   📊 forex_news records: {news_count}")
            print(f"   📊 users records: {users_count}")

            # Clean up test records
            session.delete(sample_news)
            session.delete(sample_user)
            session.commit()
            print("   ✅ Test records cleaned up")

    except Exception as e:
        print(f"   ❌ Error testing database operations: {e}")
        return False

    print("\n" + "=" * 50)
    print("✅ Local database test completed successfully!")
    return True

if __name__ == "__main__":
    print("🗄️ Local Database Test")
    print("=" * 60)

    success = test_local_database()

    if success:
        print("\n🎉 Local database is ready for use!")
        print("You can now set USE_LOCAL_DB=true to use the local database.")
    else:
        print("\n❌ Local database test failed.")

    print("\n" + "=" * 60)
    print("Test completed!")
