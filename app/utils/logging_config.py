
"""
Logging configuration for the application.
"""

import logging
import sys
import os
from pathlib import Path
from pythonjsonlogger import jsonlogger
from app.config import config

def setup_logging() -> logging.Logger:
    """
    Set up structured logging for the application.
    
    Returns:
        Configured logger instance
    """
    # Create logs directory if it doesn't exist
    logs_dir = Path("logs")
    logs_dir.mkdir(exist_ok=True)
    
    # Create formatter
    log_format = '%(asctime)s %(name)s %(levelname)s %(funcName)s %(message)s'
    
    if config.LOG_LEVEL == 'DEBUG':
        # Use regular formatter for debug mode
        formatter = logging.Formatter(
            '%(asctime)s [%(levelname)s] [%(name)s.%(funcName)s] %(message)s'
        )
    else:
        # Use JSON formatter for production
        formatter = jsonlogger.JsonFormatter(log_format)
    
    # Configure root logger
    root_logger = logging.getLogger()
    root_logger.setLevel(getattr(logging, config.LOG_LEVEL.upper()))
    
    # Remove existing handlers
    for handler in root_logger.handlers[:]:
        root_logger.removeHandler(handler)
    
    # Console handler
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setFormatter(formatter)
    root_logger.addHandler(console_handler)
    
    # File handler for application logs
    app_file_handler = logging.FileHandler(logs_dir / "app.log")
    app_file_handler.setFormatter(formatter)
    root_logger.addHandler(app_file_handler)
    
    # Separate file handler for errors
    error_file_handler = logging.FileHandler(logs_dir / "error.log")
    error_file_handler.setLevel(logging.ERROR)
    error_file_handler.setFormatter(formatter)
    root_logger.addHandler(error_file_handler)
    
    # Configure specific loggers
    
    # Reduce noise from external libraries
    logging.getLogger('urllib3').setLevel(logging.WARNING)
    logging.getLogger('requests').setLevel(logging.WARNING)
    logging.getLogger('telebot').setLevel(logging.INFO)
    logging.getLogger('sqlalchemy.engine').setLevel(logging.WARNING)
    
    # Set playwright to warning level to reduce noise
    logging.getLogger('playwright').setLevel(logging.WARNING)
    
    logger = logging.getLogger(__name__)
    logger.info(f"Logging configured with level: {config.LOG_LEVEL}")
    
    return root_logger
