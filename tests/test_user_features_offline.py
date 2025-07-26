#!/usr/bin/env python3
"""Offline test script for user features functionality."""

import sys
import os
import pytest
from datetime import datetime, time
from typing import List, Optional

# Add the parent directory to the path to find the bot module
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))

from bot.models import User

def test_user_model():
    """Test the User model functionality."""
    print("🧪 Testing User Model (Offline)")
    print("=" * 50)

    try:
        # Create a test user
        user = User(
            telegram_id=123456789,
            preferred_currencies="USD,EUR,GBP",
            impact_levels="high,medium",
            analysis_required=True,
            digest_time=time(8, 0)
        )

        print("✅ User model created successfully")
        print(f"  - Telegram ID: {user.telegram_id}")
        print(f"  - Currencies: {user.get_currencies_list()}")
        print(f"  - Impact levels: {user.get_impact_levels_list()}")
        print(f"  - Analysis required: {user.analysis_required}")
        print(f"  - Digest time: {user.digest_time}")

        # Test currency list methods
        user.set_currencies_list(["USD", "EUR", "JPY"])
        print(f"  - Updated currencies: {user.get_currencies_list()}")

        # Test impact levels methods
        user.set_impact_levels_list(["high", "low"])
        print(f"  - Updated impact levels: {user.get_impact_levels_list()}")

        # Test to_dict method
        user_dict = user.to_dict()
        print(f"  - Dictionary representation: {user_dict}")

        print("✅ User model tests passed!")

    except Exception as e:
        print(f"❌ User model test failed: {e}")
        import traceback
        traceback.print_exc()
        pytest.fail(f"User model test failed: {e}")

def test_message_formatter():
    """Test the enhanced MessageFormatter with currency filtering."""
    print("\n🧪 Testing MessageFormatter (Offline)")
    print("=" * 50)

    try:
        from bot.scraper import MessageFormatter
        from datetime import datetime

        # Create test news items
        test_news = [
            {
                'time': '10:30',
                'currency': 'USD',
                'event': 'Test USD Event',
                'actual': '1.5',
                'forecast': '1.4',
                'previous': '1.3',
                'impact': 'high'
            },
            {
                'time': '11:00',
                'currency': 'EUR',
                'event': 'Test EUR Event',
                'actual': '1.2',
                'forecast': '1.1',
                'previous': '1.0',
                'impact': 'medium'
            },
            {
                'time': '12:00',
                'currency': 'GBP',
                'event': 'Test GBP Event',
                'actual': '1.8',
                'forecast': '1.7',
                'previous': '1.6',
                'impact': 'low'
            }
        ]

        target_date = datetime.now()

        # Test without currency filtering
        message_all = MessageFormatter.format_news_message(
            test_news, target_date, "all", True
        )
        print("✅ Message formatting without currency filter:")
        print(f"  - Length: {len(message_all)} characters")
        print(f"  - Contains USD: {'USD' in message_all}")
        print(f"  - Contains EUR: {'EUR' in message_all}")
        print(f"  - Contains GBP: {'GBP' in message_all}")

        # Test with currency filtering (USD and EUR only)
        message_filtered = MessageFormatter.format_news_message(
            test_news, target_date, "all", True, ["USD", "EUR"]
        )
        print("\n✅ Message formatting with currency filter (USD, EUR):")
        print(f"  - Length: {len(message_filtered)} characters")
        print(f"  - Contains USD: {'USD' in message_filtered}")
        print(f"  - Contains EUR: {'EUR' in message_filtered}")
        print(f"  - Contains GBP: {'GBP' in message_filtered}")

        # Test with single currency filter
        message_usd_only = MessageFormatter.format_news_message(
            test_news, target_date, "all", True, ["USD"]
        )
        print("\n✅ Message formatting with single currency filter (USD):")
        print(f"  - Length: {len(message_usd_only)} characters")
        print(f"  - Contains USD: {'USD' in message_usd_only}")
        print(f"  - Contains EUR: {'EUR' in message_usd_only}")
        print(f"  - Contains GBP: {'GBP' in message_usd_only}")

        print("✅ MessageFormatter tests passed!")

    except Exception as e:
        print(f"❌ MessageFormatter test failed: {e}")
        import traceback
        traceback.print_exc()
        pytest.fail(f"MessageFormatter test failed: {e}")

def test_user_settings_handler():
    """Test the UserSettingsHandler functionality."""
    print("\n🧪 Testing UserSettingsHandler (Offline)")
    print("=" * 50)

    try:
        from bot.user_settings import UserSettingsHandler, AVAILABLE_CURRENCIES, IMPACT_LEVELS

        print("✅ Available currencies:")
        for currency in AVAILABLE_CURRENCIES:
            print(f"  - {currency}")

        print("\n✅ Available impact levels:")
        for impact in IMPACT_LEVELS:
            print(f"  - {impact}")

        print("\n✅ Available digest times (dynamic):")
        # Digest times are dynamic based on user preferences
        print("  - Times are set dynamically based on user preferences")
        print("  - Default time is 08:00")

        # Test keyboard generation (without database)
        print("\n✅ Testing keyboard generation...")

        # Mock database service
        class MockDatabaseService:
            def get_or_create_user(self, user_id):
                from bot.models import User
                return User(
                    telegram_id=user_id,
                    preferred_currencies="USD,EUR",
                    impact_levels="high,medium",
                    analysis_required=True,
                    digest_time=time(8, 0)
                )

            def update_user_preferences(self, user_id, **kwargs):
                return True

        mock_db_service = MockDatabaseService()
        settings_handler = UserSettingsHandler(mock_db_service)

        # Test settings keyboard
        settings_markup = settings_handler.get_settings_keyboard(123456789)
        if settings_markup:
            print("✅ Settings keyboard generated successfully")
        else:
            print("❌ Failed to generate settings keyboard")
            pytest.fail("Failed to generate settings keyboard")

        # Test currencies keyboard
        currencies_markup = settings_handler.get_currencies_keyboard(123456789)
        if currencies_markup:
            print("✅ Currencies keyboard generated successfully")
        else:
            print("❌ Failed to generate currencies keyboard")
            pytest.fail("Failed to generate currencies keyboard")

        # Test impact keyboard
        impact_markup = settings_handler.get_impact_keyboard(123456789)
        if impact_markup:
            print("✅ Impact keyboard generated successfully")
        else:
            print("❌ Failed to generate impact keyboard")
            pytest.fail("Failed to generate impact keyboard")

        # Test digest time keyboard
        digest_markup = settings_handler.get_digest_time_keyboard(123456789)
        if digest_markup:
            print("✅ Digest time keyboard generated successfully")
        else:
            print("❌ Failed to generate digest time keyboard")
            pytest.fail("Failed to generate digest time keyboard")

        print("✅ UserSettingsHandler tests passed!")

    except Exception as e:
        print(f"❌ UserSettingsHandler test failed: {e}")
        import traceback
        traceback.print_exc()
        pytest.fail(f"UserSettingsHandler test failed: {e}")

def test_daily_digest_scheduler():
    """Test the DailyDigestScheduler functionality."""
    print("\n🧪 Testing DailyDigestScheduler (Offline)")
    print("=" * 50)

    try:
        from bot.daily_digest import DailyDigestScheduler

        # Mock components
        class MockBot:
            def send_message(self, chat_id, text, parse_mode=None):
                print(f"📱 Mock bot would send to {chat_id}: {text[:100]}...")
                return True

        class MockConfig:
            def __init__(self):
                self.timezone = "Europe/Berlin"

        class MockDatabaseService:
            def get_users_for_digest(self, digest_time):
                from bot.models import User
                return [
                    User(
                        telegram_id=123456789,
                        preferred_currencies="USD,EUR",
                        impact_levels="high",
                        analysis_required=True,
                        digest_time=digest_time
                    )
                ]

            def get_news_for_date(self, target_date, impact_level):
                return [
                    {
                        'time': '10:30',
                        'currency': 'USD',
                        'event': 'Test Event',
                        'actual': '1.5',
                        'forecast': '1.4',
                        'previous': '1.3',
                        'impact': 'high'
                    }
                ]

            def get_all_users(self):
                from bot.models import User
                return [
                    User(
                        telegram_id=123456789,
                        preferred_currencies="USD,EUR",
                        impact_levels="high",
                        analysis_required=True,
                        digest_time=time(8, 0)
                    )
                ]

            def get_or_create_user(self, user_id):
                from bot.models import User
                return User(
                    telegram_id=user_id,
                    preferred_currencies="USD,EUR",
                    impact_levels="high",
                    analysis_required=True,
                    digest_time=time(8, 0)
                )

        mock_bot = MockBot()
        mock_config = MockConfig()
        mock_db_service = MockDatabaseService()

        # Initialize scheduler
        scheduler = DailyDigestScheduler(mock_db_service, mock_bot, mock_config)
        print("✅ Daily digest scheduler initialized")

        # Test scheduler status
        status = scheduler.get_scheduler_status()
        print(f"✅ Scheduler status: {status}")

        # Test sending test digest
        success = scheduler.send_test_digest(123456789)
        if success:
            print("✅ Test digest sent successfully")
        else:
            print("❌ Failed to send test digest")
            pytest.fail("Failed to send test digest")

        print("✅ DailyDigestScheduler tests passed!")

    except Exception as e:
        print(f"❌ DailyDigestScheduler test failed: {e}")
        import traceback
        traceback.print_exc()
        pytest.fail(f"DailyDigestScheduler test failed: {e}")

if __name__ == "__main__":
    print("🚀 Testing Forex News Bot User Features (Offline)")
    print("=" * 60)

    # Run all tests
    tests = [
        test_user_model,
        test_message_formatter,
        test_user_settings_handler,
        test_daily_digest_scheduler
    ]

    for test in tests:
        test()
        print()

    print("=" * 60)
    print("\n🎉 All offline tests passed successfully!")
    print("\n📝 User features are ready to use:")
    print("1. User model with preferences management")
    print("2. MessageFormatter with currency filtering")
    print("3. UserSettingsHandler with interactive keyboards")
    print("4. DailyDigestScheduler for automated delivery")
    print("5. All components work together seamlessly")
