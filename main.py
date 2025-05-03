
"""
Main application entry point for Telegram bot only.
Note: Scheduling is now handled by make.com via API endpoints.
"""

import os
import sys
import signal
import telebot
import logging

# Add app directory to Python path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'app'))

from app.config import config
from app.utils.logging_config import setup_logging
from app.database.connection import init_database, SessionLocal
from app.bot.handlers import BotHandlers

# Setup logging
setup_logging()
logger = logging.getLogger(__name__)

class TelegramBotApplication:
    """Telegram bot application without scheduler."""
    
    def __init__(self):
        self.bot = None
        self.bot_handlers = None
        
    def initialize(self):
        """Initialize the application."""
        logger.info("Initializing Telegram Bot application...")
        
        # Validate configuration
        if not config.validate():
            logger.error("Configuration validation failed")
            sys.exit(1)
        
        # Initialize database
        try:
            init_database()
            logger.info("Database initialized successfully")
        except Exception as e:
            logger.error(f"Database initialization failed: {e}")
            sys.exit(1)
        
        # Initialize Telegram bot
        if config.TELEGRAM_BOT_TOKEN:
            try:
                self.bot = telebot.TeleBot(config.TELEGRAM_BOT_TOKEN)
                self.bot_handlers = BotHandlers(self.bot, lambda: SessionLocal())
                logger.info("Telegram bot initialized successfully")
            except Exception as e:
                logger.error(f"Failed to initialize Telegram bot: {e}")
                sys.exit(1)
        else:
            logger.error("TELEGRAM_BOT_TOKEN not configured")
            sys.exit(1)
        
        logger.info("Application initialized successfully")
    
    def start(self):
        """Start the application."""
        logger.info("Starting Telegram Bot application...")
        
        # Set up signal handlers for graceful shutdown
        signal.signal(signal.SIGINT, self._signal_handler)
        signal.signal(signal.SIGTERM, self._signal_handler)
        
        # Start Telegram bot polling
        if self.bot:
            try:
                logger.info("Starting Telegram bot polling...")
                self.bot.infinity_polling(none_stop=True, interval=0, timeout=20)
            except Exception as e:
                logger.error(f"Telegram bot polling error: {e}")
        
    def stop(self):
        """Stop the application."""
        logger.info("Stopping Telegram Bot application...")
        
        if self.bot:
            try:
                self.bot.stop_polling()
                logger.info("Telegram bot polling stopped")
            except Exception as e:
                logger.error(f"Error stopping bot polling: {e}")
        
        logger.info("Application stopped")
    
    def _signal_handler(self, signum, frame):
        """Handle shutdown signals."""
        logger.info(f"Received signal {signum}, shutting down...")
        self.stop()
        sys.exit(0)

def main():
    """Main entry point."""
    try:
        app = TelegramBotApplication()
        app.initialize()
        app.start()
    except KeyboardInterrupt:
        logger.info("Application interrupted by user")
    except Exception as e:
        logger.error(f"Application failed: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()
