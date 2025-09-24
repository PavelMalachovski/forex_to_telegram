#!/usr/bin/env python3
"""Database migration script for the modern FastAPI application."""

import asyncio
import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from alembic import command
from alembic.config import Config
from src.database.connection import db_manager
from src.core.logging import configure_logging, get_logger

configure_logging()
logger = get_logger(__name__)


async def run_migrations():
    """Run database migrations."""
    try:
        # Initialize database connection
        await db_manager.initialize()

        # Configure Alembic
        alembic_cfg = Config("alembic.ini")

        # Run migrations
        logger.info("Running database migrations...")
        command.upgrade(alembic_cfg, "head")

        logger.info("Database migrations completed successfully")

    except Exception as e:
        logger.error(f"Migration failed: {e}")
        raise
    finally:
        await db_manager.close()


if __name__ == "__main__":
    asyncio.run(run_migrations())
