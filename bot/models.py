from sqlalchemy import create_engine, Column, Integer, String, DateTime, Text, Boolean, Index, text, Time
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from datetime import datetime
import os

Base = declarative_base()


class ForexNews(Base):
    """Database model for storing forex news data."""
    __tablename__ = 'forex_news'

    id = Column(Integer, primary_key=True)
    date = Column(DateTime, nullable=False, index=True)
    time = Column(String(50), nullable=False)
    currency = Column(String(10), nullable=False)
    event = Column(Text, nullable=False)
    actual = Column(String(100))
    forecast = Column(String(100))
    previous = Column(String(100))
    impact_level = Column(String(20), nullable=False)  # high, medium, low
    analysis = Column(Text)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Composite index for efficient queries
    __table_args__ = (
        Index('idx_date_currency_time', 'date', 'currency', 'time'),
        Index('idx_date_impact', 'date', 'impact_level'),
    )

    def __repr__(self):
        return f"<ForexNews(date={self.date}, currency={self.currency}, event={self.event[:50]})>"

    def to_dict(self):
        """Convert model to dictionary for API responses."""
        return {
            'id': self.id,
            'date': self.date.isoformat() if self.date else None,
            'time': self.time,
            'currency': self.currency,
            'event': self.event,
            'actual': self.actual,
            'forecast': self.forecast,
            'previous': self.previous,
            'impact_level': self.impact_level,
            'analysis': self.analysis,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None,
        }


class User(Base):
    """Database model for storing user preferences."""
    __tablename__ = 'users'

    id = Column(Integer, primary_key=True)
    telegram_id = Column(Integer, unique=True, nullable=False, index=True)
    preferred_currencies = Column(Text, default="")  # Comma-separated list of currencies
    impact_levels = Column(Text, default="high,medium")  # Comma-separated list of impact levels
    analysis_required = Column(Boolean, default=True)
    digest_time = Column(Time, default=datetime.strptime("08:00", "%H:%M").time())  # Default 8:00 AM
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    def __repr__(self):
        return f"<User(telegram_id={self.telegram_id}, currencies={self.preferred_currencies})>"

    def to_dict(self):
        """Convert model to dictionary for API responses."""
        return {
            'id': self.id,
            'telegram_id': self.telegram_id,
            'preferred_currencies': self.preferred_currencies,
            'impact_levels': self.impact_levels,
            'analysis_required': self.analysis_required,
            'digest_time': self.digest_time.strftime("%H:%M") if self.digest_time else "08:00",
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None,
        }

    def get_currencies_list(self):
        """Get preferred currencies as a list."""
        if not self.preferred_currencies:
            return []
        return [c.strip() for c in self.preferred_currencies.split(",") if c.strip()]

    def get_impact_levels_list(self):
        """Get impact levels as a list."""
        if not self.impact_levels:
            return ["high", "medium"]
        return [i.strip() for i in self.impact_levels.split(",") if i.strip()]

    def set_currencies_list(self, currencies_list):
        """Set preferred currencies from a list."""
        self.preferred_currencies = ",".join(currencies_list)

    def set_impact_levels_list(self, impact_levels_list):
        """Set impact levels from a list."""
        self.impact_levels = ",".join(impact_levels_list)


class DatabaseManager:
    """Manages database connections and operations."""

    def __init__(self, database_url=None):
        if database_url:
            self.database_url = database_url
        else:
            # Use environment variables for database connection
            self.database_url = os.getenv('DATABASE_URL')

        if not self.database_url:
            raise ValueError("Database URL not provided. Set DATABASE_URL environment variable.")

        self.engine = create_engine(self.database_url)
        self.SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=self.engine)

    def create_tables(self):
        """Create all database tables."""
        Base.metadata.create_all(bind=self.engine)

    def get_session(self):
        """Get a database session."""
        return self.SessionLocal()

    def close_session(self, session):
        """Close a database session."""
        session.close()

    def health_check(self):
        """Check if database is accessible."""
        try:
            with self.get_session() as session:
                session.execute(text("SELECT 1"))
                return True
        except Exception as e:
            print(f"Database health check failed: {e}")
            return False
