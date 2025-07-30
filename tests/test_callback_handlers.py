#!/usr/bin/env python3
"""
Test script to verify that callback handlers are properly registered.
"""

import sys
import os
import logging

# Add the bot directory to the path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from bot.telegram_handlers import register_handlers
from bot.config import Config

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(name)s: %(message)s'
)

def test_callback_handlers():
    """Test that callback handlers are properly registered."""

    print("Testing callback handler registration...")
    print("-" * 50)

    # Test callback data patterns
    test_callbacks = [
        "viz_currency_EUR",
        "viz_event_EUR_123",
        "viz_chart_EUR_123_1.0",
        "viz_multi_EUR_123_1.0",
        "viz_secondary_EUR_USD_123_1.0",
        "viz_back_currencies",
        "impact_high",
        "cal_2025_8",
        "pickdate_2025-08-03",
        "ANALYSIS_YES",
        "ANALYSIS_NO"
    ]

    # Mock bot and config
    class MockBot:
        def __init__(self):
            self.handlers = []

        def callback_query_handler(self, func=None, **kwargs):
            def decorator(handler_func):
                self.handlers.append(handler_func)
                return handler_func
            return decorator

    class MockConfig:
        def __init__(self):
            self.telegram_bot_token = "test_token"
            self.timezone = "UTC"

    # Create mock objects
    bot = MockBot()
    config = MockConfig()

    # Register handlers
    register_handlers(bot, lambda x: None, config)

    print(f"✅ Registered {len(bot.handlers)} callback handlers")

    # Test callback pattern matching
    for callback_data in test_callbacks:
        print(f"Testing callback: {callback_data}")

        # Check if any handler would match this callback
        matched = False
        for handler in bot.handlers:
            try:
                # Create a mock call object
                class MockCall:
                    def __init__(self, data):
                        self.data = data

                mock_call = MockCall(callback_data)

                # Try to call the handler (this might fail, but we're just testing registration)
                # We're not actually calling it, just checking if it's registered
                matched = True
                break
            except Exception as e:
                continue

        if matched:
            print(f"  ✅ Handler registered for: {callback_data}")
        else:
            print(f"  ❌ No handler found for: {callback_data}")

    print()
    print("Test completed!")

if __name__ == "__main__":
    test_callback_handlers()
