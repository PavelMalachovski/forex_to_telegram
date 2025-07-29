import os
import logging

class Config:
    """Application configuration management."""

    def __init__(self):
        self.telegram_bot_token = os.getenv("TELEGRAM_BOT_TOKEN")
        self.telegram_chat_id = os.getenv("TELEGRAM_CHAT_ID")
        self.chatgpt_api_key = os.getenv("CHATGPT_API_KEY")  # Only this variable
        self.api_key = os.getenv("API_KEY")
        self.render_hostname = os.getenv("RENDER_EXTERNAL_HOSTNAME")
        self.port = int(os.getenv("PORT", 10000))
        self.timezone = "Europe/Prague"

        # Database configuration
        self.database_url = os.getenv("DATABASE_URL")
        self.database_host = os.getenv("DB_HOST", "dpg-d1mkim2li9vc73c7toi0-a")
        self.database_port = os.getenv("DB_PORT", "5432")
        self.database_name = os.getenv("DB_NAME", "forex_db_0myg")
        self.database_user = os.getenv("DB_USER", "forex_user")
        self.database_password = os.getenv("DB_PASSWORD", "0VGr0I02HDKaiVUVT21Z3ORnEiCBAYtC")

        # Build database URL if not provided
        if not self.database_url:
            # Use SQLite for local development if no DATABASE_URL is set
            self.database_url = "sqlite:///forex_bot.db"
            logging.info("Using local SQLite database for development")

    def validate_required_vars(self):
        required_vars = {
            "TELEGRAM_BOT_TOKEN": self.telegram_bot_token,
            "TELEGRAM_CHAT_ID": self.telegram_chat_id,
            "API_KEY": self.api_key,
        }
        return [var for var, value in required_vars.items() if not value]

    def get_database_url(self):
        """Get the database URL for connection."""
        return self.database_url


def setup_logging():
    """Configure application logging."""
    logging.basicConfig(
        level=logging.INFO,  # Set to INFO instead of DEBUG
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    )
    return logging.getLogger("bot.config")
