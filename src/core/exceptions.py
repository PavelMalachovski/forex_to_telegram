"""Custom exceptions for the application."""

from typing import Optional, Dict, Any


class ForexBotException(Exception):
    """Base exception for the forex bot application."""

    def __init__(
        self,
        message: str,
        error_code: Optional[str] = None,
        details: Optional[Dict[str, Any]] = None
    ):
        self.message = message
        self.error_code = error_code
        self.details = details or {}
        super().__init__(self.message)


class ConfigurationError(ForexBotException):
    """Raised when there's a configuration error."""
    pass


class DatabaseError(ForexBotException):
    """Raised when there's a database error."""
    pass


class DataFetchError(ForexBotException):
    """Raised when data fetching fails."""
    pass


class ChartGenerationError(ForexBotException):
    """Raised when chart generation fails."""
    pass


class TelegramError(ForexBotException):
    """Raised when Telegram API operations fail."""
    pass


class ValidationError(ForexBotException):
    """Raised when data validation fails."""
    pass


class AuthenticationError(ForexBotException):
    """Raised when authentication fails."""
    pass


class AuthorizationError(ForexBotException):
    """Raised when authorization fails."""
    pass


class RateLimitError(ForexBotException):
    """Raised when rate limits are exceeded."""
    pass


class ExternalAPIError(ForexBotException):
    """Raised when external API calls fail."""
    pass


class ScrapingError(ForexBotException):
    """Raised when web scraping fails."""
    pass


class NotificationError(ForexBotException):
    """Raised when notification sending fails."""
    pass
