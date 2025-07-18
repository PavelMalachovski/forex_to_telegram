#!/usr/bin/env python3
"""
Quick test for the overhauled ForexFactory scraper
"""
import asyncio
import logging
import os
import sys
from datetime import datetime, timedelta

# Add the parent directory to the path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from bot.scraper import ForexNewsScraper, ChatGPTAnalyzer
from bot.config import Config

# Set up logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Set browser path
os.environ['PLAYWRIGHT_BROWSERS_PATH'] = '/home/ubuntu/.cache/ms-playwright'

async def quick_test():
    """Quick test of the scraper"""
    print("🚀 Quick ForexFactory Scraper Test")
    print("=" * 50)
    
    try:
        # Initialize components
        config = Config()
        analyzer = ChatGPTAnalyzer(config.openai_api_key)
        scraper = ForexNewsScraper(config, analyzer)
        
        # Test with yesterday's date (more likely to have data)
        yesterday = datetime.now() - timedelta(days=1)
        
        print(f"📅 Testing with date: {yesterday.strftime('%Y-%m-%d')}")
        print("⏳ This may take a few minutes due to Cloudflare protection...")
        
        # Test scraping with timeout
        try:
            news_items = await asyncio.wait_for(
                scraper.scrape_news(yesterday, 'all', debug=True),
                timeout=300  # 5 minute timeout
            )
            
            print(f"\n✅ SUCCESS: Found {len(news_items)} news items!")
            
            if news_items:
                print(f"\n📊 Sample items:")
                for i, item in enumerate(news_items[:2]):  # Show first 2 items
                    print(f"\n  📰 Item {i+1}:")
                    print(f"    ⏰ Time: {item['time']}")
                    print(f"    💱 Currency: {item['currency']}")
                    print(f"    📈 Event: {item['event']}")
                    print(f"    📊 Actual: {item['actual']}")
                    print(f"    🎯 Forecast: {item['forecast']}")
                    print(f"    📉 Previous: {item['previous']}")
            
            return True
            
        except asyncio.TimeoutError:
            print("❌ Test timed out after 5 minutes")
            return False
            
    except Exception as e:
        print(f"❌ Test failed: {e}")
        logger.exception("Test failed")
        return False

async def main():
    success = await quick_test()
    
    print(f"\n🏁 RESULT")
    print("=" * 50)
    
    if success:
        print("🎉 Scraper is working!")
    else:
        print("⚠️ Scraper needs more work")
        print("💡 The scraper may be blocked by Cloudflare")
        print("🔄 Try running the test again later")

if __name__ == "__main__":
    asyncio.run(main())
