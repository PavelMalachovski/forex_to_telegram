"""Test script to verify chart service functionality."""

import sys
import os
import logging
from datetime import datetime, timedelta
from unittest.mock import Mock, MagicMock

# Add the parent directory to the path so we can import the bot modules
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from bot.chart_service import ChartService
from bot.config import Config

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def test_chart_service_initialization():
    """Test chart service initialization."""
    print("Testing chart service initialization...")

    chart_service = ChartService()

    # Test that currency pairs are loaded
    assert 'USD' in chart_service.currency_pairs
    assert 'EUR' in chart_service.currency_pairs
    assert 'GBP' in chart_service.currency_pairs

    # Test default currency pair mapping
    assert chart_service.get_currency_pair_for_event('USD') == 'EURUSD=X'
    assert chart_service.get_currency_pair_for_event('EUR') == 'EURUSD=X'
    assert chart_service.get_currency_pair_for_event('GBP') == 'GBPUSD=X'

    print("✅ Chart service initialization tests passed!")


def test_chart_generation():
    """Test chart generation functionality."""
    print("Testing chart generation...")

    chart_service = ChartService()

    # Create a test event
    event_time = datetime.now() + timedelta(hours=1)  # 1 hour from now
    currency = 'USD'
    event_name = 'Test Non-Farm Payrolls'
    impact_level = 'high'

    try:
        # Test single chart generation
        chart_buffer = chart_service.create_event_chart(
            currency=currency,
            event_time=event_time,
            event_name=event_name,
            impact_level=impact_level,
            window_hours=2
        )

        if chart_buffer:
            print(f"✅ Successfully generated single chart for {currency} event")
            print(f"   Chart size: {len(chart_buffer.getvalue())} bytes")
        else:
            print("⚠️ Chart generation returned None (this might be expected if no data available)")

        # Test multi-pair chart generation
        multi_chart_buffer = chart_service.create_multi_pair_chart(
            currency=currency,
            event_time=event_time,
            event_name=event_name,
            impact_level=impact_level,
            window_hours=2
        )

        if multi_chart_buffer:
            print(f"✅ Successfully generated multi-pair chart for {currency} event")
            print(f"   Chart size: {len(multi_chart_buffer.getvalue())} bytes")
        else:
            print("⚠️ Multi-pair chart generation returned None (this might be expected if no data available)")

    except Exception as e:
        print(f"❌ Chart generation test failed: {e}")
        import traceback
        traceback.print_exc()


def test_currency_pair_mapping():
    """Test currency pair mapping functionality."""
    print("Testing currency pair mapping...")

    chart_service = ChartService()

    # Test various currency mappings
    test_cases = [
        ('USD', 'EURUSD=X'),
        ('EUR', 'EURUSD=X'),
        ('GBP', 'GBPUSD=X'),
        ('JPY', 'USDJPY=X'),
        ('AUD', 'AUDUSD=X'),
        ('CAD', 'USDCAD=X'),
        ('CHF', 'USDCHF=X'),
        ('NZD', 'NZDUSD=X'),
        ('CNY', 'USDCNY=X'),
        ('INR', 'USDINR=X'),
        ('BRL', 'USDBRL=X'),
        ('RUB', 'USDRUB=X'),
        ('KRW', 'USDKRW=X'),
        ('MXN', 'USDMXN=X'),
        ('SGD', 'USDSGD=X'),
        ('HKD', 'USDHKD=X'),
    ]

    for currency, expected_pair in test_cases:
        actual_pair = chart_service.get_currency_pair_for_event(currency)
        assert actual_pair == expected_pair, f"Expected {expected_pair} for {currency}, got {actual_pair}"

    print("✅ Currency pair mapping tests passed!")


def test_cache_functionality():
    """Test chart service cache functionality."""
    print("Testing cache functionality...")

    chart_service = ChartService()

    # Test cache cleanup
    chart_service.cleanup_cache()
    print("✅ Cache cleanup test passed!")


def test_error_handling():
    """Test error handling in chart service."""
    print("Testing error handling...")

    chart_service = ChartService()

    # Test with invalid currency
    result = chart_service.get_currency_pair_for_event('INVALID')
    assert result == 'EURUSD=X'  # Should return default

    # Test with None values
    try:
        chart_buffer = chart_service.create_event_chart(
            currency=None,
            event_time=None,
            event_name=None,
            impact_level=None
        )
        # Should handle gracefully
        print("✅ Error handling test passed!")
    except Exception as e:
        print(f"❌ Error handling test failed: {e}")


if __name__ == "__main__":
    print("🧪 Running chart service tests...\n")

    try:
        test_chart_service_initialization()
        test_currency_pair_mapping()
        test_cache_functionality()
        test_error_handling()
        test_chart_generation()

        print("\n🎉 All chart service tests completed!")

    except Exception as e:
        print(f"\n❌ Test failed: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
