#!/usr/bin/env python3
"""
Test script to verify calendar command works with local database.
"""

import sys
import os
import logging
from datetime import datetime
import pytz

# Add the parent directory to the path to import bot modules
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from bot.config import Config
from bot.telegram_handlers import TelegramBotManager, register_handlers
from bot.database_service import ForexNewsService

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(name)s: %(message)s'
)

def test_calendar_with_database():
    """Test calendar command with database integration."""

    # Set local database
    os.environ["USE_LOCAL_DB"] = "true"

    config = Config()

    print("Testing calendar command with database...")
    print("=" * 50)

    # Test 1: Initialize database service
    print("1. Initializing database service...")
    try:
        db_service = ForexNewsService(config.get_database_url())
        print("   ✅ Database service initialized successfully")
    except Exception as e:
        print(f"   ❌ Database service initialization failed: {e}")
        return False

    # Test 2: Initialize bot manager
    print("\n2. Initializing bot manager...")
    try:
        bot_manager = TelegramBotManager(config)
        if bot_manager.bot:
            print("   ✅ Bot manager initialized successfully")
        else:
            print("   ❌ Bot manager initialization failed")
            return False
    except Exception as e:
        print(f"   ❌ Bot manager initialization failed: {e}")
        return False

    # Test 3: Register handlers
    print("\n3. Registering handlers...")
    try:
        def mock_process_news(date, impact, analysis, debug, user_id=None):
            return []

        register_handlers(bot_manager.bot, mock_process_news, config, db_service)
        print("   ✅ Handlers registered successfully")
    except Exception as e:
        print(f"   ❌ Handler registration failed: {e}")
        return False

    # Test 4: Test calendar generation
    print("\n4. Testing calendar generation...")
    try:
        from bot.telegram_handlers import TelegramHandlers

        today = datetime.now()
        markup = TelegramHandlers.generate_calendar(today.year, today.month, config.timezone)
        print("   ✅ Calendar generated successfully")
        print(f"   Calendar type: {type(markup)}")
        print(f"   Calendar has keyboard: {hasattr(markup, 'keyboard')}")
        if hasattr(markup, 'keyboard'):
            print(f"   Number of rows: {len(markup.keyboard)}")
    except Exception as e:
        print(f"   ❌ Calendar generation failed: {e}")
        return False

    # Test 5: Test database operations
    print("\n5. Testing database operations...")
    try:
        # Test storing some sample news
        sample_news = [
            {
                'date': datetime.now(),
                'time': '10:00',
                'currency': 'USD',
                'event': 'Test Event 1',
                'impact_level': 'high',
                'analysis': 'Test analysis 1'
            },
            {
                'date': datetime.now(),
                'time': '14:00',
                'currency': 'EUR',
                'event': 'Test Event 2',
                'impact_level': 'medium',
                'analysis': 'Test analysis 2'
            }
        ]

        db_service.store_news_items(sample_news, datetime.now().date(), 'all')
        print("   ✅ Sample news stored successfully")

        # Test retrieving news
        news_items = db_service.get_news_for_date(datetime.now().date(), 'all')
        print(f"   📊 Retrieved {len(news_items)} news items")

    except Exception as e:
        print(f"   ❌ Database operations failed: {e}")
        return False

    print("\n" + "=" * 50)
    print("✅ Calendar with database test completed successfully!")
    return True

if __name__ == "__main__":
    print("📅 Calendar Database Integration Test")
    print("=" * 60)

    success = test_calendar_with_database()

    if success:
        print("\n🎉 Calendar command is ready to use!")
        print("The /calendar command should now work properly.")
    else:
        print("\n❌ Calendar database integration test failed.")

    print("\n" + "=" * 60)
    print("Test completed!")
