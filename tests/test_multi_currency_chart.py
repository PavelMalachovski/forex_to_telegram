#!/usr/bin/env python3
"""
Test script to verify the multi-currency chart functionality.
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

def test_multi_currency_chart():
    """Test the multi-currency chart functionality."""

    # Initialize the chart service
    chart_service = ChartService()

    # Test parameters
    test_time = datetime.now(pytz.UTC) - timedelta(hours=2)  # 2 hours ago

    print("Testing multi-currency chart functionality...")
    print(f"Test time: {test_time}")
    print()

    # Test different currency combinations
    test_combinations = [
        ('EUR', 'USD'),
        ('GBP', 'USD'),
        ('USD', 'JPY'),
        ('EUR', 'GBP'),
    ]

    for primary, secondary in test_combinations:
        print(f"Testing {primary}/{secondary} combination")
        print("-" * 50)

        try:
            # Try to create a multi-currency chart
            chart_buffer = chart_service.create_multi_currency_chart(
                primary_currency=primary,
                secondary_currency=secondary,
                event_time=test_time,
                event_name='Test Multi-Currency Event',
                impact_level='medium',
                window_hours=1
            )

            if chart_buffer is not None:
                print(f"✅ Successfully generated multi-currency chart for {primary}/{secondary}")
                print(f"   Chart size: {len(chart_buffer.getvalue())} bytes")
            else:
                print(f"❌ Failed to generate multi-currency chart for {primary}/{secondary}")

        except Exception as e:
            print(f"❌ Error generating multi-currency chart for {primary}/{secondary}: {e}")

        print()

    # Test single currency chart for comparison
    print("Testing single currency chart for comparison...")
    print("-" * 50)

    try:
        chart_buffer = chart_service.create_event_chart(
            currency='EUR',
            event_time=test_time,
            event_name='Test Single Currency Event',
            impact_level='medium',
            window_hours=1
        )

        if chart_buffer is not None:
            print("✅ Successfully generated single currency chart")
            print(f"   Chart size: {len(chart_buffer.getvalue())} bytes")
        else:
            print("❌ Failed to generate single currency chart")

    except Exception as e:
        print(f"❌ Error generating single currency chart: {e}")

    print()
    print("Test completed!")

if __name__ == "__main__":
    test_multi_currency_chart()
