
#!/usr/bin/env python3
"""
Script for managing Telegram bot webhooks.
Usage:
    python manage_webhook.py status          # Show current webhook status
    python manage_webhook.py set <url>       # Set webhook to specific URL
    python manage_webhook.py set-render      # Set webhook for Render.com
    python manage_webhook.py delete          # Delete current webhook
"""

import sys
import argparse
from webhook_utils import WebhookManager

def main():
    parser = argparse.ArgumentParser(description='Manage Telegram bot webhooks')
    parser.add_argument('action', choices=['status', 'set', 'set-render', 'delete'],
                       help='Action to perform')
    parser.add_argument('url', nargs='?', help='Webhook URL (required for "set" action)')
    
    args = parser.parse_args()
    
    try:
        manager = WebhookManager()
        
        if args.action == 'status':
            manager.print_webhook_status()
            
        elif args.action == 'set':
            if not args.url:
                print("Error: URL is required for 'set' action")
                print("Usage: python manage_webhook.py set <url>")
                sys.exit(1)
            
            success = manager.set_webhook(args.url)
            if success:
                print(f"✅ Webhook set successfully: {args.url}")
            else:
                print("❌ Failed to set webhook")
                sys.exit(1)
                
        elif args.action == 'set-render':
            success = manager.setup_webhook_for_render()
            if success:
                webhook_url = manager.get_webhook_url_for_render()
                print(f"✅ Webhook set for Render.com: {webhook_url}")
            else:
                print("❌ Failed to set webhook for Render.com")
                sys.exit(1)
                
        elif args.action == 'delete':
            success = manager.delete_webhook()
            if success:
                print("✅ Webhook deleted successfully")
            else:
                print("❌ Failed to delete webhook")
                sys.exit(1)
    
    except Exception as e:
        print(f"❌ Error: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()
