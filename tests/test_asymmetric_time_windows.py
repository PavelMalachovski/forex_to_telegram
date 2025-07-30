#!/usr/bin/env python3
"""
Test script to verify asymmetric time windows for cross-rate charts.
"""

import sys
import os
import logging
from datetime import datetime, timedelta

# Add the bot directory to the path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from bot.chart_service import ChartService
from bot.visualize_handler import VisualizeHandler
from bot.database_service import ForexNewsService
from bot.config import Config

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(name)s: %(message)s'
)

def test_asymmetric_time_windows():
    """Test asymmetric time windows for cross-rate charts."""

    print("Testing asymmetric time windows for cross-rate charts...")
    print("-" * 60)

    # Create chart service
    chart_service = ChartService()

    # Test event time
    event_time = datetime(2025, 8, 1, 14, 30)  # 2:30 PM

    # Test cases with different asymmetric time windows
    test_cases = [
        # (name, before_hours, after_hours)
        ("30m before → 1h after", 0.5, 1),
        ("30m before → 3h after", 0.5, 3),
        ("1h before → 30m after", 1, 0.5),
        ("2h before → 1h after", 2, 1),
        ("3h before → 1h after", 3, 1),
    ]

    for i, (name, before_hours, after_hours) in enumerate(test_cases, 1):
        print(f"Test {i}: {name}")

        try:
            chart_buffer = chart_service.create_multi_currency_chart(
                primary_currency='EUR',
                secondary_currency='USD',
                event_time=event_time,
                before_hours=before_hours,
                after_hours=after_hours,
                event_name='Test CPI Flash Estimate',
                impact_level='high'
            )

            if chart_buffer:
                size_kb = len(chart_buffer.getvalue()) / 1024
                print(f"   ✅ Generated chart: {size_kb:.1f} KB")
                print(f"   📊 Time window: {before_hours}h before → {after_hours}h after")

                # Calculate expected time range
                start_time = event_time - timedelta(hours=before_hours)
                end_time = event_time + timedelta(hours=after_hours)
                print(f"   🕐 Expected range: {start_time.strftime('%H:%M')} → {end_time.strftime('%H:%M')}")
            else:
                print(f"   ❌ Failed to generate chart")

        except Exception as e:
            print(f"   ❌ Error: {e}")

        print()

    # Test symmetric vs asymmetric comparison
    print("Comparison Test: Symmetric vs Asymmetric")
    print("-" * 40)

    # Symmetric: ±2h
    print("Symmetric (±2h):")
    symmetric_chart = chart_service.create_multi_currency_chart(
        primary_currency='GBP',
        secondary_currency='USD',
        event_time=event_time,
        window_hours=2,
        event_name='Test Manufacturing PMI',
        impact_level='medium'
    )

    if symmetric_chart:
        size_kb = len(symmetric_chart.getvalue()) / 1024
        print(f"   ✅ Generated: {size_kb:.1f} KB")
        print(f"   📊 Time window: ±2h")

    print()

    # Asymmetric: 1h before → 3h after
    print("Asymmetric (1h before → 3h after):")
    asymmetric_chart = chart_service.create_multi_currency_chart(
        primary_currency='GBP',
        secondary_currency='USD',
        event_time=event_time,
        before_hours=1,
        after_hours=3,
        event_name='Test Manufacturing PMI',
        impact_level='medium'
    )

    if asymmetric_chart:
        size_kb = len(asymmetric_chart.getvalue()) / 1024
        print(f"   ✅ Generated: {size_kb:.1f} KB")
        print(f"   📊 Time window: 1h before → 3h after")

    print()

    # Test VisualizeHandler cross-rate windows
    print("VisualizeHandler Cross-Rate Windows:")
    print("-" * 40)

    config = Config()
    db_service = ForexNewsService("sqlite:///test_forex_bot.db")
    viz_handler = VisualizeHandler(db_service, config)

    print("Available cross-rate time window options:")
    for i, (window_name, before_hours, after_hours) in enumerate(viz_handler.cross_rate_windows, 1):
        print(f"   {i:2d}. {window_name}")
        print(f"       Before: {before_hours}h, After: {after_hours}h")

    print()
    print("✅ Asymmetric time windows test completed!")

if __name__ == "__main__":
    test_asymmetric_time_windows()
