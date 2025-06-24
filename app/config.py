
"""
Configuration management for the Forex Bot application.
"""

import os
from typing import Optional
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

class Config:
    """Application configuration class."""
    
    # Database Configuration
    DATABASE_URL: str = os.getenv('DATABASE_URL', 'sqlite:///forex_bot.db')
    
    # Redis Configuration
    REDIS_URL: str = os.getenv('REDIS_URL', 'redis://localhost:6379/0')
    
    # Telegram Configuration
    TELEGRAM_BOT_TOKEN: Optional[str] = os.getenv('TELEGRAM_BOT_TOKEN')
    TELEGRAM_CHAT_ID: Optional[str] = os.getenv('TELEGRAM_CHAT_ID')
    
    # OpenAI Configuration
    OPENAI_API_KEY: Optional[str] = os.getenv('OPENAI_API_KEY')
    
    # API Configuration
    API_KEY: Optional[str] = os.getenv('API_KEY')
    
    # Deployment Configuration
    RENDER_EXTERNAL_HOSTNAME: Optional[str] = os.getenv('RENDER_EXTERNAL_HOSTNAME')
    WEBHOOK_MODE: Optional[str] = os.getenv('WEBHOOK_MODE')  # Force webhook mode
    WEBHOOK_URL: Optional[str] = os.getenv('WEBHOOK_URL')    # Custom webhook URL
    
    # Logging Configuration
    LOG_LEVEL: str = os.getenv('LOG_LEVEL', 'INFO')
    
    # Scheduler Configuration
    SCRAPER_SCHEDULE_HOUR: int = int(os.getenv('SCRAPER_SCHEDULE_HOUR', '3'))
    SCRAPER_SCHEDULE_MINUTE: int = int(os.getenv('SCRAPER_SCHEDULE_MINUTE', '0'))
    TIMEZONE: str = os.getenv('TIMEZONE', 'Europe/Prague')
    
    # Application Configuration
    FLASK_PORT: int = int(os.getenv('FLASK_PORT', '5000'))
    FLASK_HOST: str = os.getenv('FLASK_HOST', '0.0.0.0')
    FLASK_DEBUG: bool = os.getenv('FLASK_DEBUG', 'False').lower() == 'true'
    
    # Available currencies
    AVAILABLE_CURRENCIES = ["EUR", "USD", "JPY", "GBP", "CAD", "AUD", "CHF", "NZD"]
    
    # User agents for web scraping
    USER_AGENTS = [
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36",
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/92.0.4515.159 Safari/537.36",
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:89.0) Gecko/20100101 Firefox/89.0",
        "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36",
    ]
    
    # Impact mapping for scraping
    IMPACT_MAP = {
        "gra": "NON_ECONOMIC",
        "yel": "LOW",
        "ora": "MEDIUM", 
        "red": "HIGH",
    }
    
    @classmethod
    def validate(cls) -> bool:
        """Validate required configuration."""
        required_vars = ['TELEGRAM_BOT_TOKEN']
        missing_vars = [var for var in required_vars if not getattr(cls, var)]
        
        if missing_vars:
            print(f"Missing required environment variables: {', '.join(missing_vars)}")
            return False
        
        # Check if token looks valid (basic format check)
        if cls.TELEGRAM_BOT_TOKEN and not cls.TELEGRAM_BOT_TOKEN.startswith('your_'):
            # Basic token format validation
            parts = cls.TELEGRAM_BOT_TOKEN.split(':')
            if len(parts) != 2 or not parts[0].isdigit() or len(parts[1]) < 10:
                print("TELEGRAM_BOT_TOKEN appears to be invalid format")
                return False
        
        return True
    
    @classmethod
    def is_production(cls) -> bool:
        """Check if running in production environment."""
        return cls.RENDER_EXTERNAL_HOSTNAME is not None
    
    @classmethod
    def is_webhook_mode(cls) -> bool:
        """Check if webhook mode should be used."""
        return (
            cls.is_production() or
            cls.WEBHOOK_MODE and cls.WEBHOOK_MODE.lower() == 'true'
        )

# Global config instance
config = Config()
