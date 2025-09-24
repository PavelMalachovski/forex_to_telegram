"""SQLAlchemy database models."""

from datetime import datetime, time
from typing import Optional, List
from sqlalchemy import (
    Column, Integer, String, DateTime, Text, Boolean,
    Index, Time, JSON, ForeignKey
)
from sqlalchemy.ext.asyncio import AsyncAttrs
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


class Base(AsyncAttrs, DeclarativeBase):
    """Base class for all database models."""
    pass


class UserModel(Base):
    """User database model."""

    __tablename__ = "users"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    telegram_id: Mapped[int] = mapped_column(Integer, unique=True, nullable=False, index=True)
    username: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    first_name: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    last_name: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    language_code: Mapped[Optional[str]] = mapped_column(String(10), nullable=True)
    is_bot: Mapped[bool] = mapped_column(Boolean, default=False)
    is_premium: Mapped[bool] = mapped_column(Boolean, default=False)

    # Preferences as JSON
    preferred_currencies: Mapped[List[str]] = mapped_column(JSON, default=list)
    impact_levels: Mapped[List[str]] = mapped_column(JSON, default=lambda: ["high", "medium"])
    analysis_required: Mapped[bool] = mapped_column(Boolean, default=True)
    digest_time: Mapped[time] = mapped_column(Time, default=time(8, 0))
    timezone: Mapped[str] = mapped_column(String(50), default="Europe/Prague")

    # Notification settings
    notifications_enabled: Mapped[bool] = mapped_column(Boolean, default=False)
    notification_minutes: Mapped[int] = mapped_column(Integer, default=30)
    notification_impact_levels: Mapped[List[str]] = mapped_column(JSON, default=lambda: ["high"])

    # Chart settings
    charts_enabled: Mapped[bool] = mapped_column(Boolean, default=False)
    chart_type: Mapped[str] = mapped_column(String(20), default="single")
    chart_window_hours: Mapped[int] = mapped_column(Integer, default=2)

    # Timestamps
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    last_active: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)

    # Relationships
    notifications: Mapped[List["NotificationModel"]] = relationship(
        "NotificationModel", back_populates="user", cascade="all, delete-orphan"
    )

    __table_args__ = (
        Index("idx_telegram_id", "telegram_id"),
        Index("idx_created_at", "created_at"),
        Index("idx_last_active", "last_active"),
    )


class ForexNewsModel(Base):
    """Forex news database model."""

    __tablename__ = "forex_news"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    date: Mapped[datetime] = mapped_column(DateTime, nullable=False, index=True)
    time: Mapped[str] = mapped_column(String(50), nullable=False)
    currency: Mapped[str] = mapped_column(String(10), nullable=False, index=True)
    event: Mapped[str] = mapped_column(Text, nullable=False)
    actual: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    forecast: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    previous: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    impact_level: Mapped[str] = mapped_column(String(20), nullable=False, index=True)
    analysis: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # Timestamps
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    notifications: Mapped[List["NotificationModel"]] = relationship(
        "NotificationModel", back_populates="event", cascade="all, delete-orphan"
    )

    __table_args__ = (
        Index("idx_date_currency_time", "date", "currency", "time"),
        Index("idx_date_impact", "date", "impact_level"),
        Index("idx_currency_impact", "currency", "impact_level"),
    )


class NotificationModel(Base):
    """Notification database model."""

    __tablename__ = "notifications"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(Integer, ForeignKey("users.id"), nullable=False)
    event_id: Mapped[int] = mapped_column(Integer, ForeignKey("forex_news.id"), nullable=False)
    notification_type: Mapped[str] = mapped_column(String(50), nullable=False)
    message: Mapped[str] = mapped_column(Text, nullable=False)
    scheduled_time: Mapped[datetime] = mapped_column(DateTime, nullable=False, index=True)
    status: Mapped[str] = mapped_column(String(20), default="pending", index=True)
    sent_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    error_message: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # Timestamps
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    user: Mapped["UserModel"] = relationship("UserModel", back_populates="notifications")
    event: Mapped["ForexNewsModel"] = relationship("ForexNewsModel", back_populates="notifications")

    __table_args__ = (
        Index("idx_user_scheduled", "user_id", "scheduled_time"),
        Index("idx_status_scheduled", "status", "scheduled_time"),
        Index("idx_notification_type", "notification_type"),
    )
