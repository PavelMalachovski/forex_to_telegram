#!/usr/bin/env python3
"""Organize test files alphabetically in the tests directory."""

import os
import shutil
from pathlib import Path

def organize_tests():
    """Organize test files alphabetically."""
    tests_dir = Path("tests")

    if not tests_dir.exists():
        print("❌ Tests directory not found")
        return False

    # Get all test files
    test_files = [f for f in tests_dir.iterdir() if f.is_file() and f.name.startswith("test_") and f.suffix == ".py"]

    if not test_files:
        print("ℹ️ No test files found")
        return True

    # Sort test files alphabetically
    test_files.sort(key=lambda x: x.name)

    print("📋 Test files (alphabetically ordered):")
    for i, test_file in enumerate(test_files, 1):
        print(f"  {i:2d}. {test_file.name}")

    print(f"\n✅ Found {len(test_files)} test files")
    return True

if __name__ == "__main__":
    organize_tests()
