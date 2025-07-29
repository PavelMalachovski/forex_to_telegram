#!/usr/bin/env python3
"""Test script to verify imports work correctly from scripts directory."""

import os
import sys

# Add the parent directory to the Python path so we can import from bot
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))

def test_imports():
    """Test that all required modules can be imported."""
    try:
        from bot.config import Config
        print("✅ bot.config imported successfully")

        from bot.database_service import ForexNewsService
        print("✅ bot.database_service imported successfully")

        from bot.models import Base, DatabaseManager
        print("✅ bot.models imported successfully")

        from bot.scraper import ForexNewsScraper, ChatGPTAnalyzer
        print("✅ bot.scraper imported successfully")

        from bot.utils import setup_logging
        print("✅ bot.utils imported successfully")

        print("\n✅ All imports successful!")
        return True

    except ImportError as e:
        print(f"❌ Import error: {e}")
        return False
    except Exception as e:
        print(f"❌ Unexpected error: {e}")
        return False

if __name__ == "__main__":
    test_imports()
