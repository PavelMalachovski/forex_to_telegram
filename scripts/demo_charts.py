#!/usr/bin/env python3
"""Demo script to showcase chart generation functionality."""

import sys
import os
import logging
from datetime import datetime, timedelta

# Add the parent directory to the path so we can import the bot modules
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from bot.chart_service import ChartService

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def demo_chart_generation():
    """Demonstrate chart generation with historical data."""
    print("📊 Chart Generation Demo")
    print("=" * 50)

    chart_service = ChartService()

    # Use a past date to ensure we have data
    # Let's use a recent date that should have data
    past_date = datetime.now() - timedelta(days=7)  # 7 days ago
    event_time = past_date.replace(hour=14, minute=30, second=0, microsecond=0)  # 2:30 PM

    print(f"📅 Using event time: {event_time}")
    print(f"🕐 Time window: 2 hours before and after")

    # Test different currencies
    test_cases = [
        {
            'currency': 'USD',
            'event_name': 'Non-Farm Payrolls',
            'impact_level': 'high'
        },
        {
            'currency': 'EUR',
            'event_name': 'ECB Interest Rate Decision',
            'impact_level': 'high'
        },
        {
            'currency': 'GBP',
            'event_name': 'BOE Meeting Minutes',
            'impact_level': 'medium'
        }
    ]

    for i, test_case in enumerate(test_cases, 1):
        print(f"\n🔍 Test Case {i}: {test_case['currency']} - {test_case['event_name']}")
        print("-" * 40)

        currency = test_case['currency']
        event_name = test_case['event_name']
        impact_level = test_case['impact_level']

        # Get the currency pair for this event
        symbol = chart_service.get_currency_pair_for_event(currency)
        print(f"📈 Currency pair: {symbol}")

        # Try to generate single chart
        print("🔄 Generating single pair chart...")
        single_chart = chart_service.create_event_chart(
            currency=currency,
            event_time=event_time,
            event_name=event_name,
            impact_level=impact_level,
            window_hours=2
        )

        if single_chart:
            chart_size = len(single_chart.getvalue())
            print(f"✅ Single chart generated successfully!")
            print(f"   📏 Chart size: {chart_size:,} bytes")
            print(f"   🎨 Chart type: Single pair ({symbol})")

            # Save chart to file for inspection
            filename = f"demo_chart_{currency.lower()}_single.png"
            with open(filename, 'wb') as f:
                f.write(single_chart.getvalue())
            print(f"   💾 Saved as: {filename}")
        else:
            print("❌ Single chart generation failed (no data available)")

        # Try to generate multi-pair chart
        print("🔄 Generating multi-pair chart...")
        multi_chart = chart_service.create_multi_pair_chart(
            currency=currency,
            event_time=event_time,
            event_name=event_name,
            impact_level=impact_level,
            window_hours=2
        )

        if multi_chart:
            chart_size = len(multi_chart.getvalue())
            print(f"✅ Multi-pair chart generated successfully!")
            print(f"   📏 Chart size: {chart_size:,} bytes")
            print(f"   🎨 Chart type: Multi-pair comparison")

            # Save chart to file for inspection
            filename = f"demo_chart_{currency.lower()}_multi.png"
            with open(filename, 'wb') as f:
                f.write(multi_chart.getvalue())
            print(f"   💾 Saved as: {filename}")
        else:
            print("❌ Multi-pair chart generation failed (no data available)")

    print("\n" + "=" * 50)
    print("🎉 Chart generation demo completed!")
    print("\n📁 Generated files:")
    import glob
    for filename in glob.glob("demo_chart_*.png"):
        print(f"   📄 {filename}")


def demo_currency_mapping():
    """Demonstrate currency pair mapping."""
    print("\n🗺️ Currency Pair Mapping Demo")
    print("=" * 50)

    chart_service = ChartService()

    # Test all supported currencies
    currencies = [
        'USD', 'EUR', 'GBP', 'JPY', 'AUD', 'CAD', 'CHF', 'NZD',
        'CNY', 'INR', 'BRL', 'RUB', 'KRW', 'MXN', 'SGD', 'HKD'
    ]

    print("Currency → Yahoo Finance Symbol:")
    for currency in currencies:
        symbol = chart_service.get_currency_pair_for_event(currency)
        print(f"  {currency:3} → {symbol}")

    print(f"\n✅ Mapped {len(currencies)} currencies to their respective pairs")


def demo_cache_functionality():
    """Demonstrate cache functionality."""
    print("\n💾 Cache Functionality Demo")
    print("=" * 50)

    chart_service = ChartService()

    # Show cache stats
    print("📊 Cache Statistics:")
    print(f"   📦 Cached entries: {len(chart_service._price_cache)}")
    print(f"   ⏱️ Cache TTL: {chart_service._cache_ttl}")

    # Test cache cleanup
    print("\n🧹 Testing cache cleanup...")
    chart_service.cleanup_cache()
    print("✅ Cache cleanup completed")


if __name__ == "__main__":
    print("🚀 Starting Chart Service Demo")
    print("=" * 50)

    try:
        demo_currency_mapping()
        demo_cache_functionality()
        demo_chart_generation()

        print("\n🎯 Demo completed successfully!")
        print("\n💡 Tips:")
        print("   • Charts are generated for past events to ensure data availability")
        print("   • In production, charts are generated for real-time news events")
        print("   • Users can enable/disable charts in their settings")
        print("   • Chart generation is cached to reduce API calls")

    except Exception as e:
        print(f"\n❌ Demo failed: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
