#!/usr/bin/env python3
"""
Скрипт для исправления конфликта 409: Conflict webhook/polling
Автоматически определяет проблему и предлагает решения.
"""

import os
import sys
import requests
from pathlib import Path

# Add project root to path
project_root = Path(__file__).resolve().parent
sys.path.insert(0, str(project_root))

def check_bot_token():
    """Проверить наличие токена бота."""
    token = os.getenv('TELEGRAM_BOT_TOKEN')
    if not token or token == 'your_telegram_bot_token_here':
        print("❌ TELEGRAM_BOT_TOKEN not configured properly")
        print("💡 Please set your real bot token in .env file")
        return None
    return token

def get_webhook_info(token):
    """Получить информацию о webhook."""
    try:
        response = requests.get(f"https://api.telegram.org/bot{token}/getWebhookInfo", timeout=10)
        if response.status_code == 200:
            result = response.json()
            if result.get('ok'):
                return result.get('result', {})
    except Exception as e:
        print(f"❌ Error getting webhook info: {e}")
    return None

def delete_webhook(token):
    """Удалить webhook."""
    try:
        response = requests.post(f"https://api.telegram.org/bot{token}/deleteWebhook", timeout=10)
        if response.status_code == 200:
            result = response.json()
            return result.get('ok', False)
    except Exception as e:
        print(f"❌ Error deleting webhook: {e}")
    return False

def diagnose_409_conflict():
    """Диагностировать конфликт 409."""
    print("🔍 Diagnosing 409 Conflict: webhook vs polling")
    print("=" * 60)
    
    # Check token
    token = check_bot_token()
    if not token:
        return False
    
    # Get webhook info
    print("📊 Checking current webhook status...")
    webhook_info = get_webhook_info(token)
    
    if webhook_info is None:
        print("❌ Could not get webhook information")
        return False
    
    webhook_url = webhook_info.get('url', '')
    pending_updates = webhook_info.get('pending_update_count', 0)
    
    print(f"🔗 Webhook URL: {webhook_url if webhook_url else 'Not set'}")
    print(f"📬 Pending updates: {pending_updates}")
    
    # Determine the problem
    if webhook_url:
        print("\n🚨 PROBLEM IDENTIFIED:")
        print("   Webhook is active, but your code is trying to use polling (getUpdates)")
        print("   This causes the 409 Conflict error")
        
        print("\n💡 SOLUTIONS:")
        print("   1. Switch to webhook mode (recommended for production)")
        print("   2. Delete webhook and use polling mode (for development)")
        
        return True
    else:
        print("\n✅ No webhook is set - polling should work fine")
        print("   If you're still getting 409 errors, check your code for:")
        print("   - Multiple bot instances running")
        print("   - Mixed polling/webhook calls")
        return False

def fix_conflict_interactive():
    """Интерактивное исправление конфликта."""
    token = check_bot_token()
    if not token:
        return False
    
    webhook_info = get_webhook_info(token)
    if not webhook_info:
        return False
    
    webhook_url = webhook_info.get('url', '')
    
    if not webhook_url:
        print("✅ No webhook conflict detected")
        return True
    
    print(f"\n🔗 Active webhook detected: {webhook_url}")
    print("\nChoose your solution:")
    print("1. Delete webhook (enable polling mode)")
    print("2. Keep webhook (switch to webhook mode)")
    print("3. Cancel")
    
    while True:
        choice = input("\nEnter your choice (1-3): ").strip()
        
        if choice == '1':
            print("\n🗑️  Deleting webhook...")
            if delete_webhook(token):
                print("✅ Webhook deleted successfully!")
                print("📋 Next steps:")
                print("   - Set BOT_MODE=polling in your .env file")
                print("   - Run: python bot_runner.py")
                return True
            else:
                print("❌ Failed to delete webhook")
                return False
        
        elif choice == '2':
            print("\n🔗 Keeping webhook active")
            print("📋 Next steps:")
            print("   - Set BOT_MODE=webhook in your .env file")
            print("   - Set RENDER_EXTERNAL_URL or TELEGRAM_WEBHOOK_URL")
            print("   - Run: python production_scheduler.py")
            return True
        
        elif choice == '3':
            print("❌ Operation cancelled")
            return False
        
        else:
            print("❌ Invalid choice. Please enter 1, 2, or 3")

def main():
    """Основная функция."""
    print("🚨 Forex Bot 409 Conflict Fixer")
    print("=" * 50)
    
    if len(sys.argv) > 1:
        command = sys.argv[1].lower()
        
        if command == 'diagnose':
            success = diagnose_409_conflict()
        elif command == 'fix':
            success = fix_conflict_interactive()
        elif command == 'delete-webhook':
            token = check_bot_token()
            if token:
                print("🗑️  Deleting webhook...")
                success = delete_webhook(token)
                if success:
                    print("✅ Webhook deleted! You can now use polling mode.")
                else:
                    print("❌ Failed to delete webhook")
            else:
                success = False
        else:
            print(f"❌ Unknown command: {command}")
            success = False
    else:
        print("Usage:")
        print("  python fix_409_conflict.py diagnose        - Analyze the problem")
        print("  python fix_409_conflict.py fix             - Interactive fix")
        print("  python fix_409_conflict.py delete-webhook  - Force delete webhook")
        print("\nCommon 409 error:")
        print("  'Conflict: can't use getUpdates method while webhook is active'")
        success = True
    
    return 0 if success else 1

if __name__ == "__main__":
    exit_code = main()
    sys.exit(exit_code)
