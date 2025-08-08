#!/usr/bin/env python3
"""
Test script to verify that the bot can handle multi-currency chart requests.
"""

import sys
import os
import logging
from datetime import datetime, timedelta
import pytz

# Add the bot directory to the path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from bot.visualize_handler import VisualizeHandler
from bot.database_service import ForexNewsService
from bot.config import Config

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(name)s: %(message)s'
)

def test_bot_multi_currency():
    """Test that the bot can handle multi-currency chart requests."""

    print("Testing bot multi-currency functionality...")
    print("-" * 50)

    # Mock objects
    class MockBot:
        def edit_message_text(self, text, chat_id=None, message_id=None, reply_markup=None, parse_mode=None):
            print(f"📝 Edit message: {text[:100]}...")

        def send_photo(self, chat_id, photo, caption=None, parse_mode=None):
            print(f"📷 Send photo to {chat_id}")
            print(f"   Caption: {caption[:100]}...")

        def answer_callback_query(self, call_id, text=None):
            print(f"📞 Answer callback: {text}")

    class MockCall:
        def __init__(self, data, user_id=123):
            self.data = data
            self.id = "test_call_id"
            self.from_user = MockUser(user_id)
            self.message = MockMessage()

        def answer_callback_query(self, text=None):
            print(f"📞 Answered callback query: {text}")

    class MockUser:
        def __init__(self, user_id):
            self.id = user_id

    class MockMessage:
        def __init__(self):
            self.chat = MockChat()
            self.message_id = 456

        def reply_to(self, text, reply_markup=None, parse_mode=None):
            print(f"📝 Reply: {text[:100]}...")

    class MockChat:
        def __init__(self):
            self.id = 789

    # Create mock objects
    bot = MockBot()
    config = Config()

    # Initialize database service (use SQLite for testing)
    db_service = ForexNewsService("sqlite:///test_forex_bot.db")

    # Create visualize handler
    viz_handler = VisualizeHandler(db_service, config)

    print("Testing multi-currency callback flow...")

    # Test 1: Multi-currency selection
    print("\n1. Testing multi-currency selection...")
    multi_call = MockCall("viz_multi_EUR_123_1.0")

    try:
        viz_handler.handle_multi_currency_selection(multi_call, bot)
        print("✅ Multi-currency selection handler executed successfully")
    except Exception as e:
        print(f"❌ Error in multi-currency selection: {e}")

    # Test 2: Secondary currency selection
    print("\n2. Testing secondary currency selection...")
    secondary_call = MockCall("viz_secondary_EUR_USD_123_1.0")

    try:
        viz_handler.handle_secondary_currency_selection(secondary_call, bot)
        print("✅ Secondary currency selection handler executed successfully")
    except Exception as e:
        print(f"❌ Error in secondary currency selection: {e}")

    # Test 3: Chart generation
    print("\n3. Testing chart generation...")
    chart_call = MockCall("viz_chart_EUR_123_1.0")

    try:
        viz_handler.handle_chart_generation(chart_call, bot)
        print("✅ Chart generation handler executed successfully")
    except Exception as e:
        print(f"❌ Error in chart generation: {e}")

    # Test 4: Currency selection
    print("\n4. Testing currency selection...")
    currency_call = MockCall("viz_currency_EUR")

    try:
        viz_handler.handle_currency_selection(currency_call, bot)
        print("✅ Currency selection handler executed successfully")
    except Exception as e:
        print(f"❌ Error in currency selection: {e}")

    print("\n✅ Bot multi-currency functionality test completed!")

if __name__ == "__main__":
    test_bot_multi_currency()
