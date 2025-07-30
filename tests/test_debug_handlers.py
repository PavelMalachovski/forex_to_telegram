#!/usr/bin/env python3
"""
Debug script to check what handlers are being registered.
"""

import sys
import os
import logging

# Add the parent directory to the path to import bot modules
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from bot.config import Config
from bot.telegram_handlers import TelegramBotManager, register_handlers

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(name)s: %(message)s'
)

def debug_handlers():
    """Debug handler registration."""

    config = Config()
    bot_manager = TelegramBotManager(config)

    if not bot_manager.bot:
        print("❌ Bot not initialized")
        return

    print("🔍 Debugging handler registration...")
    print("=" * 50)

    # Check handlers before registration
    print("1. Handlers BEFORE registration:")
    handlers_before = bot_manager.bot.message_handlers
    print(f"   Found {len(handlers_before)} handlers")
    for i, handler in enumerate(handlers_before):
        print(f"   Handler {i}: {handler}")
        if hasattr(handler, 'commands'):
            print(f"     Commands: {handler.commands}")

    # Register handlers
    print("\n2. Registering handlers...")
    def mock_process_news(date, impact, analysis, debug, user_id=None):
        return []

    register_handlers(bot_manager.bot, mock_process_news, config)

    # Check handlers after registration
    print("\n3. Handlers AFTER registration:")
    handlers_after = bot_manager.bot.message_handlers
    print(f"   Found {len(handlers_after)} handlers")

    for i, handler in enumerate(handlers_after):
        print(f"   Handler {i}: {handler}")
        # Check if it's a dictionary (which it appears to be)
        if isinstance(handler, dict):
            print(f"     Type: Dictionary")
            print(f"     Function: {handler.get('function', 'N/A')}")
            print(f"     Filters: {handler.get('filters', 'N/A')}")
            if 'filters' in handler and 'commands' in handler['filters']:
                print(f"     Commands: {handler['filters']['commands']}")
        elif hasattr(handler, 'commands'):
            print(f"     Commands: {handler.commands}")
        if hasattr(handler, 'func'):
            print(f"     Function: {handler.func.__name__}")

    # Look specifically for calendar handler
    print("\n4. Looking for calendar handler...")
    calendar_handlers = []
    for handler in handlers_after:
        # Check if it's a dictionary with commands
        if isinstance(handler, dict) and 'filters' in handler and 'commands' in handler['filters']:
            if 'calendar' in handler['filters']['commands']:
                calendar_handlers.append(handler)
        # Check if it's an object with commands attribute
        elif hasattr(handler, 'commands') and 'calendar' in handler.commands:
            calendar_handlers.append(handler)

    if calendar_handlers:
        print(f"   ✅ Found {len(calendar_handlers)} calendar handler(s)")
        for handler in calendar_handlers:
            print(f"     Handler: {handler}")
            if isinstance(handler, dict):
                print(f"     Function: {handler.get('function', 'N/A')}")
            elif hasattr(handler, 'func'):
                print(f"     Function: {handler.func.__name__}")
    else:
        print("   ❌ No calendar handlers found")

        # Check all commands
        all_commands = []
        for handler in handlers_after:
            if isinstance(handler, dict) and 'filters' in handler and 'commands' in handler['filters']:
                all_commands.extend(handler['filters']['commands'])
            elif hasattr(handler, 'commands'):
                all_commands.extend(handler.commands)

        print(f"   Available commands: {all_commands}")

    print("\n" + "=" * 50)
    print("Debug completed!")

if __name__ == "__main__":
    debug_handlers()
