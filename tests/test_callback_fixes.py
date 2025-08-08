#!/usr/bin/env python3
"""
Test script to verify callback fixes work correctly.
"""

import sys
import os
import logging

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

def test_callback_fixes():
    """Test the callback fixes."""

    print("Testing callback fixes...")
    print("-" * 50)

    # Mock objects
    class MockBot:
        def __init__(self):
            self.callback_answered = False
            self.last_callback_text = None

        def edit_message_text(self, text, chat_id=None, message_id=None, reply_markup=None, parse_mode=None):
            print(f"📝 Edit message: {text[:80]}...")

        def send_photo(self, chat_id, photo, caption=None, parse_mode=None):
            print(f"📷 Send photo to {chat_id}")

        def answer_callback_query(self, call_id, text=None):
            self.callback_answered = True
            self.last_callback_text = text
            print(f"📞 Answer callback: {text}")

    class MockCall:
        def __init__(self, data, user_id=123):
            self.data = data
            self.id = "test_call_id"
            self.from_user = MockUser(user_id)
            self.message = MockMessage()

    class MockUser:
        def __init__(self, user_id):
            self.id = user_id

    class MockMessage:
        def __init__(self):
            self.chat = MockChat()
            self.message_id = 456

    class MockChat:
        def __init__(self):
            self.id = 789

    # Create mock objects
    bot = MockBot()
    config = Config()

    # Initialize database service
    db_service = ForexNewsService("sqlite:///test_forex_bot.db")

    # Create visualize handler
    viz_handler = VisualizeHandler(db_service, config)

    # Test 1: Multi-currency selection callback
    print("Test 1: Multi-currency selection callback")
    multi_call = MockCall("viz_multi_EUR_123_1.0")

    try:
        viz_handler.handle_multi_currency_selection(multi_call, bot)
        if bot.callback_answered:
            print(f"✅ Callback answered immediately: {bot.last_callback_text}")
        else:
            print("❌ Callback not answered")
    except Exception as e:
        print(f"❌ Error in multi-currency selection: {e}")

    print()

    # Test 2: Secondary currency selection callback
    print("Test 2: Secondary currency selection callback")
    bot.callback_answered = False
    secondary_call = MockCall("viz_secondary_EUR_USD_123_1.0")

    try:
        viz_handler.handle_secondary_currency_selection(secondary_call, bot)
        if bot.callback_answered:
            print(f"✅ Callback answered immediately: {bot.last_callback_text}")
        else:
            print("❌ Callback not answered")
    except Exception as e:
        print(f"❌ Error in secondary currency selection: {e}")

    print()

    # Test 3: Single chart generation callback
    print("Test 3: Single chart generation callback")
    bot.callback_answered = False
    chart_call = MockCall("viz_chart_EUR_123_1.0")

    try:
        viz_handler.handle_chart_generation(chart_call, bot)
        if bot.callback_answered:
            print(f"✅ Callback answered immediately: {bot.last_callback_text}")
        else:
            print("❌ Callback not answered")
    except Exception as e:
        print(f"❌ Error in chart generation: {e}")

    print()
    print("✅ Callback fixes test completed!")

if __name__ == "__main__":
    test_callback_fixes()
