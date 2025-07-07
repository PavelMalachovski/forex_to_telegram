
"""
Utility functions for webhook management.
"""

import os
import sys
import logging
import requests
from typing import Optional, Dict, Any

# Add app directory to Python path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'app'))

from app.config import config
from app.utils.logging_config import setup_logging

# Setup logging
setup_logging()
logger = logging.getLogger(__name__)

class WebhookManager:
    """Manages Telegram bot webhooks."""
    
    def __init__(self, bot_token: Optional[str] = None):
        self.bot_token = bot_token or config.TELEGRAM_BOT_TOKEN
        if not self.bot_token:
            raise ValueError("Bot token is required")
        
        self.api_base_url = f"https://api.telegram.org/bot{self.bot_token}"
    
    def get_webhook_info(self) -> Dict[str, Any]:
        """Get current webhook information."""
        try:
            response = requests.get(f"{self.api_base_url}/getWebhookInfo")
            response.raise_for_status()
            
            result = response.json()
            if result.get('ok'):
                return result.get('result', {})
            else:
                raise Exception(f"API error: {result.get('description', 'Unknown error')}")
                
        except Exception as e:
            logger.error(f"Failed to get webhook info: {e}")
            raise
    
    def set_webhook(self, webhook_url: str) -> bool:
        """Set webhook URL."""
        try:
            data = {'url': webhook_url}
            response = requests.post(f"{self.api_base_url}/setWebhook", data=data)
            response.raise_for_status()
            
            result = response.json()
            if result.get('ok'):
                logger.info(f"Webhook set successfully: {webhook_url}")
                return True
            else:
                error_msg = result.get('description', 'Unknown error')
                logger.error(f"Failed to set webhook: {error_msg}")
                return False
                
        except Exception as e:
            logger.error(f"Failed to set webhook: {e}")
            raise
    
    def delete_webhook(self) -> bool:
        """Delete current webhook."""
        try:
            response = requests.post(f"{self.api_base_url}/deleteWebhook")
            response.raise_for_status()
            
            result = response.json()
            if result.get('ok'):
                logger.info("Webhook deleted successfully")
                return True
            else:
                error_msg = result.get('description', 'Unknown error')
                logger.error(f"Failed to delete webhook: {error_msg}")
                return False
                
        except Exception as e:
            logger.error(f"Failed to delete webhook: {e}")
            raise
    
    def get_webhook_url_for_render(self) -> Optional[str]:
        """Get webhook URL for Render.com deployment."""
        hostname = os.getenv('RENDER_EXTERNAL_HOSTNAME')
        if hostname:
            return f"https://{hostname}/webhook"
        return None
    
    def setup_webhook_for_render(self) -> bool:
        """Setup webhook for Render.com deployment."""
        webhook_url = self.get_webhook_url_for_render()
        if not webhook_url:
            logger.error("RENDER_EXTERNAL_HOSTNAME not set")
            return False
        
        # First delete any existing webhook
        try:
            self.delete_webhook()
        except Exception as e:
            logger.warning(f"Failed to delete existing webhook: {e}")
        
        # Set new webhook
        return self.set_webhook(webhook_url)
    
    def print_webhook_status(self):
        """Print current webhook status."""
        try:
            info = self.get_webhook_info()
            
            print("\n=== Webhook Status ===")
            print(f"URL: {info.get('url', 'Not set')}")
            print(f"Has custom certificate: {info.get('has_custom_certificate', False)}")
            print(f"Pending update count: {info.get('pending_update_count', 0)}")
            
            if info.get('last_error_date'):
                print(f"Last error date: {info.get('last_error_date')}")
                print(f"Last error message: {info.get('last_error_message', 'N/A')}")
            
            if info.get('max_connections'):
                print(f"Max connections: {info.get('max_connections')}")
            
            if info.get('allowed_updates'):
                print(f"Allowed updates: {', '.join(info.get('allowed_updates'))}")
            
            print("=====================\n")
            
        except Exception as e:
            print(f"Failed to get webhook status: {e}")

def main():
    """Main function for testing webhook utilities."""
    try:
        manager = WebhookManager()
        manager.print_webhook_status()
        
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    main()
