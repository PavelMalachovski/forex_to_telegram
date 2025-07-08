
"""Database models for the Forex Bot application."""

from datetime import datetime, date, time
from typing import Optional, List
from sqlalchemy import (
    Column, Integer, String, DateTime, Boolean, Text, Date, Time,
    ForeignKey, UniqueConstraint, Index, Float
)
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship, Mapped

# Create declarative base
Base = declarative_base()


class Currency(Base):
    """Currency model for storing currency information."""
    
    __tablename__ = 'currencies'
    
    id: Mapped[int] = Column(Integer, primary_key=True)
    code: Mapped[str] = Column(String(3), unique=True, nullable=False)
    name: Mapped[str] = Column(String(100), nullable=False)
    symbol: Mapped[Optional[str]] = Column(String(10))
    is_active: Mapped[bool] = Column(Boolean, default=True, nullable=False)
    created_at: Mapped[datetime] = Column(DateTime, default=datetime.utcnow, nullable=False)
    
    # Relationships
    news_events: Mapped[List["NewsEvent"]] = relationship("NewsEvent", back_populates="currency")
    user_preferences: Mapped[List["UserCurrencyPreference"]] = relationship("UserCurrencyPreference", back_populates="currency")


class ImpactLevel(Base):
    """Impact level model for news events."""
    
    __tablename__ = 'impact_levels'
    
    id: Mapped[int] = Column(Integer, primary_key=True)
    code: Mapped[str] = Column(String(10), unique=True, nullable=False)  # LOW, MEDIUM, HIGH
    name: Mapped[str] = Column(String(50), nullable=False)
    description: Mapped[Optional[str]] = Column(Text)
    color: Mapped[Optional[str]] = Column(String(7))  # Hex color code
    priority: Mapped[int] = Column(Integer, default=0, nullable=False)
    is_active: Mapped[bool] = Column(Boolean, default=True, nullable=False)
    created_at: Mapped[datetime] = Column(DateTime, default=datetime.utcnow, nullable=False)
    
    # Relationships
    news_events: Mapped[List["NewsEvent"]] = relationship("NewsEvent", back_populates="impact_level")


class NewsEvent(Base):
    """News event model for storing economic calendar events."""
    
    __tablename__ = 'news_events'
    
    id: Mapped[int] = Column(Integer, primary_key=True)
    event_date: Mapped[date] = Column(Date, nullable=False)
    event_time: Mapped[Optional[time]] = Column(Time)
    currency_id: Mapped[Optional[int]] = Column(Integer, ForeignKey('currencies.id'))
    event_name: Mapped[str] = Column(String(255), nullable=False)
    impact_level_id: Mapped[Optional[int]] = Column(Integer, ForeignKey('impact_levels.id'))
    forecast: Mapped[Optional[str]] = Column(String(50))
    previous: Mapped[Optional[str]] = Column(String(50))
    actual: Mapped[Optional[str]] = Column(String(50))
    source: Mapped[Optional[str]] = Column(String(100))
    source_url: Mapped[Optional[str]] = Column(Text)
    is_active: Mapped[bool] = Column(Boolean, default=True, nullable=False)
    created_at: Mapped[datetime] = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at: Mapped[Optional[datetime]] = Column(DateTime, onupdate=datetime.utcnow)
    
    # Relationships
    currency: Mapped[Optional["Currency"]] = relationship("Currency", back_populates="news_events")
    impact_level: Mapped[Optional["ImpactLevel"]] = relationship("ImpactLevel", back_populates="news_events")
    
    # Indexes
    __table_args__ = (
        Index('idx_news_events_date', 'event_date'),
        Index('idx_news_events_currency', 'currency_id'),
        Index('idx_news_events_impact', 'impact_level_id'),
        Index('idx_news_events_date_currency', 'event_date', 'currency_id'),
    )


class BotUser(Base):
    """Bot user model for storing Telegram user information."""
    
    __tablename__ = 'bot_users'
    
    id: Mapped[int] = Column(Integer, primary_key=True)
    telegram_user_id: Mapped[int] = Column(Integer, unique=True, nullable=False)
    username: Mapped[Optional[str]] = Column(String(100))
    first_name: Mapped[Optional[str]] = Column(String(100))
    last_name: Mapped[Optional[str]] = Column(String(100))
    language_code: Mapped[Optional[str]] = Column(String(10))
    is_active: Mapped[bool] = Column(Boolean, default=True, nullable=False)
    notifications_enabled: Mapped[bool] = Column(Boolean, default=True, nullable=False)
    currency_preference: Mapped[Optional[str]] = Column(String(3))
    timezone: Mapped[Optional[str]] = Column(String(50))
    created_at: Mapped[datetime] = Column(DateTime, default=datetime.utcnow, nullable=False)
    last_activity: Mapped[Optional[datetime]] = Column(DateTime)
    
    # Relationships
    currency_preferences: Mapped[List["UserCurrencyPreference"]] = relationship("UserCurrencyPreference", back_populates="user")
    notification_settings: Mapped[Optional["UserNotificationSettings"]] = relationship("UserNotificationSettings", back_populates="user", uselist=False)


class UserCurrencyPreference(Base):
    """User currency preference model."""
    
    __tablename__ = 'user_currency_preferences'
    
    id: Mapped[int] = Column(Integer, primary_key=True)
    user_id: Mapped[int] = Column(Integer, ForeignKey('bot_users.id'), nullable=False)
    currency_id: Mapped[int] = Column(Integer, ForeignKey('currencies.id'), nullable=False)
    is_primary: Mapped[bool] = Column(Boolean, default=False, nullable=False)
    created_at: Mapped[datetime] = Column(DateTime, default=datetime.utcnow, nullable=False)
    
    # Relationships
    user: Mapped["BotUser"] = relationship("BotUser", back_populates="currency_preferences")
    currency: Mapped["Currency"] = relationship("Currency", back_populates="user_preferences")
    
    # Constraints
    __table_args__ = (
        UniqueConstraint('user_id', 'currency_id', name='uq_user_currency'),
    )


class UserNotificationSettings(Base):
    """User notification settings model."""
    
    __tablename__ = 'user_notification_settings'
    
    id: Mapped[int] = Column(Integer, primary_key=True)
    user_id: Mapped[int] = Column(Integer, ForeignKey('bot_users.id'), unique=True, nullable=False)
    notifications_enabled: Mapped[bool] = Column(Boolean, default=True, nullable=False)
    high_impact_only: Mapped[bool] = Column(Boolean, default=True, nullable=False)
    advance_notice_minutes: Mapped[int] = Column(Integer, default=30, nullable=False)
    daily_summary_enabled: Mapped[bool] = Column(Boolean, default=True, nullable=False)
    daily_summary_time: Mapped[Optional[time]] = Column(Time, default=time(8, 0))  # 08:00 UTC
    weekend_notifications: Mapped[bool] = Column(Boolean, default=False, nullable=False)
    created_at: Mapped[datetime] = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at: Mapped[Optional[datetime]] = Column(DateTime, onupdate=datetime.utcnow)
    
    # Relationships
    user: Mapped["BotUser"] = relationship("BotUser", back_populates="notification_settings")


class ScrapingLog(Base):
    """Scraping log model for tracking scraping activities."""
    
    __tablename__ = 'scraping_logs'
    
    id: Mapped[int] = Column(Integer, primary_key=True)
    source: Mapped[str] = Column(String(100), nullable=False)
    start_time: Mapped[datetime] = Column(DateTime, nullable=False)
    end_time: Mapped[Optional[datetime]] = Column(DateTime)
    status: Mapped[str] = Column(String(20), nullable=False)  # SUCCESS, ERROR, RUNNING
    events_scraped: Mapped[int] = Column(Integer, default=0, nullable=False)
    events_saved: Mapped[int] = Column(Integer, default=0, nullable=False)
    error_message: Mapped[Optional[str]] = Column(Text)
    metadata: Mapped[Optional[str]] = Column(Text)  # JSON string for additional data
    created_at: Mapped[datetime] = Column(DateTime, default=datetime.utcnow, nullable=False)
    
    # Indexes
    __table_args__ = (
        Index('idx_scraping_logs_source', 'source'),
        Index('idx_scraping_logs_status', 'status'),
        Index('idx_scraping_logs_start_time', 'start_time'),
    )
