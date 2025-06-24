#!/usr/bin/env python3
"""
Test script to verify ChatGPT and timezone fixes.
"""

import os
import sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'app'))

from app.config import config
from app.utils.timezone_utils import get_current_time, get_current_time_iso, format_time_for_display
from app.services.analysis_service import AnalysisService
from datetime import datetime
import pytz

def test_timezone_fixes():
    """Test timezone functionality."""
    print("=== Testing Timezone Fixes ===")
    
    # Test current timezone configuration
    print(f"Configured timezone: {config.TIMEZONE}")
    
    # Test current time functions
    current_time = get_current_time()
    current_time_iso = get_current_time_iso()
    
    print(f"Current time (with timezone): {current_time}")
    print(f"Current time (ISO): {current_time_iso}")
    print(f"Timezone info: {current_time.tzinfo}")
    
    # Test time formatting
    formatted_time = format_time_for_display(current_time)
    print(f"Formatted time for display: {formatted_time}")
    
    # Test UTC conversion
    utc_time = datetime.now(pytz.UTC)
    local_time = current_time
    time_diff = (local_time.replace(tzinfo=None) - utc_time.replace(tzinfo=None)).total_seconds() / 3600
    print(f"Time difference from UTC: {time_diff} hours")
    
    print("✅ Timezone tests completed\n")

def test_chatgpt_integration():
    """Test ChatGPT integration."""
    print("=== Testing ChatGPT Integration ===")
    
    # Test API key configuration
    print(f"OpenAI API Key configured: {'Yes' if config.OPENAI_API_KEY and not config.OPENAI_API_KEY.startswith('your_') else 'No'}")
    print(f"API Key (masked): {'*' * 20 if config.OPENAI_API_KEY and not config.OPENAI_API_KEY.startswith('your_') else config.OPENAI_API_KEY}")
    
    # Test analysis service
    analysis_service = AnalysisService()
    
    # Test single event analysis (should show proper error message)
    result = analysis_service.analyze_single_event(
        currency="EUR",
        event_name="Test Event",
        forecast="1.0%",
        previous="0.8%",
        actual="1.2%"
    )
    
    print(f"Analysis result: {result}")
    
    # Test combined events analysis
    test_events = [
        {
            'currency': 'USD',
            'event_name': 'Test Event 1',
            'forecast': '1.0%',
            'previous': '0.8%',
            'actual': '1.2%'
        }
    ]
    
    combined_result = analysis_service.analyze_combined_events(test_events)
    print(f"Combined analysis result: {combined_result}")
    
    print("✅ ChatGPT integration tests completed\n")

def test_configuration():
    """Test configuration values."""
    print("=== Testing Configuration ===")
    
    print(f"Database URL: {config.DATABASE_URL}")
    print(f"Telegram Bot Token configured: {'Yes' if config.TELEGRAM_BOT_TOKEN and not config.TELEGRAM_BOT_TOKEN.startswith('your_') else 'No'}")
    print(f"OpenAI API Key configured: {'Yes' if config.OPENAI_API_KEY and not config.OPENAI_API_KEY.startswith('your_') else 'No'}")
    print(f"Timezone: {config.TIMEZONE}")
    print(f"Flask Port: {config.FLASK_PORT}")
    print(f"Is Production: {config.is_production()}")
    print(f"Is Webhook Mode: {config.is_webhook_mode()}")
    
    print("✅ Configuration tests completed\n")

if __name__ == "__main__":
    print("🔧 Testing Forex Bot Fixes\n")
    
    test_configuration()
    test_timezone_fixes()
    test_chatgpt_integration()
    
    print("🎉 All tests completed!")
    print("\n📝 Next steps:")
    print("1. Update .env.production with real API keys")
    print("2. Set OPENAI_API_KEY environment variable")
    print("3. Deploy to production")
    print("4. Test with real Telegram bot")
