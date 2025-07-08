
"""
Service for sending today's news to all users.
"""

import logging
from sqlalchemy.orm import Session
import telebot

from app.services.user_service import UserService
from app.bot.handlers import BotHandlers
from app.database.connection import SessionLocal

logger = logging.getLogger(__name__)

class TodayService:
    """Service for sending today's news to all users."""
    
    def __init__(self, db: Session, bot: telebot.TeleBot):
        self.db = db
        self.bot = bot
        self.user_service = UserService(db)
    
    def send_today_to_all_users(self) -> dict:
        """
        Send today's news to all active users.
        
        Returns:
            Dictionary with sending results
        """
        if not self.bot:
            logger.warning("Bot not available, skipping today command call")
            return {
                'status': 'failed',
                'users_notified': 0,
                'errors_count': 1,
                'error_message': 'Bot not available'
            }
        
        logger.info("Starting automatic /today command execution")
        
        try:
            # Get all active users who have notifications enabled
            active_users = self.user_service.get_active_users_with_notifications()
            
            if not active_users:
                logger.info("No active users with notifications found")
                return {
                    'status': 'success',
                    'users_notified': 0,
                    'errors_count': 0,
                    'message': 'No active users found'
                }
            
            logger.info(f"Sending /today command to {len(active_users)} active users")
            
            # Create a mock message object for the today command
            class MockMessage:
                def __init__(self, chat_id, user_id):
                    self.chat = type('obj', (object,), {'id': chat_id})
                    self.from_user = type('obj', (object,), {'id': user_id})
            
            # Initialize bot handlers
            bot_handlers = BotHandlers(self.bot, lambda: SessionLocal())
            
            success_count = 0
            error_count = 0
            
            # Send today command to each active user
            for user in active_users:
                try:
                    mock_message = MockMessage(user.telegram_user_id, user.telegram_user_id)
                    bot_handlers.today_command(mock_message)
                    success_count += 1
                    logger.debug(f"Successfully sent /today to user {user.telegram_user_id}")
                    
                except Exception as e:
                    error_count += 1
                    logger.error(f"Failed to send /today to user {user.telegram_user_id}: {e}")
            
            logger.info(f"Automatic /today command completed: {success_count} successful, {error_count} errors")
            
            return {
                'status': 'success' if error_count == 0 else 'partial',
                'users_notified': success_count,
                'errors_count': error_count,
                'total_users': len(active_users)
            }
            
        except Exception as e:
            logger.error(f"Automatic /today command failed: {e}")
            return {
                'status': 'failed',
                'users_notified': 0,
                'errors_count': 1,
                'error_message': str(e)
            }
