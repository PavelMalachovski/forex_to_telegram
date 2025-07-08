
"""
WSGI entry point for production deployment.
"""

import os
import sys

# Add app directory to Python path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'app'))

from api_server import app
from app.utils.logging_config import setup_logging
from app.database.connection import init_database

# Setup logging
setup_logging()

# Initialize database
try:
    init_database()
except Exception as e:
    print(f"Database initialization failed: {e}")
    sys.exit(1)

if __name__ == "__main__":
    app.run()
