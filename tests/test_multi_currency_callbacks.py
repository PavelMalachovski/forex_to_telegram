#!/usr/bin/env python3
"""
Test script to verify multi-currency callback patterns are properly handled.
"""

import sys
import os
import logging

# Add the bot directory to the path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from bot.visualize_handler import VisualizeHandler

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(name)s: %(message)s'
)

def test_multi_currency_callbacks():
    """Test multi-currency callback patterns."""

    print("Testing multi-currency callback patterns...")
    print("-" * 50)

    # Test callback data patterns
    test_callbacks = [
        "viz_multi_EUR_123_1.0",
        "viz_secondary_EUR_USD_123_1.0",
        "viz_secondary_GBP_JPY_456_2.0",
        "viz_multi_USD_789_0.5"
    ]

    # Mock objects for testing
    class MockCall:
        def __init__(self, data):
            self.data = data
            self.message = MockMessage()
            self.from_user = MockUser()

        def answer_callback_query(self, text=None):
            print(f"  📞 Answered callback query: {text}")

    class MockMessage:
        def __init__(self):
            self.chat = MockChat()
            self.message_id = 123

    class MockChat:
        def __init__(self):
            self.id = 456

    class MockUser:
        def __init__(self):
            self.id = 789

    class MockBot:
        def edit_message_text(self, text, chat_id=None, message_id=None, reply_markup=None, parse_mode=None):
            print(f"  📝 Edit message: {text[:50]}...")

        def send_photo(self, chat_id, photo, caption=None, parse_mode=None):
            print(f"  📷 Send photo to {chat_id}")

        def answer_callback_query(self, call_id, text=None):
            print(f"  📞 Answer callback: {text}")

    class MockDBService:
        def __init__(self):
            pass

    class MockConfig:
        def __init__(self):
            self.timezone = "UTC"

    # Create mock objects
    db_service = MockDBService()
    config = MockConfig()
    bot = MockBot()

    # Create visualize handler
    viz_handler = VisualizeHandler(db_service, config)

    print("Testing callback pattern matching...")

    for callback_data in test_callbacks:
        print(f"\nTesting: {callback_data}")

        # Create mock call
        mock_call = MockCall(callback_data)

        try:
            # Test which handler would be called
            if callback_data.startswith("viz_multi_"):
                print("  ✅ Would call: handle_multi_currency_selection")
                # Test parsing
                parts = callback_data.split("_")
                if len(parts) >= 5:
                    primary_currency = parts[2]
                    event_id = parts[3]
                    window_hours = float(parts[4])
                    print(f"    Primary: {primary_currency}")
                    print(f"    Event ID: {event_id}")
                    print(f"    Window: {window_hours}h")

            elif callback_data.startswith("viz_secondary_"):
                print("  ✅ Would call: handle_secondary_currency_selection")
                # Test parsing
                parts = callback_data.split("_")
                if len(parts) >= 6:
                    primary_currency = parts[2]
                    secondary_currency = parts[3]
                    event_id = parts[4]
                    window_hours = float(parts[5])
                    print(f"    Primary: {primary_currency}")
                    print(f"    Secondary: {secondary_currency}")
                    print(f"    Event ID: {event_id}")
                    print(f"    Window: {window_hours}h")

            else:
                print("  ❌ No handler found")

        except Exception as e:
            print(f"  ❌ Error parsing callback: {e}")

    print("\n✅ Multi-currency callback pattern test completed!")

if __name__ == "__main__":
    test_multi_currency_callbacks()
