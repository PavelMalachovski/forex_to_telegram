
"""
Main entry point for the Forex Bot application.
"""

import logging
import sys
import os
from pathlib import Path

# Add the project root to Python path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from app.bot.main import main

if __name__ == "__main__":
    main()
