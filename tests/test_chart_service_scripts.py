#!/usr/bin/env python3
"""
Test script for the improved chart service with better error handling.
"""

import sys
import os
import logging
from datetime import datetime, timedelta
import pytz

# Add the parent directory to the path to import bot modules
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from bot.chart_service import ChartService
from bot.config import Config

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(name)s: %(message)s'
)

def test_chart_service():
    """Test the chart service with various scenarios."""

    # Initialize chart service
    chart_service = ChartService()

    # Test parameters
    test_currency = 'GBP'
    test_event_time = datetime.now(pytz.UTC) - timedelta(days=1)  # Yesterday
    test_event_name = "Test Economic Event"

    print(f"Testing chart service for {test_currency} event at {test_event_time}")
    print("=" * 60)

    # Test 1: Basic data fetching
    print("\n1. Testing basic data fetching...")
    symbols = chart_service.get_currency_pairs_for_currency(test_currency)
    print(f"Currency pairs for {test_currency}: {symbols}")

    start_time = test_event_time - timedelta(hours=2)
    end_time = test_event_time + timedelta(hours=2)

    for symbol in symbols:
        print(f"\nTrying to fetch data for {symbol}...")
        data = chart_service.fetch_price_data(symbol, start_time, end_time)

        if data is not None and not data.empty:
            print(f"✅ Successfully fetched {len(data)} data points for {symbol}")
            print(f"   Data range: {data.index[0]} to {data.index[-1]}")
            print(f"   Price range: {data['Close'].min():.4f} to {data['Close'].max():.4f}")
        else:
            print(f"❌ Failed to fetch data for {symbol}")

    # Test 2: Chart generation
    print("\n\n2. Testing chart generation...")
    chart_buffer = chart_service.create_event_chart(
        currency=test_currency,
        event_time=test_event_time,
        event_name=test_event_name,
        impact_level='medium',
        window_hours=2
    )

    if chart_buffer is not None:
        print("✅ Successfully generated chart")
        print(f"   Chart size: {len(chart_buffer.getvalue())} bytes")
    else:
        print("❌ Failed to generate chart")

    # Test 3: Multi-pair chart
    print("\n\n3. Testing multi-pair chart generation...")
    multi_chart_buffer = chart_service.create_multi_pair_chart(
        currency=test_currency,
        event_time=test_event_time,
        event_name=test_event_name,
        impact_level='high',
        window_hours=2
    )

    if multi_chart_buffer is not None:
        print("✅ Successfully generated multi-pair chart")
        print(f"   Chart size: {len(multi_chart_buffer.getvalue())} bytes")
    else:
        print("❌ Failed to generate multi-pair chart")

    # Test 4: Cache functionality
    print("\n\n4. Testing cache functionality...")
    chart_service.cleanup_cache()
    print("✅ Cache cleanup completed")

    print("\n" + "=" * 60)
    print("Chart service test completed!")

if __name__ == "__main__":
    test_chart_service()
