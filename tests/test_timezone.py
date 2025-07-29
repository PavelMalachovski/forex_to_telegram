#!/usr/bin/env python3
"""Test timezone functionality."""

import pytz
from datetime import datetime
from bot.config import Config
from bot.database_service import ForexNewsService

def test_timezone_functionality():
    """Test timezone functionality."""
    try:
        config = Config()
        db_service = ForexNewsService(config.get_database_url())

        # Test timezone conversion
        test_time = "14:30"
        target_date = datetime.now()
        user_timezone = "Europe/Prague"

        # Parse time in user's timezone
        from bot.notification_service import NotificationService
        notification_service = NotificationService(db_service, None, config)

        event_time = notification_service._parse_event_time(target_date, test_time, user_timezone)
        print(f"Event time in {user_timezone}: {event_time}")

        # Test different timezones
        timezones = ["Europe/London", "America/New_York", "Asia/Tokyo"]
        for tz in timezones:
            event_time = notification_service._parse_event_time(target_date, test_time, tz)
            print(f"Event time in {tz}: {event_time}")

        print("✅ Timezone functionality test completed")
        return True

    except Exception as e:
        print(f"❌ Error testing timezone functionality: {e}")
        return False

if __name__ == "__main__":
    success = test_timezone_functionality()
    exit(0 if success else 1)
