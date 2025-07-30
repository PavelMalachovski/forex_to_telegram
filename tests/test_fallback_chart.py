#!/usr/bin/env python3
"""
Test script to simulate Yahoo Finance API failures and test fallback mechanisms.
"""

import sys
import os
import logging
from datetime import datetime, timedelta
import pytz
from unittest.mock import patch

# Add the bot directory to the path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from bot.chart_service import ChartService

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(name)s: %(message)s'
)

def test_fallback_chart():
    """Test the fallback mechanisms when Yahoo Finance fails."""

    # Initialize the chart service
    chart_service = ChartService()

    # Test parameters
    test_time = datetime.now(pytz.UTC) - timedelta(hours=2)  # 2 hours ago

    print("Testing fallback chart functionality...")
    print(f"Test time: {test_time}")
    print()

    # Test 1: Mock Yahoo Finance failure for single currency
    print("Test 1: Single currency chart with simulated Yahoo Finance failure")
    print("-" * 60)

    def mock_yfinance_failure(*args, **kwargs):
        """Mock function that simulates yfinance failure."""
        import pandas as pd
        return pd.DataFrame()  # Return empty DataFrame

    try:
        # Mock yfinance to always fail
        with patch('yfinance.Ticker') as mock_ticker:
            mock_ticker.return_value.history.return_value = mock_yfinance_failure()

            chart_buffer = chart_service.create_event_chart(
                currency='EUR',
                event_time=test_time,
                event_name='Test Fallback Event',
                impact_level='medium',
                window_hours=1
            )

            if chart_buffer is not None:
                print("✅ Successfully generated fallback chart")
                print(f"   Chart size: {len(chart_buffer.getvalue())} bytes")

                # Save chart for inspection
                with open("fallback_single_chart.png", 'wb') as f:
                    f.write(chart_buffer.getvalue())
                print("   Chart saved as: fallback_single_chart.png")
            else:
                print("❌ Failed to generate fallback chart")

    except Exception as e:
        print(f"❌ Error in fallback test: {e}")

    print()

    # Test 2: Mock Yahoo Finance failure for multi-currency
    print("Test 2: Multi-currency chart with simulated Yahoo Finance failure")
    print("-" * 60)

    try:
        # Mock yfinance to always fail
        with patch('yfinance.Ticker') as mock_ticker:
            mock_ticker.return_value.history.return_value = mock_yfinance_failure()

            chart_buffer = chart_service.create_multi_currency_chart(
                primary_currency='EUR',
                secondary_currency='USD',
                event_time=test_time,
                event_name='Test Multi-Currency Fallback Event',
                impact_level='medium',
                window_hours=1
            )

            if chart_buffer is not None:
                print("✅ Successfully generated fallback multi-currency chart")
                print(f"   Chart size: {len(chart_buffer.getvalue())} bytes")

                # Save chart for inspection
                with open("fallback_multi_chart.png", 'wb') as f:
                    f.write(chart_buffer.getvalue())
                print("   Chart saved as: fallback_multi_chart.png")
            else:
                print("❌ Failed to generate fallback multi-currency chart")

    except Exception as e:
        print(f"❌ Error in multi-currency fallback test: {e}")

    print()

    # Test 3: Normal operation (no mocking)
    print("Test 3: Normal operation (real Yahoo Finance)")
    print("-" * 60)

    try:
        chart_buffer = chart_service.create_event_chart(
            currency='EUR',
            event_time=test_time,
            event_name='Test Normal Event',
            impact_level='medium',
            window_hours=1
        )

        if chart_buffer is not None:
            print("✅ Successfully generated normal chart")
            print(f"   Chart size: {len(chart_buffer.getvalue())} bytes")
        else:
            print("❌ Failed to generate normal chart")

    except Exception as e:
        print(f"❌ Error in normal test: {e}")

    print()
    print("Fallback test completed!")

if __name__ == "__main__":
    test_fallback_chart()
