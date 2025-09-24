"""Notification data models."""

from datetime import datetime
from typing import Optional, Dict, Any
from pydantic import BaseModel, Field, validator


class NotificationBase(BaseModel):
    """Base notification model."""

    user_id: int = Field(description="User ID")
    event_id: int = Field(description="Event ID")
    notification_type: str = Field(description="Notification type")
    message: str = Field(description="Notification message")
    scheduled_time: datetime = Field(description="Scheduled notification time")
    status: str = Field(default="pending", description="Notification status")

    @validator("notification_type")
    def validate_notification_type(cls, v):
        """Validate notification type."""
        valid_types = {"event_reminder", "daily_digest", "price_alert", "system"}
        if v not in valid_types:
            raise ValueError(f"Invalid notification type: {v}")
        return v

    @validator("status")
    def validate_status(cls, v):
        """Validate notification status."""
        valid_statuses = {"pending", "sent", "failed", "cancelled"}
        if v not in valid_statuses:
            raise ValueError(f"Invalid status: {v}")
        return v


class NotificationCreate(NotificationBase):
    """Notification creation model."""
    pass


class NotificationUpdate(BaseModel):
    """Notification update model."""

    status: Optional[str] = None
    sent_at: Optional[datetime] = None
    error_message: Optional[str] = None


class Notification(NotificationBase):
    """Notification model."""

    id: int = Field(description="Notification ID")
    sent_at: Optional[datetime] = Field(default=None, description="Sent timestamp")
    error_message: Optional[datetime] = Field(default=None, description="Error message")
    created_at: datetime = Field(description="Creation timestamp")
    updated_at: datetime = Field(description="Last update timestamp")

    class Config:
        from_attributes = True
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }
