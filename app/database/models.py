
"""
SQLAlchemy models for the Forex Bot application.
"""

from sqlalchemy import Column, Integer, BigInteger, String, Text, Date, Time, DateTime, Boolean, ForeignKey, UniqueConstraint
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship
from datetime import datetime

Base = declarative_base()

class Currency(Base):
    """Currency model."""
    __tablename__ = 'currencies'
    
    id = Column(Integer, primary_key=True)
    code = Column(String(3), unique=True, nullable=False, index=True)
    name = Column(String(50), nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # Relationships
    news_events = relationship("NewsEvent", back_populates="currency")
    user_preferences = relationship("UserCurrencyPreference", back_populates="currency")
    
    def __repr__(self):
        return f"<Currency(code='{self.code}', name='{self.name}')>"

class ImpactLevel(Base):
    """Impact level model."""
    __tablename__ = 'impact_levels'
    
    id = Column(Integer, primary_key=True)
    code = Column(String(20), unique=True, nullable=False, index=True)
    name = Column(String(50), nullable=False)
    priority = Column(Integer, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # Relationships
    news_events = relationship("NewsEvent", back_populates="impact_level")
    
    def __repr__(self):
        return f"<ImpactLevel(code='{self.code}', name='{self.name}', priority={self.priority})>"

class NewsEvent(Base):
    """News event model."""
    __tablename__ = 'news_events'
    
    id = Column(Integer, primary_key=True)
    event_date = Column(Date, nullable=False, index=True)
    event_time = Column(Time, nullable=False)
    currency_id = Column(Integer, ForeignKey('currencies.id'), nullable=False, index=True)
    impact_level_id = Column(Integer, ForeignKey('impact_levels.id'), nullable=False, index=True)
    event_name = Column(Text, nullable=False)
    forecast = Column(Text)
    previous_value = Column(Text)
    actual_value = Column(Text)
    analysis = Column(Text)
    source_url = Column(Text)
    scraped_at = Column(DateTime, default=datetime.utcnow, index=True)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    currency = relationship("Currency", back_populates="news_events")
    impact_level = relationship("ImpactLevel", back_populates="news_events")
    
    # Unique constraint
    __table_args__ = (
        UniqueConstraint('event_date', 'event_time', 'currency_id', 'event_name', name='uq_news_event'),
    )
    
    def __repr__(self):
        return f"<NewsEvent(date='{self.event_date}', time='{self.event_time}', event='{self.event_name}')>"

class BotUser(Base):
    """Bot user model."""
    __tablename__ = 'bot_users'
    
    id = Column(Integer, primary_key=True)
    telegram_user_id = Column(BigInteger, unique=True, nullable=False, index=True)
    telegram_username = Column(String(255))
    first_name = Column(String(255))
    last_name = Column(String(255))
    language_code = Column(String(10))
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    last_activity = Column(DateTime, default=datetime.utcnow)
    
    # Relationships
    currency_preferences = relationship("UserCurrencyPreference", back_populates="user", cascade="all, delete-orphan")
    notification_settings = relationship("UserNotificationSettings", back_populates="user", uselist=False, cascade="all, delete-orphan")
    
    def __repr__(self):
        return f"<BotUser(telegram_user_id={self.telegram_user_id}, username='{self.telegram_username}')>"

class UserCurrencyPreference(Base):
    """User currency preference model."""
    __tablename__ = 'user_currency_preferences'
    
    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey('bot_users.id', ondelete='CASCADE'), nullable=False)
    currency_id = Column(Integer, ForeignKey('currencies.id'), nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # Relationships
    user = relationship("BotUser", back_populates="currency_preferences")
    currency = relationship("Currency", back_populates="user_preferences")
    
    # Unique constraint
    __table_args__ = (
        UniqueConstraint('user_id', 'currency_id', name='uq_user_currency'),
    )
    
    def __repr__(self):
        return f"<UserCurrencyPreference(user_id={self.user_id}, currency_id={self.currency_id})>"

class ScrapingLog(Base):
    """Scraping log model."""
    __tablename__ = 'scraping_logs'
    
    id = Column(Integer, primary_key=True)
    start_date = Column(Date, nullable=False)
    end_date = Column(Date, nullable=False)
    events_scraped = Column(Integer, default=0)
    events_updated = Column(Integer, default=0)
    errors_count = Column(Integer, default=0)
    duration_seconds = Column(Integer)
    status = Column(String(20), nullable=False)  # 'success', 'partial', 'failed'
    error_message = Column(Text)
    created_at = Column(DateTime, default=datetime.utcnow, index=True)
    
    def __repr__(self):
        return f"<ScrapingLog(start_date='{self.start_date}', status='{self.status}', events_scraped={self.events_scraped})>"

class UserNotificationSettings(Base):
    """User notification settings model."""
    __tablename__ = 'user_notification_settings'
    
    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey('bot_users.id', ondelete='CASCADE'), nullable=False, unique=True)
    notifications_enabled = Column(Boolean, default=True)
    notify_15_minutes = Column(Boolean, default=False)
    notify_30_minutes = Column(Boolean, default=False)
    notify_60_minutes = Column(Boolean, default=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    user = relationship("BotUser", back_populates="notification_settings")
    
    def __repr__(self):
        return f"<UserNotificationSettings(user_id={self.user_id}, enabled={self.notifications_enabled})>"

# Alias for backward compatibility
User = BotUser
