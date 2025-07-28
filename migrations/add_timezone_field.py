"""
Migration script to add timezone field to the User table.
"""

from sqlalchemy import create_engine, text
import os

def run_migration():
    """Add timezone field to the User table."""

    # Get database URL from environment or use default
    database_url = os.getenv('DATABASE_URL')
    if not database_url:
        # Use default from alembic.ini
        database_url = "postgresql://forex_user:0VGr0I02HDKaiVUVT21Z3ORnEiCBAYtC@dpg-d1mkim2li9vc73c7toi0-a/forex_db_0myg"

    engine = create_engine(database_url)

    with engine.connect() as conn:
        # Check if timezone column already exists
        result = conn.execute(text("""
            SELECT column_name
            FROM information_schema.columns
            WHERE table_name = 'users'
            AND column_name = 'timezone'
        """))

        existing_columns = [row[0] for row in result]

        # Add timezone column if it doesn't exist
        if 'timezone' not in existing_columns:
            conn.execute(text("""
                ALTER TABLE users
                ADD COLUMN timezone VARCHAR(50) DEFAULT 'Europe/Prague'
            """))
            print("Added timezone column")
        else:
            print("Timezone column already exists")

        conn.commit()
        print("Migration completed successfully!")

if __name__ == "__main__":
    run_migration()