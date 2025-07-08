#!/usr/bin/env python3
"""
Script to setup webhook for Telegram bot deployment.
"""

import os
import sys
import requests
import time
from pathlib import Path

# Add project root to path
project_root = Path(__file__).resolve().parent
sys.path.insert(0, str(project_root))

def setup_webhook():
    """Setup webhook for Telegram bot."""
    
    # Get bot token
    bot_token = os.getenv('TELEGRAM_BOT_TOKEN')
    if not bot_token:
        print("❌ TELEGRAM_BOT_TOKEN not found in environment")
        return False
    
    # Get webhook URL
    webhook_url = os.getenv('TELEGRAM_WEBHOOK_URL')
    render_url = os.getenv('RENDER_EXTERNAL_URL')
    
    if webhook_url:
        full_webhook_url = webhook_url
    elif render_url:
        full_webhook_url = f"{render_url}/webhook"
    else:
        print("❌ Neither TELEGRAM_WEBHOOK_URL nor RENDER_EXTERNAL_URL found")
        return False
    
    print(f"🔧 Setting up webhook: {full_webhook_url}")
    
    # Telegram API URLs
    base_url = f"https://api.telegram.org/bot{bot_token}"
    
    try:
        # First, delete any existing webhook
        print("🗑️  Removing existing webhook...")
        delete_response = requests.post(f"{base_url}/deleteWebhook")
        
        if delete_response.status_code == 200:
            print("✅ Existing webhook removed")
        else:
            print(f"⚠️  Failed to remove existing webhook: {delete_response.text}")
        
        # Wait a moment
        time.sleep(2)
        
        # Set new webhook
        print(f"🔗 Setting new webhook: {full_webhook_url}")
        webhook_data = {
            'url': full_webhook_url,
            'max_connections': 40,
            'allowed_updates': ['message', 'callback_query']
        }
        
        set_response = requests.post(f"{base_url}/setWebhook", json=webhook_data)
        
        if set_response.status_code == 200:
            result = set_response.json()
            if result.get('ok'):
                print("✅ Webhook set successfully!")
                return True
            else:
                print(f"❌ Failed to set webhook: {result.get('description')}")
                return False
        else:
            print(f"❌ HTTP error setting webhook: {set_response.status_code}")
            return False
            
    except Exception as e:
        print(f"❌ Error setting up webhook: {e}")
        return False

def check_webhook_status():
    """Check current webhook status."""
    
    bot_token = os.getenv('TELEGRAM_BOT_TOKEN')
    if not bot_token:
        print("❌ TELEGRAM_BOT_TOKEN not found in environment")
        return
    
    base_url = f"https://api.telegram.org/bot{bot_token}"
    
    try:
        response = requests.get(f"{base_url}/getWebhookInfo")
        
        if response.status_code == 200:
            result = response.json()
            if result.get('ok'):
                webhook_info = result.get('result', {})
                
                print("📊 Current Webhook Status:")
                print(f"   URL: {webhook_info.get('url', 'Not set')}")
                print(f"   Has custom certificate: {webhook_info.get('has_custom_certificate', False)}")
                print(f"   Pending update count: {webhook_info.get('pending_update_count', 0)}")
                print(f"   Max connections: {webhook_info.get('max_connections', 'Not set')}")
                print(f"   Allowed updates: {webhook_info.get('allowed_updates', 'All')}")
                
                if webhook_info.get('last_error_date'):
                    print(f"   Last error: {webhook_info.get('last_error_message', 'Unknown')}")
                    print(f"   Last error date: {webhook_info.get('last_error_date')}")
                
                return webhook_info
            else:
                print(f"❌ Failed to get webhook info: {result.get('description')}")
        else:
            print(f"❌ HTTP error getting webhook info: {response.status_code}")
            
    except Exception as e:
        print(f"❌ Error checking webhook status: {e}")
    
    return None

def main():
    """Main function."""
    print("🚀 Telegram Bot Webhook Setup")
    print("=" * 50)
    
    if len(sys.argv) > 1:
        command = sys.argv[1].lower()
        
        if command == 'status':
            check_webhook_status()
        elif command == 'setup':
            success = setup_webhook()
            if success:
                print("\n✅ Webhook setup completed successfully!")
                print("🔍 Checking status...")
                check_webhook_status()
            else:
                print("\n❌ Webhook setup failed!")
                sys.exit(1)
        elif command == 'delete':
            bot_token = os.getenv('TELEGRAM_BOT_TOKEN')
            if bot_token:
                base_url = f"https://api.telegram.org/bot{bot_token}"
                response = requests.post(f"{base_url}/deleteWebhook")
                if response.status_code == 200:
                    print("✅ Webhook deleted successfully!")
                else:
                    print("❌ Failed to delete webhook")
            else:
                print("❌ TELEGRAM_BOT_TOKEN not found")
        else:
            print(f"❌ Unknown command: {command}")
            print("Available commands: status, setup, delete")
    else:
        print("Usage:")
        print("  python setup_webhook.py status  - Check current webhook status")
        print("  python setup_webhook.py setup   - Setup webhook")
        print("  python setup_webhook.py delete  - Delete webhook")

if __name__ == "__main__":
    main()
