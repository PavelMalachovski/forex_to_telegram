
#!/usr/bin/env python3
"""
Telegram Bot Webhook Manager
Управление webhook для Telegram бота с поддержкой разных режимов работы.
"""

import os
import sys
import requests
import time
import argparse
from pathlib import Path

# Add project root to path
project_root = Path(__file__).resolve().parent
sys.path.insert(0, str(project_root))

class WebhookManager:
    """Класс для управления webhook Telegram бота."""
    
    def __init__(self):
        self.bot_token = os.getenv('TELEGRAM_BOT_TOKEN')
        if not self.bot_token:
            raise ValueError("TELEGRAM_BOT_TOKEN not found in environment variables")
        
        self.base_url = f"https://api.telegram.org/bot{self.bot_token}"
        
        # Определяем webhook URL
        self.webhook_url = self._get_webhook_url()
    
    def _get_webhook_url(self):
        """Получить URL для webhook."""
        # Приоритет: TELEGRAM_WEBHOOK_URL > RENDER_EXTERNAL_URL > локальный URL
        webhook_url = os.getenv('TELEGRAM_WEBHOOK_URL')
        if webhook_url:
            return webhook_url
        
        render_url = os.getenv('RENDER_EXTERNAL_URL')
        if render_url:
            return f"{render_url}/webhook"
        
        # Для локальной разработки (если используется ngrok или подобное)
        local_webhook = os.getenv('LOCAL_WEBHOOK_URL')
        if local_webhook:
            return f"{local_webhook}/webhook"
        
        return None
    
    def get_webhook_info(self):
        """Получить информацию о текущем webhook."""
        try:
            response = requests.get(f"{self.base_url}/getWebhookInfo", timeout=10)
            response.raise_for_status()
            
            result = response.json()
            if result.get('ok'):
                return result.get('result', {})
            else:
                print(f"❌ API Error: {result.get('description', 'Unknown error')}")
                return None
                
        except requests.RequestException as e:
            print(f"❌ Network error getting webhook info: {e}")
            return None
        except Exception as e:
            print(f"❌ Unexpected error getting webhook info: {e}")
            return None
    
    def delete_webhook(self):
        """Удалить webhook."""
        try:
            print("🗑️  Deleting webhook...")
            response = requests.post(f"{self.base_url}/deleteWebhook", timeout=10)
            response.raise_for_status()
            
            result = response.json()
            if result.get('ok'):
                print("✅ Webhook deleted successfully")
                return True
            else:
                print(f"❌ Failed to delete webhook: {result.get('description', 'Unknown error')}")
                return False
                
        except requests.RequestException as e:
            print(f"❌ Network error deleting webhook: {e}")
            return False
        except Exception as e:
            print(f"❌ Unexpected error deleting webhook: {e}")
            return False
    
    def set_webhook(self, url=None):
        """Установить webhook."""
        webhook_url = url or self.webhook_url
        
        if not webhook_url:
            print("❌ No webhook URL available. Set TELEGRAM_WEBHOOK_URL, RENDER_EXTERNAL_URL, or LOCAL_WEBHOOK_URL")
            return False
        
        try:
            print(f"🔗 Setting webhook: {webhook_url}")
            
            webhook_data = {
                'url': webhook_url,
                'max_connections': 40,
                'allowed_updates': ['message', 'callback_query'],
                'drop_pending_updates': True  # Очищаем старые обновления
            }
            
            response = requests.post(f"{self.base_url}/setWebhook", json=webhook_data, timeout=10)
            response.raise_for_status()
            
            result = response.json()
            if result.get('ok'):
                print("✅ Webhook set successfully!")
                return True
            else:
                print(f"❌ Failed to set webhook: {result.get('description', 'Unknown error')}")
                return False
                
        except requests.RequestException as e:
            print(f"❌ Network error setting webhook: {e}")
            return False
        except Exception as e:
            print(f"❌ Unexpected error setting webhook: {e}")
            return False
    
    def check_status(self):
        """Проверить статус webhook."""
        print("📊 Checking webhook status...")
        print("=" * 50)
        
        webhook_info = self.get_webhook_info()
        if webhook_info is None:
            return False
        
        url = webhook_info.get('url', '')
        if url:
            print(f"🔗 Webhook URL: {url}")
            print(f"📊 Status: ✅ ACTIVE")
        else:
            print("📊 Status: ❌ NO WEBHOOK SET")
        
        print(f"🔒 Has custom certificate: {webhook_info.get('has_custom_certificate', False)}")
        print(f"📬 Pending updates: {webhook_info.get('pending_update_count', 0)}")
        print(f"🔌 Max connections: {webhook_info.get('max_connections', 'Not set')}")
        print(f"📝 Allowed updates: {webhook_info.get('allowed_updates', 'All')}")
        
        if webhook_info.get('last_error_date'):
            print(f"⚠️  Last error: {webhook_info.get('last_error_message', 'Unknown')}")
            print(f"📅 Last error date: {webhook_info.get('last_error_date')}")
        
        return True
    
    def reset_webhook(self):
        """Сбросить webhook (удалить и установить заново)."""
        print("🔄 Resetting webhook...")
        
        # Удаляем существующий webhook
        if not self.delete_webhook():
            return False
        
        # Ждем немного
        time.sleep(2)
        
        # Устанавливаем новый webhook
        return self.set_webhook()

def main():
    """Основная функция с CLI интерфейсом."""
    parser = argparse.ArgumentParser(
        description="Telegram Bot Webhook Manager",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python webhook_manager.py status          # Check webhook status
  python webhook_manager.py delete          # Delete webhook (enable polling)
  python webhook_manager.py set             # Set webhook (disable polling)
  python webhook_manager.py reset           # Reset webhook (delete + set)
  python webhook_manager.py set --url URL   # Set custom webhook URL

Environment Variables:
  TELEGRAM_BOT_TOKEN      - Required: Bot token from @BotFather
  TELEGRAM_WEBHOOK_URL    - Optional: Full webhook URL
  RENDER_EXTERNAL_URL     - Optional: Render service URL (auto-adds /webhook)
  LOCAL_WEBHOOK_URL       - Optional: Local development webhook URL
        """
    )
    
    parser.add_argument(
        'command',
        choices=['status', 'delete', 'set', 'reset'],
        help='Command to execute'
    )
    
    parser.add_argument(
        '--url',
        help='Custom webhook URL (only for set command)'
    )
    
    args = parser.parse_args()
    
    print("🤖 Telegram Bot Webhook Manager")
    print("=" * 50)
    
    try:
        manager = WebhookManager()
        
        if args.command == 'status':
            success = manager.check_status()
        elif args.command == 'delete':
            success = manager.delete_webhook()
        elif args.command == 'set':
            success = manager.set_webhook(args.url)
            if success:
                print("\n🔍 Checking status after setting webhook...")
                manager.check_status()
        elif args.command == 'reset':
            success = manager.reset_webhook()
            if success:
                print("\n🔍 Checking status after reset...")
                manager.check_status()
        else:
            print(f"❌ Unknown command: {args.command}")
            success = False
        
        if success:
            print(f"\n✅ Command '{args.command}' completed successfully!")
            sys.exit(0)
        else:
            print(f"\n❌ Command '{args.command}' failed!")
            sys.exit(1)
            
    except ValueError as e:
        print(f"❌ Configuration error: {e}")
        print("\n💡 Make sure TELEGRAM_BOT_TOKEN is set in your environment")
        sys.exit(1)
    except KeyboardInterrupt:
        print("\n\n⚠️  Operation cancelled by user")
        sys.exit(1)
    except Exception as e:
        print(f"❌ Unexpected error: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()
