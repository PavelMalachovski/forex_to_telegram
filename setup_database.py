#!/usr/bin/env python3
"""
Database setup script for the forex news bot.
This script will create the database tables and run any necessary migrations.
"""

import os
import sys
from bot.config import Config
from bot.models import DatabaseManager, Base
from bot.database_service import ForexNewsService

def setup_database():
    """Set up the database with tables and initial data."""
    try:
        config = Config()
        database_url = config.get_database_url()

        print(f"Setting up database with URL: {database_url}")

        # Create database manager
        db_manager = DatabaseManager(database_url)

        # Test connection
        if not db_manager.health_check():
            print("❌ Database connection failed!")
            return False

        print("✅ Database connection successful")

        # Create tables
        print("Creating database tables...")
        db_manager.create_tables()
        print("✅ Database tables created successfully")

        # Test database service
        db_service = ForexNewsService(database_url)
        if db_service.health_check():
            print("✅ Database service is working correctly")
        else:
            print("❌ Database service health check failed")
            return False

        print("\n🎉 Database setup completed successfully!")
        return True

    except Exception as e:
        print(f"❌ Database setup failed: {e}")
        return False


def run_migrations():
    """Run database migrations."""
    try:
        print("Running database migrations...")
        os.system("alembic upgrade head")
        print("✅ Migrations completed successfully")
        return True
    except Exception as e:
        print(f"❌ Migration failed: {e}")
        return False


if __name__ == "__main__":
    print("🚀 Setting up Forex News Bot Database")
    print("=" * 50)

    # Check environment variables
    config = Config()
    missing_vars = config.validate_required_vars()

    if missing_vars:
        print(f"⚠️  Missing environment variables: {missing_vars}")
        print("Please set these variables before running the setup.")
        sys.exit(1)

    # Setup database
    if setup_database():
        print("\n📊 Database is ready for use!")
        print("\nNext steps:")
        print("1. Deploy to Render.com with the updated environment variables")
        print("2. Use the bulk import script to import historical data:")
        print("   python bulk_import.py --start-date 2025-01-01 --end-date 2025-01-31 --impact-level high")
        print("3. Test the API endpoints:")
        print("   - GET /health - Check service health")
        print("   - GET /db/stats - View database statistics")
        print("   - GET /db/check/2025-01-01 - Check data for specific date")
    else:
        print("\n❌ Database setup failed!")
        sys.exit(1)
