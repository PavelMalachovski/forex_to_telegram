
"""
Database connection management.
"""

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session
from sqlalchemy.pool import QueuePool
from app.config import config
import logging
import os

logger = logging.getLogger(__name__)

# Database connection with fallback handling
def create_database_engine():
    """Create database engine with proper error handling."""
    try:
        # Use the properly formatted DATABASE_URL
        database_url = config.get_database_url()
        
        if not database_url:
            logger.error("DATABASE_URL is not configured")
            return None
            
        logger.info(f"Connecting to database: {database_url.split('@')[0]}@***")
        
        engine = create_engine(
            database_url,
            poolclass=QueuePool,
            pool_size=10,
            max_overflow=20,
            pool_pre_ping=True,
            pool_recycle=3600,
            echo=config.LOG_LEVEL == 'DEBUG',
            connect_args={
                "connect_timeout": 10,
                "application_name": "forex_bot"
            }
        )
        
        # Test connection
        with engine.connect() as conn:
            conn.execute("SELECT 1")
            logger.info("Database connection successful")
            
        return engine
        
    except Exception as e:
        logger.error(f"Failed to create database engine: {e}")
        return None

# Create database engine with error handling
engine = create_database_engine()

# Create session factory only if engine is available
if engine:
    SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
else:
    SessionLocal = None
    logger.warning("Database engine not available - running in fallback mode")

def get_db() -> Session:
    """
    Dependency to get database session.
    
    Returns:
        Session: SQLAlchemy database session or None if database unavailable
    """
    if not SessionLocal:
        logger.warning("Database session factory not available")
        return None
        
    try:
        db = SessionLocal()
        yield db
    except Exception as e:
        logger.error(f"Database session error: {e}")
        yield None
    finally:
        if 'db' in locals() and db:
            db.close()

def get_db_session():
    """
    Get database session directly (not generator).
    
    Returns:
        Session: SQLAlchemy database session or None if database unavailable
    """
    if not SessionLocal:
        logger.warning("Database session factory not available")
        return None
        
    try:
        return SessionLocal()
    except Exception as e:
        logger.error(f"Failed to create database session: {e}")
        return None

def init_database():
    """Initialize database tables."""
    if not engine:
        logger.error("Cannot initialize database - engine not available")
        return False
        
    try:
        from .models import Base
        Base.metadata.create_all(bind=engine)
        logger.info("Database tables created successfully")
        return True
    except Exception as e:
        logger.error(f"Failed to create database tables: {e}")
        return False
