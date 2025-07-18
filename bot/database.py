
import os
from sqlalchemy import create_engine, Column, String, Date, Float, Integer, DateTime, UniqueConstraint
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from sqlalchemy.dialects.postgresql import insert
from datetime import datetime
import logging

logger = logging.getLogger(__name__)

Base = declarative_base()

class ForexEvent(Base):
    __tablename__ = 'forex_events'
    
    id = Column(Integer, primary_key=True)
    currencies = Column(String(10), nullable=False)
    date = Column(Date, nullable=False)
    impact = Column(String(20), nullable=False)
    actual = Column(String(50))
    forecast = Column(String(50))
    previous = Column(String(50))
    event_title = Column(String(200))
    created_at = Column(DateTime, default=datetime.utcnow)
    
    __table_args__ = (
        UniqueConstraint('currencies', 'date', 'event_title', name='unique_event'),
    )

class DatabaseManager:
    def __init__(self, database_url):
        self.engine = create_engine(database_url)
        self.SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=self.engine)
        
    def create_tables(self):
        Base.metadata.create_all(bind=self.engine)
        
    def get_session(self):
        return self.SessionLocal()
        
    def insert_events(self, events_data):
        """Insert events with upsert logic to avoid duplicates"""
        session = self.get_session()
        try:
            for event_data in events_data:
                stmt = insert(ForexEvent).values(**event_data)
                stmt = stmt.on_conflict_do_nothing(
                    index_elements=['currencies', 'date', 'event_title']
                )
                session.execute(stmt)
            session.commit()
            logger.info(f"Inserted {len(events_data)} events into database")
        except Exception as e:
            session.rollback()
            logger.error(f"Error inserting events: {e}")
            raise
        finally:
            session.close()
            
    def get_events_by_date_range(self, start_date, end_date):
        """Get events within date range"""
        session = self.get_session()
        try:
            events = session.query(ForexEvent).filter(
                ForexEvent.date >= start_date,
                ForexEvent.date <= end_date
            ).order_by(ForexEvent.date, ForexEvent.currencies).all()
            return events
        finally:
            session.close()
            
    def check_data_exists(self, start_date, end_date):
        """Check if data exists for the given date range"""
        session = self.get_session()
        try:
            count = session.query(ForexEvent).filter(
                ForexEvent.date >= start_date,
                ForexEvent.date <= end_date
            ).count()
            return count > 0
        finally:
            session.close()

# Global database manager instance
db_manager = None

def get_db_manager():
    global db_manager
    if db_manager is None:
        from .config import DATABASE_URL
        db_manager = DatabaseManager(DATABASE_URL)
    return db_manager
