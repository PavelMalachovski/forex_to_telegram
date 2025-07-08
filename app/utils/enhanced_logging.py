
"""
Enhanced logging configuration with rotation, structured logging, and monitoring.
"""

import logging
import logging.config
from logging.handlers import RotatingFileHandler, TimedRotatingFileHandler
import os
import json
from pathlib import Path
from datetime import datetime
import threading
from app.config import config

class HealthAwareFormatter(logging.Formatter):
    """Custom formatter that tracks error counts for health monitoring."""
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.error_count = 0
        self.warning_count = 0
        self.last_error_time = None
        self._lock = threading.Lock()
    
    def format(self, record):
        with self._lock:
            if record.levelno >= logging.ERROR:
                self.error_count += 1
                self.last_error_time = datetime.now()
            elif record.levelno >= logging.WARNING:
                self.warning_count += 1
        
        # Add context information
        if hasattr(record, 'user_id'):
            record.msg = f"[User:{record.user_id}] {record.msg}"
        if hasattr(record, 'request_id'):
            record.msg = f"[Req:{record.request_id}] {record.msg}"
            
        return super().format(record)
    
    def get_health_stats(self):
        """Get health statistics for monitoring."""
        with self._lock:
            return {
                'error_count': self.error_count,
                'warning_count': self.warning_count,
                'last_error_time': self.last_error_time.isoformat() if self.last_error_time else None
            }
    
    def reset_stats(self):
        """Reset health statistics."""
        with self._lock:
            self.error_count = 0
            self.warning_count = 0
            self.last_error_time = None

class CompactPathFormatter(HealthAwareFormatter):
    """Formatter that shows relative paths and includes health monitoring."""
    
    def format(self, record):
        if hasattr(record, 'pathname'):
            record.pathname = os.path.relpath(record.pathname, start=os.getcwd())
        return super().format(record)

# Global formatter instance for health monitoring
health_formatter = None

def get_logging_config():
    """Get comprehensive logging configuration."""
    global health_formatter
    
    # Ensure log directory exists
    log_dir = Path("logs")
    log_dir.mkdir(exist_ok=True)
    
    # Create health-aware formatter
    health_formatter = CompactPathFormatter(
        '%(asctime)s [%(levelname)s] %(name)s:%(lineno)d - %(message)s'
    )
    
    return {
        "version": 1,
        "disable_existing_loggers": False,
        "formatters": {
            "standard": {
                "format": "%(asctime)s [%(levelname)s] %(name)s - %(message)s",
                "datefmt": "%Y-%m-%d %H:%M:%S"
            },
            "detailed": {
                "format": "%(asctime)s [%(levelname)s] %(name)s:%(lineno)d [%(funcName)s] - %(message)s",
                "datefmt": "%Y-%m-%d %H:%M:%S"
            },
            "json": {
                "()": "pythonjsonlogger.jsonlogger.JsonFormatter",
                "format": "%(asctime)s %(name)s %(levelname)s %(funcName)s %(lineno)d %(message)s"
            }
        },
        "handlers": {
            "console": {
                "class": "logging.StreamHandler",
                "formatter": "standard",
                "level": "INFO",
                "stream": "ext://sys.stdout"
            },
            "app_file": {
                "class": "logging.handlers.RotatingFileHandler",
                "formatter": "detailed",
                "level": "DEBUG",
                "filename": str(log_dir / "app.log"),
                "maxBytes": 10 * 1024 * 1024,  # 10 MB
                "backupCount": 5,
                "encoding": "utf-8"
            },
            "error_file": {
                "class": "logging.handlers.RotatingFileHandler",
                "formatter": "detailed",
                "level": "ERROR",
                "filename": str(log_dir / "error.log"),
                "maxBytes": 5 * 1024 * 1024,  # 5 MB
                "backupCount": 3,
                "encoding": "utf-8"
            },
            "json_file": {
                "class": "logging.handlers.TimedRotatingFileHandler",
                "formatter": "json",
                "level": "INFO",
                "filename": str(log_dir / "app_structured.log"),
                "when": "midnight",
                "interval": 1,
                "backupCount": 7,
                "encoding": "utf-8"
            },
            "health_file": {
                "class": "logging.handlers.RotatingFileHandler",
                "formatter": "standard",
                "level": "INFO",
                "filename": str(log_dir / "health.log"),
                "maxBytes": 1 * 1024 * 1024,  # 1 MB
                "backupCount": 2,
                "encoding": "utf-8"
            }
        },
        "loggers": {
            "": {  # Root logger
                "handlers": ["console", "app_file", "error_file"],
                "level": config.LOG_LEVEL.upper(),
                "propagate": False
            },
            "app": {
                "handlers": ["console", "app_file", "error_file", "json_file"],
                "level": "DEBUG",
                "propagate": False
            },
            "health": {
                "handlers": ["health_file", "console"],
                "level": "INFO",
                "propagate": False
            },
            # Reduce noise from external libraries
            "urllib3": {"level": "WARNING"},
            "requests": {"level": "WARNING"},
            "telebot": {"level": "INFO"},
            "sqlalchemy.engine": {"level": "WARNING"},

            "werkzeug": {"level": "WARNING"}
        }
    }

def setup_enhanced_logging():
    """Setup enhanced logging with rotation and health monitoring."""
    config_dict = get_logging_config()
    logging.config.dictConfig(config_dict)
    
    # Set custom formatter for health monitoring
    if health_formatter:
        root_logger = logging.getLogger()
        for handler in root_logger.handlers:
            if isinstance(handler, (RotatingFileHandler, TimedRotatingFileHandler)):
                handler.setFormatter(health_formatter)
    
    logger = logging.getLogger(__name__)
    logger.info("Enhanced logging system initialized")
    logger.info(f"Log level: {config.LOG_LEVEL}")
    logger.info(f"Log directory: {Path('logs').absolute()}")
    
    return logger

def get_log_health_stats():
    """Get health statistics from logging system."""
    if health_formatter:
        return health_formatter.get_health_stats()
    return {"error": "Health formatter not initialized"}

def reset_log_health_stats():
    """Reset health statistics."""
    if health_formatter:
        health_formatter.reset_stats()

class LogContextManager:
    """Context manager for adding context to log messages."""
    
    def __init__(self, logger, **context):
        self.logger = logger
        self.context = context
        self.old_factory = None
    
    def __enter__(self):
        self.old_factory = logging.getLogRecordFactory()
        
        def record_factory(*args, **kwargs):
            record = self.old_factory(*args, **kwargs)
            for key, value in self.context.items():
                setattr(record, key, value)
            return record
        
        logging.setLogRecordFactory(record_factory)
        return self.logger
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        logging.setLogRecordFactory(self.old_factory)

def log_with_context(logger, **context):
    """Create a context manager for logging with additional context."""
    return LogContextManager(logger, **context)

# Convenience function for structured logging
def log_event(logger, event_type, message, **extra_data):
    """Log a structured event with additional data."""
    event_data = {
        'event_type': event_type,
        'timestamp': datetime.utcnow().isoformat(),
        **extra_data
    }
    
    # Add structured data to the message
    structured_message = f"{message} | Event: {json.dumps(event_data, default=str)}"
    logger.info(structured_message)

if __name__ == "__main__":
    # Test the enhanced logging
    setup_enhanced_logging()
    logger = logging.getLogger("test")
    
    logger.debug("Debug message")
    logger.info("Info message")
    logger.warning("Warning message")
    logger.error("Error message")
    
    # Test context logging
    with log_with_context(logger, user_id="12345", request_id="req-abc") as ctx_logger:
        ctx_logger.info("Message with context")
    
    # Test structured logging
    log_event(logger, "user_action", "User logged in", user_id="12345", ip="192.168.1.1")
    
    print("Health stats:", get_log_health_stats())
