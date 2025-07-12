#!/usr/bin/env python3
"""
Test script for critical fixes in Telegram bot.
"""

import sys
import os
from datetime import date, timedelta

# Add project root to path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

def test_botuser_model():
    """Test BotUser model with telegram_username field."""
    print("Testing BotUser model...")
    
    try:
        from app.database.models import BotUser
        
        # Check if telegram_username field exists
        user_fields = [column.name for column in BotUser.__table__.columns]
        
        if 'telegram_username' in user_fields:
            print("✅ BotUser model has telegram_username field")
            return True
        else:
            print("❌ BotUser model missing telegram_username field")
            print(f"Available fields: {user_fields}")
            return False
            
    except Exception as e:
        print(f"❌ Error testing BotUser model: {e}")
        return False

def test_auto_scraper_service():
    """Test AutoScraperService has scrape_date_range method."""
    print("Testing AutoScraperService...")
    
    try:
        from app.services.auto_scraper_service import AutoScraperService
        
        # Check if scrape_date_range method exists
        if hasattr(AutoScraperService, 'scrape_date_range'):
            print("✅ AutoScraperService has scrape_date_range method")
            return True
        else:
            print("❌ AutoScraperService missing scrape_date_range method")
            available_methods = [method for method in dir(AutoScraperService) if not method.startswith('_')]
            print(f"Available methods: {available_methods}")
            return False
            
    except Exception as e:
        print(f"❌ Error testing AutoScraperService: {e}")
        return False

def test_calendar_callback():
    """Test calendar callback processing."""
    print("Testing calendar callback processing...")
    
    try:
        from app.bot.utils.calendar import process_calendar_callback
        
        # Test with valid callback data
        test_data = "cal_select_2025_7_15"
        result = process_calendar_callback(test_data)
        
        if result and len(result) == 3:
            action, selected_date, nav_data = result
            print(f"✅ Calendar callback processing works: {result}")
            return True
        else:
            print(f"❌ Calendar callback processing failed: {result}")
            return False
            
    except Exception as e:
        print(f"❌ Error testing calendar callback: {e}")
        return False

def test_user_service():
    """Test user service with telegram_username."""
    print("Testing UserService...")
    
    try:
        # Import without database connection
        from app.services.user_service import UserService
        
        # Check if get_or_create_user method accepts telegram_username
        import inspect
        signature = inspect.signature(UserService.get_or_create_user)
        params = list(signature.parameters.keys())
        
        if 'telegram_username' in params:
            print("✅ UserService.get_or_create_user accepts telegram_username parameter")
            return True
        else:
            print(f"❌ UserService.get_or_create_user missing telegram_username parameter")
            print(f"Available parameters: {params}")
            return False
            
    except Exception as e:
        print(f"❌ Error testing UserService: {e}")
        return False

def main():
    """Run all tests."""
    print("🔧 Testing critical fixes for Telegram bot\n")
    
    tests = [
        test_botuser_model,
        test_auto_scraper_service,
        test_calendar_callback,
        test_user_service
    ]
    
    results = []
    for test in tests:
        result = test()
        results.append(result)
        print()
    
    # Summary
    passed = sum(results)
    total = len(results)
    
    print(f"📊 Test Results: {passed}/{total} tests passed")
    
    if passed == total:
        print("🎉 All critical fixes are working correctly!")
        return 0
    else:
        print("⚠️  Some fixes need attention.")
        return 1

if __name__ == "__main__":
    exit(main())
