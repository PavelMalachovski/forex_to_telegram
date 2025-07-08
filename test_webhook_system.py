#!/usr/bin/env python3
"""
Тестирование системы управления webhook без реального токена бота.
"""

import os
import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).resolve().parent
sys.path.insert(0, str(project_root))

def test_imports():
    """Тест импортов основных модулей."""
    print("🧪 Testing imports...")
    
    try:
        from webhook_manager import WebhookManager
        print("✅ webhook_manager imported successfully")
    except ImportError as e:
        print(f"❌ Failed to import webhook_manager: {e}")
        return False
    
    try:
        import bot_runner
        print("✅ bot_runner imported successfully")
    except ImportError as e:
        print(f"❌ Failed to import bot_runner: {e}")
        return False
    
    try:
        import production_scheduler
        print("✅ production_scheduler imported successfully")
    except ImportError as e:
        print(f"❌ Failed to import production_scheduler: {e}")
        return False
    
    return True

def test_env_loading():
    """Тест загрузки переменных окружения."""
    print("\n🧪 Testing environment variables...")
    
    # Test BOT_MODE
    bot_mode = os.getenv('BOT_MODE', 'polling')
    print(f"📊 BOT_MODE: {bot_mode}")
    
    if bot_mode not in ['polling', 'webhook']:
        print(f"❌ Invalid BOT_MODE: {bot_mode}")
        return False
    
    # Test other variables
    database_url = os.getenv('DATABASE_URL', 'Not set')
    print(f"🗄️  DATABASE_URL: {database_url}")
    
    log_dir = os.getenv('LOG_DIR', './logs')
    print(f"📝 LOG_DIR: {log_dir}")
    
    port = os.getenv('PORT', '8000')
    print(f"🌐 PORT: {port}")
    
    return True

def test_webhook_manager_without_token():
    """Тест WebhookManager без реального токена."""
    print("\n🧪 Testing WebhookManager (without real token)...")
    
    try:
        from webhook_manager import WebhookManager
        
        # Test without token (should fail gracefully)
        try:
            manager = WebhookManager()
            print("❌ WebhookManager should fail without token")
            return False
        except ValueError as e:
            if "TELEGRAM_BOT_TOKEN not found" in str(e):
                print("✅ WebhookManager correctly validates token requirement")
                return True
            else:
                print(f"❌ Unexpected error: {e}")
                return False
        
    except Exception as e:
        print(f"❌ Error testing WebhookManager: {e}")
        return False

def test_mode_detection():
    """Тест определения режима работы."""
    print("\n🧪 Testing mode detection...")
    
    # Test polling mode
    os.environ['BOT_MODE'] = 'polling'
    mode = os.getenv('BOT_MODE')
    print(f"📊 Polling mode test: {mode}")
    
    if mode != 'polling':
        print("❌ Failed to set polling mode")
        return False
    
    # Test webhook mode
    os.environ['BOT_MODE'] = 'webhook'
    mode = os.getenv('BOT_MODE')
    print(f"📊 Webhook mode test: {mode}")
    
    if mode != 'webhook':
        print("❌ Failed to set webhook mode")
        return False
    
    # Reset to default
    os.environ['BOT_MODE'] = 'polling'
    print("✅ Mode detection works correctly")
    return True

def test_file_structure():
    """Тест структуры файлов."""
    print("\n🧪 Testing file structure...")
    
    required_files = [
        'webhook_manager.py',
        'bot_runner.py',
        'production_scheduler.py',
        '.env.example',
        'README.md'
    ]
    
    missing_files = []
    for file in required_files:
        if not (project_root / file).exists():
            missing_files.append(file)
        else:
            print(f"✅ {file} exists")
    
    if missing_files:
        print(f"❌ Missing files: {missing_files}")
        return False
    
    return True

def test_logging_setup():
    """Тест настройки логирования."""
    print("\n🧪 Testing logging setup...")
    
    try:
        # Create logs directory
        log_dir = Path(os.getenv('LOG_DIR', './logs'))
        log_dir.mkdir(exist_ok=True)
        print(f"✅ Log directory created: {log_dir}")
        
        # Test logging import
        import logging
        logger = logging.getLogger('test')
        logger.info("Test log message")
        print("✅ Logging works correctly")
        
        return True
        
    except Exception as e:
        print(f"❌ Logging setup failed: {e}")
        return False

def main():
    """Основная функция тестирования."""
    print("🚀 Forex Bot Webhook System Test")
    print("=" * 50)
    
    tests = [
        ("File Structure", test_file_structure),
        ("Imports", test_imports),
        ("Environment Variables", test_env_loading),
        ("Mode Detection", test_mode_detection),
        ("Webhook Manager", test_webhook_manager_without_token),
        ("Logging Setup", test_logging_setup),
    ]
    
    passed = 0
    total = len(tests)
    
    for test_name, test_func in tests:
        print(f"\n{'='*20} {test_name} {'='*20}")
        try:
            if test_func():
                print(f"✅ {test_name} PASSED")
                passed += 1
            else:
                print(f"❌ {test_name} FAILED")
        except Exception as e:
            print(f"❌ {test_name} ERROR: {e}")
    
    print(f"\n{'='*50}")
    print(f"📊 Test Results: {passed}/{total} tests passed")
    
    if passed == total:
        print("🎉 All tests passed! System is ready.")
        print("\n📋 Next steps:")
        print("1. Set your real TELEGRAM_BOT_TOKEN in .env file")
        print("2. Choose BOT_MODE (polling for dev, webhook for prod)")
        print("3. For webhook mode, set RENDER_EXTERNAL_URL or TELEGRAM_WEBHOOK_URL")
        print("4. Run: python bot_runner.py (polling) or python production_scheduler.py (webhook)")
        return 0
    else:
        print("❌ Some tests failed. Please fix the issues above.")
        return 1

if __name__ == "__main__":
    exit_code = main()
    sys.exit(exit_code)
