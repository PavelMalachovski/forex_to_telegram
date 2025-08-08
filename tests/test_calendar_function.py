#!/usr/bin/env python3
"""
Test script to verify the calendar function works correctly.
"""

import sys
import os
import logging
from datetime import datetime
import pytz

# Add the parent directory to the path to import bot modules
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from bot.telegram_handlers import TelegramHandlers

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(name)s: %(message)s'
)

def test_calendar_generation():
    """Test calendar generation function."""

    print("Testing calendar generation...")
    print("=" * 50)

    # Test 1: Generate calendar for current month
    print("1. Generating calendar for current month...")
    try:
        today = datetime.now()
        markup = TelegramHandlers.generate_calendar(today.year, today.month, "UTC")
        print("   ✅ Calendar generated successfully")
        print(f"   Calendar type: {type(markup)}")
        print(f"   Calendar has keyboard: {hasattr(markup, 'keyboard')}")
        if hasattr(markup, 'keyboard'):
            print(f"   Number of rows: {len(markup.keyboard)}")
    except Exception as e:
        print(f"   ❌ Calendar generation failed: {e}")
        return False

    # Test 2: Generate calendar for different months
    print("\n2. Testing different months...")
    test_months = [
        (2025, 1),   # January
        (2025, 6),   # June
        (2025, 12),  # December
    ]

    for year, month in test_months:
        try:
            markup = TelegramHandlers.generate_calendar(year, month, "UTC")
            print(f"   ✅ {year}-{month:02d}: Success")
        except Exception as e:
            print(f"   ❌ {year}-{month:02d}: Failed - {e}")
            return False

    # Test 3: Test with different timezones
    print("\n3. Testing different timezones...")
    timezones = ["UTC", "America/New_York", "Europe/London", "Asia/Tokyo"]

    for tz in timezones:
        try:
            markup = TelegramHandlers.generate_calendar(2025, 8, tz)
            print(f"   ✅ {tz}: Success")
        except Exception as e:
            print(f"   ❌ {tz}: Failed - {e}")
            return False

    print("\n" + "=" * 50)
    print("✅ Calendar generation test completed successfully!")
    return True

if __name__ == "__main__":
    print("📅 Calendar Function Test")
    print("=" * 60)

    success = test_calendar_generation()

    if success:
        print("\n🎉 All calendar tests passed!")
    else:
        print("\n❌ Some calendar tests failed.")

    print("\n" + "=" * 60)
    print("Test completed!")
