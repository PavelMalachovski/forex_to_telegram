import sqlite3
import logging

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")

def clear_db():
    logging.info("Clearing the news database...")
    try:
        conn = sqlite3.connect('news.db')
        c = conn.cursor()
        c.execute('DELETE FROM news')
        conn.commit()
        conn.close()
        logging.info("Database cleared successfully")
    except Exception as e:
        logging.error(f"Failed to clear database: {e}")

if __name__ == "__main__":
    clear_db()
