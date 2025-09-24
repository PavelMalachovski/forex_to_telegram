"""Application configuration using Pydantic Settings."""

from typing import Optional, List
from pydantic import Field, validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class DatabaseSettings(BaseSettings):
    """Database configuration."""

    url: Optional[str] = Field(default=None, description="Database URL")
    host: Optional[str] = Field(default=None, description="Database host")
    port: int = Field(default=5432, description="Database port")
    name: Optional[str] = Field(default=None, description="Database name")
    user: Optional[str] = Field(default=None, description="Database user")
    password: Optional[str] = Field(default=None, description="Database password")
    pool_size: int = Field(default=10, description="Connection pool size")
    max_overflow: int = Field(default=20, description="Max overflow connections")
    echo: bool = Field(default=False, description="Echo SQL queries")

    model_config = SettingsConfigDict(env_prefix="DB_")


class RedisSettings(BaseSettings):
    """Redis configuration."""

    url: Optional[str] = Field(default="redis://localhost:6379", description="Redis URL")
    host: str = Field(default="localhost", description="Redis host")
    port: int = Field(default=6379, description="Redis port")
    password: Optional[str] = Field(default=None, description="Redis password")
    db: int = Field(default=0, description="Redis database number")
    max_connections: int = Field(default=10, description="Max Redis connections")

    model_config = SettingsConfigDict(env_prefix="REDIS_")


class TelegramSettings(BaseSettings):
    """Telegram bot configuration."""

    bot_token: str = Field(default="your-telegram-bot-token-here", description="Telegram bot token")
    webhook_url: Optional[str] = Field(default=None, description="Webhook URL")
    webhook_secret: Optional[str] = Field(default=None, description="Webhook secret")
    chat_id: Optional[str] = Field(default=None, description="Default chat ID")

    model_config = SettingsConfigDict(env_prefix="TELEGRAM_")


class APISettings(BaseSettings):
    """External API configuration."""

    alpha_vantage_key: Optional[str] = Field(default=None, description="Alpha Vantage API key")
    openai_api_key: Optional[str] = Field(default=None, description="OpenAI API key")
    openai_model: str = Field(default="gpt-4o-mini", description="OpenAI model")
    openai_temperature: float = Field(default=0.25, description="OpenAI temperature")
    openai_max_tokens: int = Field(default=500, description="OpenAI max tokens")
    openai_enabled: bool = Field(default=True, description="Enable OpenAI features")
    openai_rate_limit_seconds: int = Field(default=15, description="Rate limit in seconds")

    model_config = SettingsConfigDict(env_prefix="API_")


class ChartSettings(BaseSettings):
    """Chart generation configuration."""

    enable_alpha_vantage: bool = Field(default=False, description="Enable Alpha Vantage fallback")
    enable_alt_symbols: bool = Field(default=False, description="Enable alternative symbols")
    allow_mock_data: bool = Field(default=False, description="Allow mock data generation")
    display_timezone: str = Field(default="Europe/Prague", description="Display timezone")
    yf_min_request_interval_sec: float = Field(default=3.0, description="Yahoo Finance request interval")
    chart_retention_days: int = Field(default=3, description="Chart retention days")

    model_config = SettingsConfigDict(env_prefix="CHART_")


class SecuritySettings(BaseSettings):
    """Security configuration."""

    secret_key: str = Field(default="your-secret-key-change-in-production-minimum-32-characters", description="Secret key for JWT tokens")
    algorithm: str = Field(default="HS256", description="JWT algorithm")
    access_token_expire_minutes: int = Field(default=30, description="Access token expiration")
    refresh_token_expire_days: int = Field(default=7, description="Refresh token expiration")
    api_key: Optional[str] = Field(default=None, description="API key for internal endpoints")

    model_config = SettingsConfigDict(env_prefix="SECURITY_")


class LoggingSettings(BaseSettings):
    """Logging configuration."""

    level: str = Field(default="INFO", description="Logging level")
    format: str = Field(default="%(asctime)s [%(levelname)s] %(name)s: %(message)s", description="Log format")
    file_path: Optional[str] = Field(default=None, description="Log file path")
    max_file_size: int = Field(default=10485760, description="Max log file size in bytes")
    backup_count: int = Field(default=5, description="Number of backup files")

    model_config = SettingsConfigDict(env_prefix="LOG_")


class Settings(BaseSettings):
    """Main application settings."""

    # Environment
    environment: str = Field(default="development", description="Environment")
    debug: bool = Field(default=False, description="Debug mode")

    # Server
    host: str = Field(default="0.0.0.0", description="Server host")
    port: int = Field(default=8000, description="Server port")
    workers: int = Field(default=1, description="Number of workers")

    # Application
    app_name: str = Field(default="Forex News Bot", description="Application name")
    app_version: str = Field(default="2.0.0", description="Application version")
    app_description: str = Field(default="Modern forex news bot", description="Application description")

    # Sub-settings
    database: DatabaseSettings = Field(default_factory=DatabaseSettings)
    redis: RedisSettings = Field(default_factory=RedisSettings)
    telegram: TelegramSettings = Field(default_factory=TelegramSettings)
    api: APISettings = Field(default_factory=APISettings)
    chart: ChartSettings = Field(default_factory=ChartSettings)
    security: SecuritySettings = Field(default_factory=SecuritySettings)
    logging: LoggingSettings = Field(default_factory=LoggingSettings)

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore"
    )

    @validator("environment")
    def validate_environment(cls, v):
        """Validate environment value."""
        allowed_envs = ["development", "staging", "production"]
        if v not in allowed_envs:
            raise ValueError(f"Environment must be one of {allowed_envs}")
        return v

    @validator("debug")
    def validate_debug(cls, v, values):
        """Validate debug mode."""
        if values.get("environment") == "production" and v:
            raise ValueError("Debug mode cannot be enabled in production")
        return v


# Global settings instance
settings = Settings()
