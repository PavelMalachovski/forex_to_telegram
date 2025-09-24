"""Telegram-related data models."""

from datetime import datetime
from typing import Optional, Dict, Any, List
from pydantic import BaseModel, Field


class TelegramUser(BaseModel):
    """Telegram user model."""

    id: int = Field(description="User ID")
    is_bot: bool = Field(default=False, description="Is bot")
    first_name: str = Field(description="First name")
    last_name: Optional[str] = Field(default=None, description="Last name")
    username: Optional[str] = Field(default=None, description="Username")
    language_code: Optional[str] = Field(default=None, description="Language code")
    is_premium: bool = Field(default=False, description="Is premium")


class TelegramChat(BaseModel):
    """Telegram chat model."""

    id: int = Field(description="Chat ID")
    type: str = Field(description="Chat type")
    title: Optional[str] = Field(default=None, description="Chat title")
    username: Optional[str] = Field(default=None, description="Chat username")
    first_name: Optional[str] = Field(default=None, description="First name")
    last_name: Optional[str] = Field(default=None, description="Last name")


class TelegramMessage(BaseModel):
    """Telegram message model."""

    message_id: int = Field(description="Message ID")
    from_user: Optional[TelegramUser] = Field(default=None, description="From user")
    chat: TelegramChat = Field(description="Chat")
    date: datetime = Field(description="Message date")
    text: Optional[str] = Field(default=None, description="Message text")
    entities: Optional[List[Dict[str, Any]]] = Field(default=None, description="Message entities")

    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }


class TelegramCallback(BaseModel):
    """Telegram callback query model."""

    id: str = Field(description="Callback query ID")
    from_user: TelegramUser = Field(description="From user")
    message: Optional[TelegramMessage] = Field(default=None, description="Message")
    inline_message_id: Optional[str] = Field(default=None, description="Inline message ID")
    chat_instance: str = Field(description="Chat instance")
    data: Optional[str] = Field(default=None, description="Callback data")
    game_short_name: Optional[str] = Field(default=None, description="Game short name")

    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }


class TelegramUpdate(BaseModel):
    """Telegram update model."""

    update_id: int = Field(description="Update ID")
    message: Optional[TelegramMessage] = Field(default=None, description="Message")
    callback_query: Optional[TelegramCallback] = Field(default=None, description="Callback query")
    edited_message: Optional[TelegramMessage] = Field(default=None, description="Edited message")

    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }
