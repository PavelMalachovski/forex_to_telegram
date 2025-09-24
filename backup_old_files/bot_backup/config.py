import os
import logging

class Config:
    """Application configuration management."""

    def __init__(self):
        self.telegram_bot_token = os.getenv("TELEGRAM_BOT_TOKEN")
        self.telegram_chat_id = os.getenv("TELEGRAM_CHAT_ID")
        self.chatgpt_api_key = os.getenv("CHATGPT_API_KEY")  # Only this variable
        # Admin API key for protecting internal endpoints
        self.api_key = os.getenv("API_KEY")
        # Optional Telegram webhook secret to verify incoming webhook requests
        self.telegram_webhook_secret = os.getenv("TELEGRAM_WEBHOOK_SECRET")
        self.render_hostname = os.getenv("RENDER_EXTERNAL_HOSTNAME")
        self.port = int(os.getenv("PORT", 10000))
        self.timezone = "Europe/Prague"

        # Database configuration
        self.database_url = os.getenv("DATABASE_URL")
        # Do not hardcode secrets; rely on env vars. Provide no insecure defaults.
        self.database_host = os.getenv("DB_HOST")
        self.database_port = os.getenv("DB_PORT", "5432")
        self.database_name = os.getenv("DB_NAME")
        self.database_user = os.getenv("DB_USER")
        self.database_password = os.getenv("DB_PASSWORD")

        # Build database URL if not provided
        if not self.database_url:
            # Prefer explicit DATABASE_URL. For local/dev, opt-in to SQLite with USE_LOCAL_DB=true
            if os.getenv("USE_LOCAL_DB", "false").lower() == "true":
                self.database_url = "sqlite:///./forex_bot.db"
            elif all([self.database_user, self.database_password, self.database_host, self.database_name]):
                self.database_url = (
                    f"postgresql://{self.database_user}:{self.database_password}@{self.database_host}:{self.database_port}/{self.database_name}"
                )
            else:
                # Leave unset to force explicit configuration
                self.database_url = None

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
