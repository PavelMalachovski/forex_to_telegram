import os
import logging

# Database configuration
DATABASE_URL = os.getenv(
    "DATABASE_URL", 
    "postgresql://forex_user:0VGr0I02HDKaiVUVT21Z3ORnEiCBAYtC@dpg-d1mkim2li9vc73c7toi0-a.frankfurt-postgres.render.com:5432/forex_db_0myg?sslmode=require"
)

class Config:
    """Application configuration management."""

    def __init__(self):
        self.telegram_bot_token = os.getenv("TELEGRAM_BOT_TOKEN")
        self.telegram_chat_id = os.getenv("TELEGRAM_CHAT_ID")
        self.openai_api_key = os.getenv("OPENAI_API_KEY")
        self.api_key = os.getenv("API_KEY")
        self.render_hostname = os.getenv("RENDER_EXTERNAL_HOSTNAME")
        self.port = int(os.getenv("PORT", 10000))
        self.timezone = "Europe/Prague"
        self.database_url = DATABASE_URL
        
        # Multi-source configuration
        self.news_sources = self._load_news_sources_config()
    
    def _load_news_sources_config(self):
        """Load news sources configuration."""
        return {
            'forex_factory': {
                'enabled': os.getenv("FOREX_FACTORY_ENABLED", "true").lower() == "true",
                'priority': int(os.getenv("FOREX_FACTORY_PRIORITY", "1")),
            },
            'alpha_vantage': {
                'enabled': os.getenv("ALPHA_VANTAGE_ENABLED", "true").lower() == "true",
                'priority': int(os.getenv("ALPHA_VANTAGE_PRIORITY", "2")),
                'api_key': os.getenv("ALPHA_VANTAGE_API_KEY"),
            },
            'fmp': {
                'enabled': os.getenv("FMP_ENABLED", "true").lower() == "true",
                'priority': int(os.getenv("FMP_PRIORITY", "3")),
                'api_key': os.getenv("FMP_API_KEY"),
            },
            'newsapi': {
                'enabled': os.getenv("NEWSAPI_ENABLED", "true").lower() == "true",
                'priority': int(os.getenv("NEWSAPI_PRIORITY", "4")),
                'api_key': os.getenv("NEWSAPI_API_KEY"),
            },
            'rss': {
                'enabled': os.getenv("RSS_ENABLED", "true").lower() == "true",
                'priority': int(os.getenv("RSS_PRIORITY", "5")),
            }
        }

    def validate_required_vars(self):
        required_vars = {
            "TELEGRAM_BOT_TOKEN": self.telegram_bot_token,
            "TELEGRAM_CHAT_ID": self.telegram_chat_id,
            "API_KEY": self.api_key,
        }
        return [var for var, value in required_vars.items() if not value]


def setup_logging():
    """Configure application logging."""
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        handlers=[logging.FileHandler("scraper.log"), logging.StreamHandler()],
    )
    return logging.getLogger(__name__)
