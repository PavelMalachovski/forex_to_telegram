
"""
Centralized error handling for the Telegram bot.
"""

import logging
import functools
import traceback
from typing import Callable, Any
from telebot import types
from telebot.apihelper import ApiTelegramException

logger = logging.getLogger(__name__)

def safe_handler(fallback_message: str = "❌ Произошла ошибка. Попробуйте позже."):
    """
    Decorator for safe handling of bot commands and callbacks.
    Prevents bot from crashing on errors and provides user feedback.
    """
    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        def wrapper(*args, **kwargs) -> Any:
            try:
                return func(*args, **kwargs)
            except ApiTelegramException as e:
                logger.error(f"Telegram API error in {func.__name__}: {e}")
                # Try to send fallback message if possible
                try:
                    if args and hasattr(args[0], 'bot'):
                        bot = args[0].bot
                        if len(args) > 1:
                            message_or_call = args[1]
                            if hasattr(message_or_call, 'chat'):
                                bot.send_message(message_or_call.chat.id, fallback_message)
                            elif hasattr(message_or_call, 'message') and hasattr(message_or_call.message, 'chat'):
                                bot.send_message(message_or_call.message.chat.id, fallback_message)
                except Exception as send_error:
                    logger.error(f"Failed to send fallback message: {send_error}")
                return None
            except Exception as e:
                logger.error(f"Unexpected error in {func.__name__}: {e}")
                logger.error(f"Traceback: {traceback.format_exc()}")
                # Try to send fallback message if possible
                try:
                    if args and hasattr(args[0], 'bot'):
                        bot = args[0].bot
                        if len(args) > 1:
                            message_or_call = args[1]
                            if hasattr(message_or_call, 'chat'):
                                bot.send_message(message_or_call.chat.id, fallback_message)
                            elif hasattr(message_or_call, 'message') and hasattr(message_or_call.message, 'chat'):
                                bot.send_message(message_or_call.message.chat.id, fallback_message)
                except Exception as send_error:
                    logger.error(f"Failed to send fallback message: {send_error}")
                return None
        return wrapper
    return decorator

def safe_callback_handler(fallback_message: str = "❌ Произошла ошибка. Попробуйте позже."):
    """
    Decorator specifically for callback query handlers.
    """
    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        def wrapper(*args, **kwargs) -> Any:
            try:
                return func(*args, **kwargs)
            except ApiTelegramException as e:
                logger.error(f"Telegram API error in callback {func.__name__}: {e}")
                # Try to answer callback query and send message
                try:
                    if args and hasattr(args[0], 'bot') and len(args) > 1:
                        bot = args[0].bot
                        call = args[1]
                        if hasattr(call, 'id'):
                            bot.answer_callback_query(call.id, fallback_message, show_alert=True)
                        if hasattr(call, 'message') and hasattr(call.message, 'chat'):
                            bot.send_message(call.message.chat.id, fallback_message)
                except Exception as send_error:
                    logger.error(f"Failed to send callback fallback message: {send_error}")
                return None
            except Exception as e:
                logger.error(f"Unexpected error in callback {func.__name__}: {e}")
                logger.error(f"Traceback: {traceback.format_exc()}")
                # Try to answer callback query and send message
                try:
                    if args and hasattr(args[0], 'bot') and len(args) > 1:
                        bot = args[0].bot
                        call = args[1]
                        if hasattr(call, 'id'):
                            bot.answer_callback_query(call.id, fallback_message, show_alert=True)
                        if hasattr(call, 'message') and hasattr(call.message, 'chat'):
                            bot.send_message(call.message.chat.id, fallback_message)
                except Exception as send_error:
                    logger.error(f"Failed to send callback fallback message: {send_error}")
                return None
        return wrapper
    return decorator

class ErrorHandler:
    """
    Centralized error handler for the bot.
    """
    
    @staticmethod
    def log_error(error: Exception, context: str = ""):
        """Log error with context information."""
        logger.error(f"Error in {context}: {error}")
        logger.error(f"Traceback: {traceback.format_exc()}")
    
    @staticmethod
    def handle_db_error(error: Exception, context: str = "database operation"):
        """Handle database-related errors."""
        ErrorHandler.log_error(error, f"DB {context}")
        return None
    
    @staticmethod
    def handle_api_error(error: ApiTelegramException, context: str = "API call"):
        """Handle Telegram API errors."""
        ErrorHandler.log_error(error, f"API {context}")
        return None
    
    @staticmethod
    def safe_send_message(bot, chat_id: int, text: str, **kwargs):
        """Safely send message with error handling."""
        try:
            return bot.send_message(chat_id, text, **kwargs)
        except ApiTelegramException as e:
            ErrorHandler.handle_api_error(e, "send_message")
            return None
        except Exception as e:
            ErrorHandler.log_error(e, "send_message")
            return None
    
    @staticmethod
    def safe_edit_message(bot, chat_id: int, message_id: int, text: str, **kwargs):
        """Safely edit message with error handling."""
        try:
            return bot.edit_message_text(text, chat_id, message_id, **kwargs)
        except ApiTelegramException as e:
            ErrorHandler.handle_api_error(e, "edit_message")
            return None
        except Exception as e:
            ErrorHandler.log_error(e, "edit_message")
            return None
    
    @staticmethod
    def safe_answer_callback(bot, callback_query_id: str, text: str = None, show_alert: bool = False):
        """Safely answer callback query with error handling."""
        try:
            return bot.answer_callback_query(callback_query_id, text, show_alert)
        except ApiTelegramException as e:
            ErrorHandler.handle_api_error(e, "answer_callback_query")
            return None
        except Exception as e:
            ErrorHandler.log_error(e, "answer_callback_query")
            return None
