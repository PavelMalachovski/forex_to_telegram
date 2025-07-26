"""
Migration script to add notification fields to the User table.
"""

from sqlalchemy import create_engine, text
import os

def run_migration():
    """Add notification fields to the User table."""

    # Get database URL from environment or use default
    database_url = os.getenv('DATABASE_URL')
    if not database_url:
        # Use default from alembic.ini
        database_url = "postgresql://forex_user:0VGr0I02HDKaiVUVT21Z3ORnEiCBAYtC@dpg-d1mkim2li9vc73c7toi0-a/forex_db_0myg"

    engine = create_engine(database_url)

    with engine.connect() as conn:
        # Check if columns already exist
        result = conn.execute(text("""
            SELECT column_name
            FROM information_schema.columns
            WHERE table_name = 'users'
            AND column_name IN ('notifications_enabled', 'notification_minutes', 'notification_impact_levels')
        """))

        existing_columns = [row[0] for row in result]

        # Add notifications_enabled column if it doesn't exist
        if 'notifications_enabled' not in existing_columns:
            conn.execute(text("""
                ALTER TABLE users
                ADD COLUMN notifications_enabled BOOLEAN DEFAULT FALSE
            """))
            print("Added notifications_enabled column")

        # Add notification_minutes column if it doesn't exist
        if 'notification_minutes' not in existing_columns:
            conn.execute(text("""
                ALTER TABLE users
                ADD COLUMN notification_minutes INTEGER DEFAULT 30
            """))
            print("Added notification_minutes column")

        # Add notification_impact_levels column if it doesn't exist
        if 'notification_impact_levels' not in existing_columns:
            conn.execute(text("""
                ALTER TABLE users
                ADD COLUMN notification_impact_levels TEXT DEFAULT 'high'
            """))
            print("Added notification_impact_levels column")

        conn.commit()
        print("Migration completed successfully!")

if __name__ == "__main__":
    run_migration()
