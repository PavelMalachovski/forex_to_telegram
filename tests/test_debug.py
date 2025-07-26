#!/usr/bin/env python3
"""Debug script to test news fetching functionality."""

import asyncio
import sys
import os
import pytest
from datetime import datetime

# Add the parent directory to the path to find the bot module
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))

from bot.config import Config
from bot.scraper import ChatGPTAnalyzer, ForexNewsScraper
from bot.database_service import ForexNewsService

@pytest.mark.asyncio
async def test_news_fetching():
    """Test the news fetching functionality."""
    print("🧪 Testing News Fetching")
    print("=" * 50)

    try:
        # Initialize components
        config = Config()
        analyzer = ChatGPTAnalyzer(config.chatgpt_api_key)
        scraper = ForexNewsScraper(config, analyzer)

        print("✅ Components initialized")

        # Test database connection
        try:
            db_service = ForexNewsService(config.get_database_url())
            print("✅ Database service initialized")

            # Test if we can get news for today
            today = datetime.now().date()
            print(f"📅 Testing news for date: {today}")

            # Check if news exists in database
            has_news = db_service.has_news_for_date(today, 'all')
            print(f"📊 Has news in database: {has_news}")

            if has_news:
                news_items = db_service.get_news_for_date(today, 'all')
                print(f"📰 Found {len(news_items)} news items in database")
                for i, item in enumerate(news_items[:3]):  # Show first 3 items
                    print(f"  {i+1}. {item.get('currency')} - {item.get('event')[:50]}...")
            else:
                print("📰 No news in database, will need to scrape")

        except Exception as e:
            print(f"❌ Database error: {e}")
            db_service = None

        # Test scraping
        print("\n🔄 Testing news scraping...")
        try:
            target_date = datetime.now()
            news_items = await scraper.scrape_news(target_date, analysis_required=False, debug=True)

            if news_items:
                print(f"✅ Scraped {len(news_items)} news items")
                for i, item in enumerate(news_items[:3]):  # Show first 3 items
                    print(f"  {i+1}. {item.get('currency')} - {item.get('event')[:50]}...")
            else:
                print("❌ No news items scraped")

        except Exception as e:
            print(f"❌ Scraping error: {e}")
            import traceback
            traceback.print_exc()

        # Test message formatting
        print("\n📝 Testing message formatting...")
        try:
            from bot.scraper import MessageFormatter

            test_news = [
                {
                    'time': '10:30',
                    'currency': 'USD',
                    'event': 'Test Event',
                    'actual': '1.5',
                    'forecast': '1.4',
                    'previous': '1.3',
                    'impact': 'high'
                }
            ]

            message = MessageFormatter.format_news_message(
                test_news,
                datetime.now(),
                "high",
                True
            )

            print(f"✅ Message formatted successfully ({len(message)} characters)")
            print(f"📄 Message preview: {message[:200]}...")

        except Exception as e:
            print(f"❌ Message formatting error: {e}")
            import traceback
            traceback.print_exc()

        print("\n🎉 Debug test completed!")

    except Exception as e:
        print(f"❌ Debug test failed: {e}")
        import traceback
        traceback.print_exc()
        pytest.fail(f"Debug test failed: {e}")

if __name__ == "__main__":
    asyncio.run(test_news_fetching())
