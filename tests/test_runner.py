#!/usr/bin/env python3
"""Test runner script for the modern FastAPI application."""

import subprocess
import sys
import os
from pathlib import Path


def run_command(command: str, description: str) -> bool:
    """Run a command and return success status."""
    print(f"\n{'='*60}")
    print(f"Running: {description}")
    print(f"Command: {command}")
    print(f"{'='*60}")

    try:
        result = subprocess.run(command, shell=True, check=True, capture_output=True, text=True)
        print("✅ SUCCESS")
        if result.stdout:
            print("Output:")
            print(result.stdout)
        return True
    except subprocess.CalledProcessError as e:
        print("❌ FAILED")
        print(f"Exit code: {e.returncode}")
        if e.stdout:
            print("Output:")
            print(e.stdout)
        if e.stderr:
            print("Error:")
            print(e.stderr)
        return False


def main():
    """Main test runner function."""
    print("🚀 Starting comprehensive test suite for Forex Bot")

    # Change to project root directory
    project_root = Path(__file__).parent.parent
    os.chdir(project_root)

    # Test commands to run
    test_commands = [
        # Unit tests
        ("pytest tests/test_core/ -v", "Core module unit tests"),
        ("pytest tests/test_models/ -v", "Data models unit tests"),
        ("pytest tests/test_services/ -v", "Services unit tests"),

        # API tests
        ("pytest tests/test_api/ -v", "API endpoints tests"),

        # Integration tests
        ("pytest tests/test_integration/ -v", "Integration tests"),

        # Performance tests (optional)
        ("pytest tests/test_performance/ -v -m 'not slow'", "Performance tests (fast only)"),

        # Full test suite
        ("pytest tests/ -v --tb=short", "Complete test suite"),

        # Coverage report
        ("pytest tests/ --cov=src --cov-report=html --cov-report=term", "Test coverage report"),

        # Linting
        ("python -m flake8 src/ --max-line-length=100", "Code linting"),

        # Type checking
        ("python -m mypy src/ --ignore-missing-imports", "Type checking"),
    ]

    # Track results
    results = []

    for command, description in test_commands:
        success = run_command(command, description)
        results.append((description, success))

        if not success:
            print(f"\n⚠️  {description} failed. Continuing with remaining tests...")

    # Summary
    print(f"\n{'='*60}")
    print("TEST SUMMARY")
    print(f"{'='*60}")

    passed = sum(1 for _, success in results if success)
    total = len(results)

    for description, success in results:
        status = "✅ PASSED" if success else "❌ FAILED"
        print(f"{status}: {description}")

    print(f"\nOverall: {passed}/{total} test suites passed")

    if passed == total:
        print("🎉 All tests passed! The application is ready for deployment.")
        return 0
    else:
        print("⚠️  Some tests failed. Please review the output above.")
        return 1


if __name__ == "__main__":
    sys.exit(main())
