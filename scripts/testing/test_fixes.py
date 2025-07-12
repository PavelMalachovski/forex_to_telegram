
"""
Test script to verify critical fixes.
"""

import sys
import os
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

def test_imports():
    """Test that all critical imports work."""
    try:
        from app.core.error_handler import safe_handler, safe_callback_handler, ErrorHandler
        from app.bot.handlers import BotHandlers
        from app.database.models import UserNotificationSettings
        print("✅ All imports successful")
        return True
    except Exception as e:
        print(f"❌ Import error: {e}")
        return False

def test_notification_model():
    """Test UserNotificationSettings model has required fields."""
    try:
        from app.database.models import UserNotificationSettings
        
        required_fields = [
            'notify_15_minutes',
            'notify_30_minutes', 
            'notify_60_minutes',
            'notifications_enabled'
        ]
        
        for field in required_fields:
            if not hasattr(UserNotificationSettings, field):
                print(f"❌ Missing field: {field}")
                return False
        
        print("✅ UserNotificationSettings model has all required fields")
        return True
    except Exception as e:
        print(f"❌ Model test error: {e}")
        return False

def test_error_handlers():
    """Test error handler decorators."""
    try:
        from app.core.error_handler import safe_handler, safe_callback_handler
        
        @safe_handler("Test error message")
        def test_function():
            return "success"
        
        @safe_callback_handler("Test callback error")
        def test_callback():
            return "callback success"
        
        result1 = test_function()
        result2 = test_callback()
        
        print("✅ Error handler decorators work correctly")
        return True
    except Exception as e:
        print(f"❌ Error handler test failed: {e}")
        return False

def test_project_structure():
    """Test that project structure is correct."""
    try:
        required_dirs = [
            'app/core',
            'app/bot', 
            'app/database',
            'app/services',
            'docs',
            'scripts/testing',
            'scripts/deployment',
            'config/production',
            'deployment/docker'
        ]
        
        for dir_path in required_dirs:
            full_path = project_root / dir_path
            if not full_path.exists():
                print(f"❌ Missing directory: {dir_path}")
                return False
        
        print("✅ Project structure is correct")
        return True
    except Exception as e:
        print(f"❌ Structure test error: {e}")
        return False

def main():
    """Run all tests."""
    print("🔍 Testing critical fixes...\n")
    
    tests = [
        ("Import Tests", test_imports),
        ("Notification Model", test_notification_model),
        ("Error Handlers", test_error_handlers),
        ("Project Structure", test_project_structure)
    ]
    
    passed = 0
    total = len(tests)
    
    for test_name, test_func in tests:
        print(f"Running {test_name}...")
        if test_func():
            passed += 1
        print()
    
    print(f"📊 Results: {passed}/{total} tests passed")
    
    if passed == total:
        print("🎉 All critical fixes verified successfully!")
        return True
    else:
        print("⚠️  Some tests failed. Please check the issues above.")
        return False

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
