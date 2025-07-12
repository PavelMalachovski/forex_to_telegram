
"""
Main bot application entry point.
"""

import logging
import os
import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from app.config import Config
from app.database.connection import get_db_session_factory
from app.bot.bot import ForexBot
from app.core.error_handler import ErrorHandler

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('logs/bot.log'),
        logging.StreamHandler(sys.stdout)
    ]
)

logger = logging.getLogger(__name__)

def main():
    """Main application entry point."""
    try:
        # Load configuration
        config = Config()
        
        # Validate required environment variables
        if not config.TELEGRAM_BOT_TOKEN:
            logger.error("TELEGRAM_BOT_TOKEN environment variable is required")
            sys.exit(1)
        
        # Create database session factory
        db_session_factory = get_db_session_factory(config.DATABASE_URL)
        
        # Create and start bot
        bot = ForexBot(config.TELEGRAM_BOT_TOKEN, db_session_factory)
        
        logger.info("Starting Forex Bot...")
        bot.start()
        
    except KeyboardInterrupt:
        logger.info("Bot stopped by user")
    except Exception as e:
        ErrorHandler.log_error(e, "main application")
        sys.exit(1)

if __name__ == "__main__":
    main()
