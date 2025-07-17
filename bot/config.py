import os
import logging

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
