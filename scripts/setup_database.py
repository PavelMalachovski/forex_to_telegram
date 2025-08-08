#!/usr/bin/env python3
"""
Script to set up the database tables for the forex bot.
"""

import sys
import os
import logging
from datetime import datetime

# Add the parent directory to the path to import bot modules
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from bot.config import Config
from bot.models import DatabaseManager, Base, ForexNews, User
from sqlalchemy import text

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(name)s: %(message)s'
)

def setup_database():
    """Set up the database tables."""

    config = Config()

    print("Setting up database...")
    print("=" * 50)

    # Test 1: Check database connection
    print("1. Testing database connection...")
    try:
        db_manager = DatabaseManager(config.get_database_url())
        print("   ✅ Database connection successful")
    except Exception as e:
        print(f"   ❌ Database connection failed: {e}")
        return False

    # Test 2: Check if tables exist
    print("\n2. Checking existing tables...")
    try:
        with db_manager.get_session() as session:
            # Check if forex_news table exists
            result = session.execute(text("""
                SELECT EXISTS (
                    SELECT FROM information_schema.tables
                    WHERE table_name = 'forex_news'
                )
            """))
            forex_news_exists = result.scalar()

            # Check if users table exists
            result = session.execute(text("""
                SELECT EXISTS (
                    SELECT FROM information_schema.tables
                    WHERE table_name = 'users'
                )
            """))
            users_exists = result.scalar()

            print(f"   forex_news table exists: {'✅' if forex_news_exists else '❌'}")
            print(f"   users table exists: {'✅' if users_exists else '❌'}")

    except Exception as e:
        print(f"   ❌ Error checking tables: {e}")
        return False

    # Test 3: Create tables
    print("\n3. Creating tables...")
    try:
        db_manager.create_tables()
        print("   ✅ Tables created successfully")
    except Exception as e:
        print(f"   ❌ Error creating tables: {e}")
        return False

    # Test 4: Verify tables were created
    print("\n4. Verifying tables...")
    try:
        with db_manager.get_session() as session:
            # Check if forex_news table exists
            result = session.execute(text("""
                SELECT EXISTS (
                    SELECT FROM information_schema.tables
                    WHERE table_name = 'forex_news'
                )
            """))
            forex_news_exists = result.scalar()

            # Check if users table exists
            result = session.execute(text("""
                SELECT EXISTS (
                    SELECT FROM information_schema.tables
                    WHERE table_name = 'users'
                )
            """))
            users_exists = result.scalar()

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

    # Test 5: Test inserting a sample record
    print("\n5. Testing database operations...")
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

            # Clean up test records
            session.delete(sample_news)
            session.delete(sample_user)
            session.commit()
            print("   ✅ Test records cleaned up")

    except Exception as e:
        print(f"   ❌ Error testing database operations: {e}")
        return False

    print("\n" + "=" * 50)
    print("✅ Database setup completed successfully!")
    return True

def check_database_health():
    """Check database health."""

    config = Config()

    print("\nChecking database health...")
    print("=" * 50)

    try:
        db_manager = DatabaseManager(config.get_database_url())

        # Test connection
        if db_manager.health_check():
            print("   ✅ Database connection healthy")
        else:
            print("   ❌ Database connection unhealthy")
            return False

        # Test table access
        with db_manager.get_session() as session:
            # Count records in forex_news table
            result = session.execute(text("SELECT COUNT(*) FROM forex_news"))
            forex_news_count = result.scalar()
            print(f"   📊 forex_news records: {forex_news_count}")

            # Count records in users table
            result = session.execute(text("SELECT COUNT(*) FROM users"))
            users_count = result.scalar()
            print(f"   📊 users records: {users_count}")

            # Check table structure
            result = session.execute(text("""
                SELECT column_name, data_type
                FROM information_schema.columns
                WHERE table_name = 'forex_news'
                ORDER BY ordinal_position
            """))
            forex_news_columns = result.fetchall()
            print(f"   📋 forex_news columns: {len(forex_news_columns)}")

            result = session.execute(text("""
                SELECT column_name, data_type
                FROM information_schema.columns
                WHERE table_name = 'users'
                ORDER BY ordinal_position
            """))
            users_columns = result.fetchall()
            print(f"   📋 users columns: {len(users_columns)}")

    except Exception as e:
        print(f"   ❌ Database health check failed: {e}")
        return False

    print("   ✅ Database health check completed")
    return True

if __name__ == "__main__":
    print("🗄️ Database Setup Script")
    print("=" * 60)

    # Set up database
    setup_success = setup_database()

    if setup_success:
        # Check database health
        health_success = check_database_health()

        if health_success:
            print("\n🎉 Database is ready for use!")
        else:
            print("\n❌ Database health check failed.")
    else:
        print("\n❌ Database setup failed.")

    print("\n" + "=" * 60)
    print("Setup completed!")
