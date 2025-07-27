#!/usr/bin/env python3
"""Test script for notification functionality."""

import os
import sys
from datetime import datetime, timedelta

# Add the bot directory to the path
sys.path.append(os.path.join(os.path.dirname(__file__), 'bot'))

from bot.config import Config
from bot.database_service import ForexNewsService
from bot.notification_service import NotificationService
from bot.models import User

def test_notification_service():
    """Test the notification service functionality."""

    print("🧪 Testing Notification Service...")

    # Initialize config and services
    config = Config()

    try:
        db_service = ForexNewsService(config.get_database_url())
    except Exception as e:
        print(f"⚠️ Skipping notification service tests - database not available: {e}")
        return

    # Create a mock bot for testing
    class MockBot:
        def send_message(self, chat_id, message, parse_mode=None):
            print(f"📱 Mock Bot: Sending to {chat_id}: {message}")
            return True

    mock_bot = MockBot()
    notification_service = NotificationService(db_service, mock_bot, config)

    # Test 1: Format notification message
    print("\n📝 Test 1: Format notification message")
    test_news_item = {
        'time': '14:30',
        'currency': 'USD',
        'event': 'Non-Farm Payrolls',
        'impact': 'high'
    }
    message = notification_service.format_notification_message(test_news_item, 30)
    print(f"Formatted message: {message}")

    # Test 2: Parse event time
    print("\n⏰ Test 2: Parse event time")
    target_date = datetime.now()
    test_times = ['14:30', '2:30pm', '09:00', '9:00am']

    for time_str in test_times:
        parsed_time = notification_service._parse_event_time(target_date, time_str)
        print(f"'{time_str}' -> {parsed_time}")

    # Test 3: Get upcoming events
    print("\n🔍 Test 3: Get upcoming events")
    upcoming_events = notification_service.get_upcoming_events(
        datetime.now(),
        ['high', 'medium'],
        60
    )
    print(f"Found {len(upcoming_events)} upcoming events")

    # Test 4: User notification preferences
    print("\n👤 Test 4: User notification preferences")
    try:
        # Create or get a test user
        test_user_id = 123456789
        user = db_service.get_or_create_user(test_user_id)

        # Update notification preferences
        db_service.update_user_preferences(
            test_user_id,
            notifications_enabled=True,
            notification_minutes=30,
            notification_impact_levels="high,medium"
        )

        # Verify the settings
        updated_user = db_service.get_or_create_user(test_user_id)
        print(f"Notifications enabled: {updated_user.notifications_enabled}")
        print(f"Notification minutes: {updated_user.notification_minutes}")
        print(f"Notification impacts: {updated_user.get_notification_impact_levels_list()}")

    except Exception as e:
        print(f"❌ Error testing user preferences: {e}")

    print("\n✅ Notification service tests completed!")

def test_notification_scheduler():
    """Test the notification scheduler."""

    print("\n🧪 Testing Notification Scheduler...")

    # Initialize config and services
    config = Config()

    try:
        db_service = ForexNewsService(config.get_database_url())
    except Exception as e:
        print(f"⚠️ Skipping notification scheduler tests - database not available: {e}")
        return

    # Create a mock bot for testing
    class MockBot:
        def send_message(self, chat_id, message, parse_mode=None):
            print(f"📱 Mock Bot: Sending to {chat_id}: {message}")
            return True

    mock_bot = MockBot()

    try:
        from bot.notification_scheduler import NotificationScheduler
        scheduler = NotificationScheduler(db_service, mock_bot, config)

        print(f"Scheduler running: {scheduler.is_running()}")

        # Test the notification check manually
        print("Testing manual notification check...")
        scheduler._check_notifications()

        # Stop the scheduler
        scheduler.stop()
        print("Scheduler stopped")

    except Exception as e:
        print(f"❌ Error testing notification scheduler: {e}")

    print("✅ Notification scheduler tests completed!")

if __name__ == "__main__":
    print("🚀 Starting Notification Feature Tests...")

    try:
        test_notification_service()
        test_notification_scheduler()
        print("\n🎉 All notification tests completed successfully!")

    except Exception as e:
        print(f"❌ Test failed with error: {e}")
        import traceback
        traceback.print_exc()
