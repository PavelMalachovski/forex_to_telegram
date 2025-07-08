#!/usr/bin/env python3
"""
Быстрый запуск Forex Bot с автоматическим определением режима и исправлением конфликтов.
"""

import os
import sys
import subprocess
from pathlib import Path

# Add project root to path
project_root = Path(__file__).resolve().parent
sys.path.insert(0, str(project_root))

def load_env_file():
    """Загрузить переменные из .env файла."""
    env_file = project_root / '.env'
    if env_file.exists():
        with open(env_file, 'r') as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith('#') and '=' in line:
                    key, value = line.split('=', 1)
                    os.environ[key] = value

def check_token():
    """Проверить токен бота."""
    token = os.getenv('TELEGRAM_BOT_TOKEN')
    return token and token != 'your_telegram_bot_token_here'

def get_bot_mode():
    """Получить режим работы бота."""
    return os.getenv('BOT_MODE', 'polling').lower()

def run_command(command, description):
    """Запустить команду с описанием."""
    print(f"🔄 {description}...")
    try:
        result = subprocess.run(command, shell=True, capture_output=True, text=True)
        if result.returncode == 0:
            print(f"✅ {description} completed")
            if result.stdout.strip():
                print(result.stdout)
            return True
        else:
            print(f"❌ {description} failed")
            if result.stderr.strip():
                print(result.stderr)
            return False
    except Exception as e:
        print(f"❌ Error running command: {e}")
        return False

def setup_polling_mode():
    """Настроить polling режим."""
    print("\n🔄 Setting up POLLING mode...")
    
    # Delete webhook if exists
    if check_token():
        run_command("python webhook_manager.py delete", "Deleting webhook")
    
    # Set environment
    os.environ['BOT_MODE'] = 'polling'
    
    print("✅ Polling mode configured")
    print("📋 Starting bot in polling mode...")
    
    # Start bot
    try:
        subprocess.run([sys.executable, "bot_runner.py"], check=False)
    except KeyboardInterrupt:
        print("\n⚠️  Bot stopped by user")

def setup_webhook_mode():
    """Настроить webhook режим."""
    print("\n🔗 Setting up WEBHOOK mode...")
    
    # Check webhook URL
    webhook_url = (
        os.getenv('TELEGRAM_WEBHOOK_URL') or
        os.getenv('RENDER_EXTERNAL_URL') or
        os.getenv('LOCAL_WEBHOOK_URL')
    )
    
    if not webhook_url:
        print("❌ No webhook URL configured!")
        print("💡 Please set one of:")
        print("   - TELEGRAM_WEBHOOK_URL")
        print("   - RENDER_EXTERNAL_URL")
        print("   - LOCAL_WEBHOOK_URL")
        return False
    
    # Set environment
    os.environ['BOT_MODE'] = 'webhook'
    
    # Setup webhook
    if check_token():
        run_command("python webhook_manager.py set", "Setting up webhook")
    
    print("✅ Webhook mode configured")
    print("📋 Starting bot in webhook mode...")
    
    # Start bot
    try:
        subprocess.run([sys.executable, "production_scheduler.py"], check=False)
    except KeyboardInterrupt:
        print("\n⚠️  Bot stopped by user")
    
    return True

def interactive_mode_selection():
    """Интерактивный выбор режима."""
    print("\n🤖 Forex Bot Quick Start")
    print("=" * 40)
    
    current_mode = get_bot_mode()
    print(f"📊 Current mode: {current_mode.upper()}")
    
    print("\nSelect mode:")
    print("1. 🔄 Polling (for development)")
    print("2. 🔗 Webhook (for production)")
    print("3. 🔧 Fix 409 conflict")
    print("4. 📊 Check status")
    print("5. ❌ Exit")
    
    while True:
        choice = input("\nEnter your choice (1-5): ").strip()
        
        if choice == '1':
            setup_polling_mode()
            break
        elif choice == '2':
            if setup_webhook_mode():
                break
        elif choice == '3':
            run_command("python fix_409_conflict.py fix", "Fixing 409 conflict")
        elif choice == '4':
            if check_token():
                run_command("python webhook_manager.py status", "Checking webhook status")
            else:
                print("❌ Token not configured")
        elif choice == '5':
            print("👋 Goodbye!")
            break
        else:
            print("❌ Invalid choice. Please enter 1-5")

def auto_mode():
    """Автоматический режим на основе переменных окружения."""
    mode = get_bot_mode()
    
    print(f"🚀 Auto-starting in {mode.upper()} mode...")
    
    if mode == 'polling':
        setup_polling_mode()
    elif mode == 'webhook':
        setup_webhook_mode()
    else:
        print(f"❌ Invalid mode: {mode}")
        return False
    
    return True

def main():
    """Основная функция."""
    # Load environment variables
    load_env_file()
    
    print("🤖 Forex Bot Quick Start")
    print("=" * 50)
    
    # Check token
    if not check_token():
        print("❌ TELEGRAM_BOT_TOKEN not configured!")
        print("💡 Please set your bot token in .env file")
        print("📝 Copy .env.example to .env and edit it")
        return 1
    
    # Parse command line arguments
    if len(sys.argv) > 1:
        command = sys.argv[1].lower()
        
        if command == 'polling':
            setup_polling_mode()
        elif command == 'webhook':
            setup_webhook_mode()
        elif command == 'auto':
            auto_mode()
        elif command == 'fix':
            run_command("python fix_409_conflict.py fix", "Fixing 409 conflict")
        elif command == 'status':
            run_command("python webhook_manager.py status", "Checking status")
        else:
            print(f"❌ Unknown command: {command}")
            print("Available commands: polling, webhook, auto, fix, status")
            return 1
    else:
        # Interactive mode
        interactive_mode_selection()
    
    return 0

if __name__ == "__main__":
    try:
        exit_code = main()
        sys.exit(exit_code)
    except KeyboardInterrupt:
        print("\n\n⚠️  Operation cancelled by user")
        sys.exit(1)
