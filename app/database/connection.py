"""
Database connection management.
"""

import logging
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.database.models import Base

logger = logging.getLogger(__name__)

def get_db_session_factory(database_url: str):
    """
    Create and return a database session factory.
    
    Args:
        database_url: Database connection URL
        
    Returns:
        Session factory function
    """
    try:
        # Create engine with appropriate settings
        if database_url.startswith('sqlite'):
            engine = create_engine(
                database_url,
                poolclass=StaticPool,
                connect_args={"check_same_thread": False},
                echo=False
            )
        else:
            engine = create_engine(
                database_url,
                pool_pre_ping=True,
                pool_recycle=300,
                echo=False
            )
        
        # Create tables if they don't exist
        Base.metadata.create_all(bind=engine)
        
        # Create session factory
        SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
        
        logger.info("Database connection established successfully")
        return SessionLocal
        
    except Exception as e:
        logger.error(f"Failed to create database session factory: {e}")
        raise
