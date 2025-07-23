import os
from bot.models import Base, DatabaseManager

if __name__ == "__main__":
    print("WARNING: This will DROP ALL TABLES and DELETE ALL DATA in the database!")
    confirm = input("Type 'yes' to continue: ").strip().lower()
    if confirm != 'yes':
        print("Aborted.")
        exit(0)

    db_url = os.getenv('DATABASE_URL')
    if not db_url:
        print("DATABASE_URL environment variable not set.")
        exit(1)

    db_manager = DatabaseManager(db_url)
    engine = db_manager.engine
    print("Dropping all tables...")
    Base.metadata.drop_all(bind=engine)
    print("All tables dropped. Database is now empty.")
