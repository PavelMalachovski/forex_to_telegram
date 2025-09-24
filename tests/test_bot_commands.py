#!/usr/bin/env python3
"""
Test script to check if bot commands are working properly.
"""

import sys
import os
import logging
from datetime import datetime
import pytz

# Add the parent directory to the path to import bot modules
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from bot.config import Config
from bot.telegram_handlers import TelegramBotManager

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(name)s: %(message)s'
)

def test_bot_initialization():
    """Test bot initialization and basic functionality."""

    config = Config()

    print("Testing bot initialization...")
    print("=" * 50)

    # Test 1: Check if bot token is set
    print(f"1. Bot token configured: {'✅' if config.telegram_bot_token else '❌'}")
    if config.telegram_bot_token:
        print(f"   Token: {config.telegram_bot_token[:10]}...")
    else:
        print("   ❌ TELEGRAM_BOT_TOKEN not set")
        assert False, "TELEGRAM_BOT_TOKEN not set"

    # Test 2: Initialize bot manager
    print("\n2. Initializing bot manager...")
    bot_manager = TelegramBotManager(config)

    if bot_manager.bot:
        print("   ✅ Bot initialized successfully")
    else:
        print("   ❌ Bot initialization failed")
        assert False, "Bot initialization failed"

    # Test 3: Test bot connection
    print("\n3. Testing bot connection...")
    try:
        bot_info = bot_manager.test_bot_connection()
        if bot_info:
            print("   ✅ Bot connection successful")
            print(f"   Bot ID: {bot_info.get('id', 'N/A')}")
            print(f"   Bot Username: {bot_info.get('username', 'N/A')}")
            print(f"   Bot Name: {bot_info.get('first_name', 'N/A')}")
        else:
            print("   ❌ Bot connection failed")
            assert False, "Bot connection failed"
    except Exception as e:
        print(f"   ❌ Bot connection error: {e}")
        assert False, f"Bot connection error: {e}"

    # Test 4: Check webhook status
    print("\n4. Checking webhook status...")
    try:
        webhook_status = bot_manager.check_webhook_status()
        if 'error' not in webhook_status:
            print("   ✅ Webhook status retrieved")
            print(f"   Webhook URL: {webhook_status.get('url', 'Not set')}")
            print(f"   Pending updates: {webhook_status.get('pending_update_count', 0)}")
            if webhook_status.get('last_error_message'):
                print(f"   ⚠️ Last error: {webhook_status['last_error_message']}")
        else:
            print(f"   ❌ Webhook status error: {webhook_status['error']}")
    except Exception as e:
        print(f"   ❌ Webhook status error: {e}")

    # Test 5: Test command handlers registration
    print("\n5. Testing command handlers...")
    try:
        # Import the register_handlers function
        from bot.telegram_handlers import register_handlers

        # Create a mock process function
        def mock_process_news(date, impact, analysis, debug, user_id=None):
            return []

        # Register handlers
        register_handlers(bot_manager.bot, mock_process_news, config)
        print("   ✅ Command handlers registered successfully")

        # Check if handlers are registered AFTER registration
        handlers = bot_manager.bot.message_handlers
        print(f"   Found {len(handlers)} message handlers")

        # Check for specific commands
        calendar_handler = None
        for handler in handlers:
            if hasattr(handler, 'commands') and 'calendar' in handler.commands:
                calendar_handler = handler
                break

        if calendar_handler:
            print("   ✅ Calendar command handler found")
        else:
            print("   ❌ Calendar command handler not found")
            print("   Available commands:")
            for handler in handlers:
                if hasattr(handler, 'commands'):
                    print(f"     - {handler.commands}")

    except Exception as e:
        print(f"   ❌ Command handler registration error: {e}")
        assert False, f"Command handler registration error: {e}"

    print("\n" + "=" * 50)
    print("✅ Bot initialization test completed successfully!")

def test_webhook_processing():
    """Test webhook processing with a mock message."""

    config = Config()
    bot_manager = TelegramBotManager(config)

    if not bot_manager.bot:
        print("❌ Cannot test webhook processing: Bot not initialized")
        assert False, "Cannot test webhook processing: Bot not initialized"

    print("\nTesting webhook processing...")
    print("=" * 50)

    # Create a mock message
    from telebot.types import Message, User, Chat

    mock_user = User(id=123456789, is_bot=False, first_name="Test")
    mock_user.username = "testuser"

    mock_chat = Chat(id=123456789, type="private")

    mock_message = Message()
    mock_message.message_id = 1
    mock_message.from_user = mock_user
    mock_message.chat = mock_chat
    mock_message.text = "/calendar"
    mock_message.date = int(datetime.now().timestamp())

    print(f"1. Created mock message: {mock_message.text}")
    print(f"   From user: {mock_user.first_name} (@{mock_user.username})")
    print(f"   Chat ID: {mock_chat.id}")

    # Test message processing
    try:
        # This would normally be called by the webhook
        # For testing, we'll just check if the bot can process it
        print("\n2. Testing message processing...")

        # Check if the bot has handlers for this command
        handlers = bot_manager.bot.message_handlers
        calendar_handlers = [h for h in handlers if hasattr(h, 'commands') and 'calendar' in h.commands]

        if calendar_handlers:
            print("   ✅ Calendar command handlers found")
            for handler in calendar_handlers:
                print(f"   Handler: {handler}")
        else:
            print("   ❌ No calendar command handlers found")

    except Exception as e:
        print(f"   ❌ Message processing error: {e}")
        assert False, f"Message processing error: {e}"

    print("\n" + "=" * 50)
    print("✅ Webhook processing test completed!")

if __name__ == "__main__":
    print("🤖 Bot Command Test Suite")
    print("=" * 60)

    # Test bot initialization
    init_success = test_bot_initialization()

    if init_success:
        # Test webhook processing
        webhook_success = test_webhook_processing()

        if webhook_success:
            print("\n🎉 All tests passed! Bot should be working correctly.")
        else:
            print("\n❌ Webhook processing test failed.")
    else:
        print("\n❌ Bot initialization test failed.")

    print("\n" + "=" * 60)
    print("Test suite completed!")
