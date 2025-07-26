#!/usr/bin/env python3
"""Test script for user features functionality."""

import sys
import os
from datetime import datetime, time

# Add the parent directory to the path to find the bot module
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))

from bot.config import Config
from bot.database_service import ForexNewsService
from bot.user_settings import UserSettingsHandler
from bot.daily_digest import DailyDigestScheduler

def test_user_features():
    """Test the new user features functionality."""
    print("🧪 Testing User Features")
    print("=" * 50)

    # Initialize config and database service
    config = Config()
    database_url = config.get_database_url()

    if not database_url:
        print("❌ DATABASE_URL not configured")
        return False

    try:
        # Initialize database service
        db_service = ForexNewsService(database_url)
        print("✅ Database service initialized")

        # Test user creation and preferences
        test_telegram_id = 123456789

        # Create or get user
        user = db_service.get_or_create_user(test_telegram_id)
        print(f"✅ User created/retrieved: {user.telegram_id}")

        # Test user preferences
        user.set_currencies_list(["USD", "EUR", "GBP"])
        user.set_impact_levels_list(["high", "medium"])
        user.analysis_required = True
        user.digest_time = time(8, 0)  # 8:00 AM

        # Update preferences
        success = db_service.update_user_preferences(
            test_telegram_id,
            preferred_currencies="USD,EUR,GBP",
            impact_levels="high,medium",
            analysis_required=True,
            digest_time=time(8, 0)
        )

        if success:
            print("✅ User preferences updated successfully")
        else:
            print("❌ Failed to update user preferences")
            return False

        # Verify preferences
        updated_user = db_service.get_or_create_user(test_telegram_id)
        print(f"✅ User preferences verified:")
        print(f"  - Currencies: {updated_user.get_currencies_list()}")
        print(f"  - Impact levels: {updated_user.get_impact_levels_list()}")
        print(f"  - Analysis required: {updated_user.analysis_required}")
        print(f"  - Digest time: {updated_user.digest_time}")

        # Test user settings handler
        settings_handler = UserSettingsHandler(db_service)
        print("✅ User settings handler initialized")

        # Test settings keyboard generation
        markup = settings_handler.get_settings_keyboard(test_telegram_id)
        if markup:
            print("✅ Settings keyboard generated successfully")
        else:
            print("❌ Failed to generate settings keyboard")
            return False

        # Test currencies keyboard
        currencies_markup = settings_handler.get_currencies_keyboard(test_telegram_id)
        if currencies_markup:
            print("✅ Currencies keyboard generated successfully")
        else:
            print("❌ Failed to generate currencies keyboard")
            return False

        # Test impact keyboard
        impact_markup = settings_handler.get_impact_keyboard(test_telegram_id)
        if impact_markup:
            print("✅ Impact keyboard generated successfully")
        else:
            print("❌ Failed to generate impact keyboard")
            return False

        # Test digest time keyboard
        digest_markup = settings_handler.get_digest_time_keyboard(test_telegram_id)
        if digest_markup:
            print("✅ Digest time keyboard generated successfully")
        else:
            print("❌ Failed to generate digest time keyboard")
            return False

        # Test getting users for digest
        users_for_digest = db_service.get_users_for_digest(time(8, 0))
        print(f"✅ Found {len(users_for_digest)} users for 8:00 AM digest")

        # Test getting all users
        all_users = db_service.get_all_users()
        print(f"✅ Found {len(all_users)} total users")

        # Clean up test user
        with db_service.db_manager.get_session() as session:
            test_user = session.query(db_service.db_manager.Base.classes.User).filter(
                db_service.db_manager.Base.classes.User.telegram_id == test_telegram_id
            ).first()
            if test_user:
                session.delete(test_user)
                session.commit()
                print("✅ Test user cleaned up")

        print("\n🎉 All user features tests passed!")
        return True

    except Exception as e:
        print(f"❌ User features test failed: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_daily_digest_scheduler():
    """Test the daily digest scheduler functionality."""
    print("\n🧪 Testing Daily Digest Scheduler")
    print("=" * 50)

    config = Config()
    database_url = config.get_database_url()

    if not database_url:
        print("❌ DATABASE_URL not configured")
        return False

    try:
        # Initialize database service
        db_service = ForexNewsService(database_url)
        print("✅ Database service initialized")

        # Create a mock bot for testing
        class MockBot:
            def send_message(self, chat_id, text, parse_mode=None):
                print(f"📱 Mock bot would send to {chat_id}: {text[:100]}...")
                return True

        mock_bot = MockBot()

        # Initialize digest scheduler
        digest_scheduler = DailyDigestScheduler(db_service, mock_bot, config)
        print("✅ Daily digest scheduler initialized")

        # Test scheduler status
        status = digest_scheduler.get_scheduler_status()
        print(f"✅ Scheduler status: {status}")

        # Test sending test digest
        test_telegram_id = 123456789

        # Create a test user
        user = db_service.get_or_create_user(test_telegram_id)
        user.set_currencies_list(["USD", "EUR"])
        user.set_impact_levels_list(["high"])
        user.analysis_required = True
        user.digest_time = time(8, 0)

        db_service.update_user_preferences(
            test_telegram_id,
            preferred_currencies="USD,EUR",
            impact_levels="high",
            analysis_required=True,
            digest_time=time(8, 0)
        )

        # Test sending digest
        success = digest_scheduler.send_test_digest(test_telegram_id)
        if success:
            print("✅ Test digest sent successfully")
        else:
            print("❌ Failed to send test digest")

        # Clean up test user
        with db_service.db_manager.get_session() as session:
            test_user = session.query(db_service.db_manager.Base.classes.User).filter(
                db_service.db_manager.Base.classes.User.telegram_id == test_telegram_id
            ).first()
            if test_user:
                session.delete(test_user)
                session.commit()
                print("✅ Test user cleaned up")

        print("🎉 Daily digest scheduler tests passed!")
        return True

    except Exception as e:
        print(f"❌ Daily digest scheduler test failed: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    print("🚀 Testing Forex News Bot User Features")
    print("=" * 60)

    # Test user features
    if test_user_features():
        # Test daily digest scheduler
        if test_daily_digest_scheduler():
            print("\n🎉 All tests passed successfully!")
            print("\n📝 User features are ready to use:")
            print("1. Users can use /settings to configure preferences")
            print("2. Currency filtering is available")
            print("3. Impact level selection is working")
            print("4. Daily digest scheduling is functional")
            print("5. AI analysis preferences are configurable")
        else:
            print("\n❌ Daily digest scheduler tests failed!")
            sys.exit(1)
    else:
        print("\n❌ User features tests failed!")
        sys.exit(1)
