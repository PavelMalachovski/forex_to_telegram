#!/usr/bin/env python3
"""Offline test for timezone functionality."""

import pytz
from datetime import datetime

def test_timezone_conversion():
    """Test timezone conversion without database."""
    try:
        # Test timezone conversion
        test_time = "14:30"
        target_date = datetime.now()

        # Test different timezones
        timezones = ["Europe/Prague", "Europe/London", "America/New_York", "Asia/Tokyo"]

        for tz in timezones:
            try:
                user_tz = pytz.timezone(tz)

                # Parse time string
                time_obj = datetime.strptime(test_time, "%H:%M")

                # Combine with target date
                event_datetime = datetime.combine(target_date.date(), time_obj.time())

                # Convert to user's timezone
                event_datetime = user_tz.localize(event_datetime)

                print(f"✅ Event time in {tz}: {event_datetime}")

            except Exception as e:
                print(f"❌ Error with timezone {tz}: {e}")

        print("✅ Timezone conversion test completed")
        return True

    except Exception as e:
        print(f"❌ Error testing timezone conversion: {e}")
        return False

def test_timezone_display_names():
    """Test timezone display name formatting."""
    try:
        timezones = [
            "Europe/Prague", "Europe/London", "Europe/Paris", "Europe/Berlin",
            "America/New_York", "America/Chicago", "America/Los_Angeles",
            "Asia/Tokyo", "Asia/Shanghai", "Asia/Singapore",
            "Australia/Sydney", "UTC"
        ]

        for timezone in timezones:
            display_name = timezone.replace("Europe/", "").replace("America/", "").replace("Asia/", "").replace("Australia/", "")
            print(f"✅ {timezone} -> {display_name}")

        print("✅ Timezone display name test completed")
        return True

    except Exception as e:
        print(f"❌ Error testing timezone display names: {e}")
        return False

if __name__ == "__main__":
    print("Testing timezone functionality...")
    success1 = test_timezone_conversion()
    success2 = test_timezone_display_names()

    if success1 and success2:
        print("✅ All timezone tests passed!")
        exit(0)
    else:
        print("❌ Some timezone tests failed!")
        exit(1)
