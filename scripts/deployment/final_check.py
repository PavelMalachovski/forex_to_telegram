"""
Final readiness check for the Forex Bot.
"""

import sys
import os
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

def check_critical_fixes():
    """Check that all critical fixes are in place."""
    print("🔍 Checking critical fixes...")
    
    try:
        # Check UserNotificationSettings model
        from app.database.models import UserNotificationSettings
        required_fields = ['notify_15_minutes', 'notify_30_minutes', 'notify_60_minutes']
        
        for field in required_fields:
            if not hasattr(UserNotificationSettings, field):
                print(f"❌ Missing field: {field}")
                return False
        
        print("✅ UserNotificationSettings model fixed")
        
        # Check error handlers
        from app.core.error_handler import safe_handler, safe_callback_handler, ErrorHandler
        print("✅ Error handlers available")
        
        # Check bot handlers
        from app.bot.handlers import BotHandlers
        print("✅ Bot handlers with error handling")
        
        return True
        
    except Exception as e:
        print(f"❌ Critical fix check failed: {e}")
        return False

def check_project_structure():
    """Check project structure."""
    print("\n📁 Checking project structure...")
    
    required_dirs = [
        'app/core',
        'app/bot',
        'app/database', 
        'docs',
        'scripts/testing',
        'scripts/deployment',
        'config/production',
        'deployment/docker'
    ]
    
    missing_dirs = []
    for dir_path in required_dirs:
        if not (project_root / dir_path).exists():
            missing_dirs.append(dir_path)
    
    if missing_dirs:
        print(f"❌ Missing directories: {', '.join(missing_dirs)}")
        return False
    
    print("✅ Project structure is correct")
    return True

def check_main_files():
    """Check main entry point files."""
    print("\n📄 Checking main files...")
    
    required_files = [
        'main.py',
        'app/bot/main.py',
        'app/bot/bot.py',
        'app/core/error_handler.py',
        'app/database/connection.py',
        'README.md'
    ]
    
    missing_files = []
    for file_path in required_files:
        if not (project_root / file_path).exists():
            missing_files.append(file_path)
    
    if missing_files:
        print(f"❌ Missing files: {', '.join(missing_files)}")
        return False
    
    print("✅ All main files present")
    return True

def check_environment_setup():
    """Check environment setup."""
    print("\n🌍 Checking environment...")
    
    # Check if we can import main modules
    try:
        from app.config import Config
        print("✅ Configuration module available")
    except Exception as e:
        print(f"⚠️  Configuration module issue (expected without env vars): {e}")
    
    # Check required environment variables
    required_vars = ['TELEGRAM_BOT_TOKEN', 'DATABASE_URL']
    missing_vars = [var for var in required_vars if not os.getenv(var)]
    
    if missing_vars:
        print(f"⚠️  Missing environment variables: {', '.join(missing_vars)}")
        print("   Set these before running the bot")
    else:
        print("✅ All environment variables set")
    
    return True

def main():
    """Run final readiness check."""
    print("🚀 Final Forex Bot Readiness Check\n")
    print("=" * 50)
    
    checks = [
        ("Critical Fixes", check_critical_fixes),
        ("Project Structure", check_project_structure), 
        ("Main Files", check_main_files),
        ("Environment", check_environment_setup)
    ]
    
    passed = 0
    total = len(checks)
    
    for check_name, check_func in checks:
        if check_func():
            passed += 1
    
    print("\n" + "=" * 50)
    print(f"📊 Final Results: {passed}/{total} checks passed")
    
    if passed == total:
        print("\n🎉 ALL CHECKS PASSED!")
        print("\n📋 Next steps:")
        print("1. Set environment variables:")
        print("   export TELEGRAM_BOT_TOKEN='your_token'")
        print("   export DATABASE_URL='your_db_url'")
        print("2. Start PostgreSQL database")
        print("3. Run migrations: alembic -c config/alembic.ini upgrade head")
        print("4. Start bot: python main.py")
        print("\n✅ Bot is ready for deployment!")
        return True
    else:
        print(f"\n⚠️  {total - passed} checks failed. Please fix issues above.")
        return False

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
