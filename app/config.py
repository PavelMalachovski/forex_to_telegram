
"""Configuration module for the Forex Bot application."""

import os
from typing import Optional, Union
from pathlib import Path


def _get_bool_env(key: str, default: bool = False) -> bool:
    """
    Get boolean environment variable.
    
    Args:
        key: Environment variable key
        default: Default value if not found
        
    Returns:
        Boolean value
    """
    value = os.getenv(key, '').lower()
    if value in ('true', '1', 'yes', 'on'):
        return True
    elif value in ('false', '0', 'no', 'off'):
        return False
    else:
        return default


class Config:
    """Application configuration class."""
    
    # Database configuration
    DATABASE_URL: str = os.getenv(
        'DATABASE_URL',
        'postgresql://postgres:password@localhost:5432/forex_bot'
    )
    
    # Telegram Bot configuration
    TELEGRAM_BOT_TOKEN: Optional[str] = os.getenv('TELEGRAM_BOT_TOKEN')
    TELEGRAM_WEBHOOK_URL: Optional[str] = os.getenv('TELEGRAM_WEBHOOK_URL')
    TELEGRAM_WEBHOOK_SECRET: Optional[str] = os.getenv('TELEGRAM_WEBHOOK_SECRET')
    
    # API configuration
    API_HOST: str = os.getenv('API_HOST', '0.0.0.0')
    API_PORT: int = int(os.getenv('API_PORT', '8000'))
    API_DEBUG: bool = _get_bool_env('API_DEBUG', False)
    
    # Scraping configuration
    SCRAPING_ENABLED: bool = _get_bool_env('SCRAPING_ENABLED', True)
    SCRAPING_INTERVAL_HOURS: int = int(os.getenv('SCRAPING_INTERVAL_HOURS', '6'))
    FOREX_FACTORY_BASE_URL: str = os.getenv(
        'FOREX_FACTORY_BASE_URL',
        'https://www.forexfactory.com'
    )
    
    # Notification configuration
    NOTIFICATIONS_ENABLED: bool = _get_bool_env('NOTIFICATIONS_ENABLED', True)
    NOTIFICATION_ADVANCE_MINUTES: int = int(os.getenv('NOTIFICATION_ADVANCE_MINUTES', '30'))
    DAILY_SUMMARY_ENABLED: bool = _get_bool_env('DAILY_SUMMARY_ENABLED', True)
    DAILY_SUMMARY_TIME: str = os.getenv('DAILY_SUMMARY_TIME', '08:00')
    
    # Logging configuration
    LOG_LEVEL: str = os.getenv('LOG_LEVEL', 'INFO')
    LOG_FORMAT: str = os.getenv(
        'LOG_FORMAT',
        '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    LOG_FILE: Optional[str] = os.getenv('LOG_FILE')
    STRUCTURED_LOGGING: bool = _get_bool_env('STRUCTURED_LOGGING', False)
    
    # Health monitoring configuration
    HEALTH_CHECK_ENABLED: bool = _get_bool_env('HEALTH_CHECK_ENABLED', True)
    HEALTH_CHECK_INTERVAL: int = int(os.getenv('HEALTH_CHECK_INTERVAL', '300'))
    METRICS_ENABLED: bool = _get_bool_env('METRICS_ENABLED', True)
    
    # Security configuration
    SECRET_KEY: str = os.getenv('SECRET_KEY', 'your-secret-key-here')
    ALLOWED_HOSTS: list[str] = os.getenv('ALLOWED_HOSTS', '*').split(',')
    
    # File paths
    BASE_DIR: Path = Path(__file__).parent.parent
    LOGS_DIR: Path = BASE_DIR / 'logs'
    DATA_DIR: Path = BASE_DIR / 'data'
    
    # Environment
    ENVIRONMENT: str = os.getenv('ENVIRONMENT', 'development')
    DEBUG: bool = _get_bool_env('DEBUG', ENVIRONMENT == 'development')
    
    # Timezone configuration
    DEFAULT_TIMEZONE: str = os.getenv('DEFAULT_TIMEZONE', 'Europe/Prague')
    TIMEZONE: str = os.getenv('TIMEZONE', 'Europe/Prague')
    
    # Rate limiting
    RATE_LIMIT_ENABLED: bool = _get_bool_env('RATE_LIMIT_ENABLED', True)
    RATE_LIMIT_REQUESTS: int = int(os.getenv('RATE_LIMIT_REQUESTS', '100'))
    RATE_LIMIT_WINDOW: int = int(os.getenv('RATE_LIMIT_WINDOW', '3600'))
    
    # Cache configuration
    CACHE_ENABLED: bool = _get_bool_env('CACHE_ENABLED', True)
    CACHE_TTL: int = int(os.getenv('CACHE_TTL', '3600'))
    
    @classmethod
    def validate(cls) -> bool:
        """
        Validate configuration settings.
        
        Returns:
            True if configuration is valid, False otherwise
        """
        if not cls.TELEGRAM_BOT_TOKEN:
            print("ERROR: TELEGRAM_BOT_TOKEN is required")
            return False
        
        if not cls.DATABASE_URL:
            print("ERROR: DATABASE_URL is required")
            return False
        
        return True
    
    @classmethod
    def get_database_url(cls) -> str:
        """
        Get the database URL with proper formatting.
        
        Returns:
            Formatted database URL
        """
        url = cls.DATABASE_URL
        
        # Handle Render.com database URL format
        if url.startswith('postgres://'):
            url = url.replace('postgres://', 'postgresql://', 1)
        
        return url


# Global configuration instance
config = Config()
