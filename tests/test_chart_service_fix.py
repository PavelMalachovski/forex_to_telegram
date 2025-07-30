#!/usr/bin/env python3
"""
Test script to verify the improved chart service handles Yahoo Finance API issues.
"""

import sys
import os
import logging
from datetime import datetime, timedelta
import pytz

# Add the bot directory to the path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from bot.chart_service import ChartService

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(name)s: %(message)s'
)

def test_chart_service():
    """Test the improved chart service with various scenarios."""

    # Initialize the chart service
    chart_service = ChartService()

    # Test parameters
    test_time = datetime.now(pytz.UTC) - timedelta(hours=2)  # 2 hours ago
    start_time = test_time - timedelta(hours=1)
    end_time = test_time + timedelta(hours=1)

    print("Testing improved chart service...")
    print(f"Test time range: {start_time} to {end_time}")
    print()

    # Test symbols that commonly fail
    test_symbols = ['EURUSD=X', 'GBPUSD=X', 'USDJPY=X']

    for symbol in test_symbols:
        print(f"Testing symbol: {symbol}")
        print("-" * 50)

        try:
            # Try to fetch data
            data = chart_service.fetch_price_data(symbol, start_time, end_time)

            if data is not None and not data.empty:
                print(f"✅ Successfully fetched data for {symbol}")
                print(f"   Data points: {len(data)}")
                print(f"   Time range: {data.index[0]} to {data.index[-1]}")
                print(f"   Price range: {data['Close'].min():.4f} to {data['Close'].max():.4f}")
            else:
                print(f"❌ No data available for {symbol}")

        except Exception as e:
            print(f"❌ Error fetching data for {symbol}: {e}")

        print()

    # Test chart generation
    print("Testing chart generation...")
    print("-" * 50)

    try:
        # Try to create a chart
        chart_buffer = chart_service.create_event_chart(
            currency='EUR',
            event_time=test_time,
            event_name='Test Event',
            impact_level='medium',
            window_hours=1
        )

        if chart_buffer is not None:
            print("✅ Successfully generated chart")
            print(f"   Chart size: {len(chart_buffer.getvalue())} bytes")
        else:
            print("❌ Failed to generate chart")

    except Exception as e:
        print(f"❌ Error generating chart: {e}")

    print()
    print("Test completed!")

if __name__ == "__main__":
    test_chart_service()
