#!/usr/bin/env python3
"""
Test script for the improved forex scraper
"""
import asyncio
import logging
import os
from datetime import datetime, timedelta
from pytz import timezone
from bot.scraper import ForexNewsScraper, ChatGPTAnalyzer
from bot.config import Config

# Set up logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Set browser path
os.environ['PLAYWRIGHT_BROWSERS_PATH'] = '/home/ubuntu/.cache/ms-playwright'

async def test_scraper_with_date(date_str: str):
    """Test scraper with a specific date"""
    try:
        # Initialize components
        config = Config()
        analyzer = ChatGPTAnalyzer(config.openai_api_key)
        scraper = ForexNewsScraper(config, analyzer)
        
        # Parse date
        target_date = datetime.strptime(date_str, "%Y-%m-%d")
        target_date = timezone(config.timezone).localize(target_date)
        
        print(f'\n=== Testing scraper for date: {date_str} ===')
        
        # Test scraping
        news_items = await scraper.scrape_news(target_date, 'all', debug=True)
        print(f'Successfully scraped {len(news_items)} news items')
        
        if news_items:
            print("\nFirst few items:")
            for i, item in enumerate(news_items[:3]):
                print(f'\nItem {i+1}:')
                print(f'  Time: {item["time"]}')
                print(f'  Currency: {item["currency"]}')
                print(f'  Event: {item["event"]}')
                print(f'  Actual: {item["actual"]}')
                print(f'  Forecast: {item["forecast"]}')
                print(f'  Previous: {item["previous"]}')
        else:
            print("No news items found")
            
        return len(news_items)
        
    except Exception as e:
        print(f'Error during scraping: {e}')
        logger.exception("Scraping failed")
        return 0

async def main():
    """Main test function"""
    print("=== Forex Scraper Test ===")
    
    # Test with today's date
    today = datetime.now().strftime("%Y-%m-%d")
    result1 = await test_scraper_with_date(today)
    
    # Test with yesterday's date (more likely to have data)
    yesterday = (datetime.now() - timedelta(days=1)).strftime("%Y-%m-%d")
    result2 = await test_scraper_with_date(yesterday)
    
    print(f"\n=== Test Results ===")
    print(f"Today ({today}): {result1} items")
    print(f"Yesterday ({yesterday}): {result2} items")
    
    if result1 > 0 or result2 > 0:
        print("✅ Scraper is working!")
    else:
        print("❌ Scraper needs more work")

if __name__ == "__main__":
    asyncio.run(main())
