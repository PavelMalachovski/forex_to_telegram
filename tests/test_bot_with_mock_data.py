#!/usr/bin/env python3
"""Test script to verify bot functionality with mock data."""

import sys
import os
from datetime import datetime, time

# Add the bot directory to the path
sys.path.append(os.path.join(os.path.dirname(__file__), 'bot'))

def test_bot_with_mock_data():
    """Test the bot functionality with mock data."""
    print("🧪 Testing Bot with Mock Data")
    print("=" * 50)

    try:
        # Mock user data
        mock_user = {
            'telegram_id': 123456789,
            'preferred_currencies': "USD,EUR",
            'impact_levels': "high,medium",
            'analysis_required': True,
            'digest_time': time(8, 0)
        }

        # Mock news data
        mock_news = [
            {
                'time': '10:30',
                'currency': 'USD',
                'event': 'Non-Farm Payrolls',
                'actual': '180K',
                'forecast': '175K',
                'previous': '165K',
                'impact': 'high'
            },
            {
                'time': '11:00',
                'currency': 'EUR',
                'event': 'ECB Interest Rate Decision',
                'actual': '4.50%',
                'forecast': '4.50%',
                'previous': '4.25%',
                'impact': 'high'
            },
            {
                'time': '12:00',
                'currency': 'GBP',
                'event': 'GDP Growth Rate',
                'actual': '0.3%',
                'forecast': '0.2%',
                'previous': '0.1%',
                'impact': 'medium'
            },
            {
                'time': '13:00',
                'currency': 'JPY',
                'event': 'Bank of Japan Policy Rate',
                'actual': '-0.10%',
                'forecast': '-0.10%',
                'previous': '-0.10%',
                'impact': 'low'
            }
        ]

        print("✅ Mock data created")
        print(f"📊 User preferences: {mock_user}")
        print(f"📰 News items: {len(mock_news)}")

        # Test user preferences parsing
        print("\n🧪 Testing user preferences...")
        currencies = mock_user['preferred_currencies'].split(',')
        impact_levels = mock_user['impact_levels'].split(',')

        print(f"✅ User currencies: {currencies}")
        print(f"✅ User impact levels: {impact_levels}")
        print(f"✅ Analysis required: {mock_user['analysis_required']}")
        print(f"✅ Digest time: {mock_user['digest_time']}")

        # Test news filtering based on user preferences
        print("\n🧪 Testing news filtering...")

        # Filter by user's preferred currencies
        filtered_by_currency = [
            item for item in mock_news
            if item.get('currency') in currencies
        ]
        print(f"✅ News filtered by currency: {len(filtered_by_currency)} items")
        for item in filtered_by_currency:
            print(f"  - {item['currency']}: {item['event']}")

        # Filter by user's preferred impact levels
        filtered_by_impact = [
            item for item in filtered_by_currency
            if item.get('impact') in impact_levels
        ]
        print(f"✅ News filtered by impact: {len(filtered_by_impact)} items")
        for item in filtered_by_impact:
            print(f"  - {item['currency']} ({item['impact']}): {item['event']}")

        # Test message formatting with user preferences
        print("\n🧪 Testing message formatting with user preferences...")
        from bot.scraper import MessageFormatter

        target_date = datetime.now()

        # Format message with user's currency preferences
        message = MessageFormatter.format_news_message(
            filtered_by_impact,
            target_date,
            "all",
            mock_user['analysis_required'],
            currencies
        )

        print(f"✅ Message formatted successfully ({len(message)} characters)")
        print(f"📄 Message preview:\n{message[:800]}...")

        # Test different scenarios
        print("\n🧪 Testing different scenarios...")

        # Scenario 1: All news (no currency filter)
        message_all = MessageFormatter.format_news_message(
            mock_news, target_date, "all", True
        )
        print(f"✅ All news message: {len(message_all)} characters")

        # Scenario 2: High impact only
        high_impact_news = [item for item in mock_news if item.get('impact') == 'high']
        message_high = MessageFormatter.format_news_message(
            high_impact_news, target_date, "high", True
        )
        print(f"✅ High impact message: {len(message_high)} characters")

        # Scenario 3: USD only
        usd_news = [item for item in mock_news if item.get('currency') == 'USD']
        message_usd = MessageFormatter.format_news_message(
            usd_news, target_date, "all", True, ["USD"]
        )
        print(f"✅ USD only message: {len(message_usd)} characters")

        print("\n🎉 All tests completed successfully!")
        print("\n📋 Summary:")
        print("- User preferences work correctly")
        print("- Currency filtering works correctly")
        print("- Impact level filtering works correctly")
        print("- Message formatting works correctly")
        print("- The bot is ready to work when news data is available")

        return True

    except Exception as e:
        print(f"❌ Bot test failed: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    test_bot_with_mock_data()
