
"""
Main bot class for the Forex Bot application.
"""

import logging
import telebot
from telebot.apihelper import ApiTelegramException

from app.bot.handlers import BotHandlers
from app.core.error_handler import ErrorHandler

logger = logging.getLogger(__name__)

class ForexBot:
    """Main Forex Bot class."""
    
    def __init__(self, token: str, db_session_factory):
        """Initialize the bot."""
        self.token = token
        self.db_session_factory = db_session_factory
        self.bot = None
        self._setup_bot()
    
    def _setup_bot(self):
        """Setup the Telegram bot."""
        try:
            self.bot = telebot.TeleBot(self.token)
            
            # Initialize handlers
            self.handlers = BotHandlers(self.bot, self.db_session_factory)
            
            logger.info("Bot setup completed successfully")
            
        except Exception as e:
            ErrorHandler.log_error(e, "bot setup")
            raise
    
    def start(self):
        """Start the bot."""
        try:
            logger.info("Bot is starting...")
            self.bot.infinity_polling(
                timeout=10,
                long_polling_timeout=5,
                none_stop=True,
                interval=1
            )
        except KeyboardInterrupt:
            logger.info("Bot stopped by user")
        except Exception as e:
            ErrorHandler.log_error(e, "bot polling")
            raise
    
    def stop(self):
        """Stop the bot."""
        try:
            if self.bot:
                self.bot.stop_polling()
                logger.info("Bot stopped successfully")
        except Exception as e:
            ErrorHandler.log_error(e, "bot stop")
