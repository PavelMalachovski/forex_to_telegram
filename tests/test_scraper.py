#!/usr/bin/env python3
"""
Enhanced test script for the overhauled ForexFactory scraper
"""
import asyncio
import logging
import os
import sys
from datetime import datetime, timedelta
from pytz import timezone

# Add the parent directory to the path so we can import bot modules
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from bot.scraper import ForexNewsScraper, ChatGPTAnalyzer
from bot.config import Config

# Enhanced logging configuration
logging.basicConfig(
    level=logging.INFO, 
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler('/tmp/scraper_test.log')
    ]
)
logger = logging.getLogger(__name__)

# Set browser path for Playwright
os.environ['PLAYWRIGHT_BROWSERS_PATH'] = '/home/ubuntu/.cache/ms-playwright'

async def test_scraper_comprehensive():
    """Comprehensive test of the overhauled scraper"""
    print("🚀 Starting comprehensive ForexFactory scraper test...")
    print("=" * 60)
    
    try:
        # Initialize components
        config = Config()
        analyzer = ChatGPTAnalyzer(config.openai_api_key)
        scraper = ForexNewsScraper(config, analyzer)
        
        # Test dates
        today = datetime.now()
        yesterday = today - timedelta(days=1)
        tomorrow = today + timedelta(days=1)
        
        test_dates = [
            (yesterday, "Yesterday"),
            (today, "Today"), 
            (tomorrow, "Tomorrow")
        ]
        
        results = {}
        
        for test_date, label in test_dates:
            print(f"\n📅 Testing {label} ({test_date.strftime('%Y-%m-%d')})...")
            print("-" * 40)
            
            try:
                # Test with 'all' impact level for maximum coverage
                news_items = await scraper.scrape_news(test_date, 'all', debug=True)
                results[label] = len(news_items)
                
                print(f"✅ {label}: Found {len(news_items)} news items")
                
                if news_items:
                    print(f"\n📊 Sample items from {label}:")
                    for i, item in enumerate(news_items[:3]):  # Show first 3 items
                        print(f"\n  📰 Item {i+1}:")
                        print(f"    ⏰ Time: {item['time']}")
                        print(f"    💱 Currency: {item['currency']}")
                        print(f"    📈 Event: {item['event']}")
                        print(f"    📊 Actual: {item['actual']}")
                        print(f"    🎯 Forecast: {item['forecast']}")
                        print(f"    📉 Previous: {item['previous']}")
                        
                        # Show analysis if available
                        if 'analysis' in item and item['analysis'] != "⚠️ ChatGPT analysis skipped: API key not configured.":
                            print(f"    🤖 Analysis: {item['analysis'][:100]}...")
                else:
                    print(f"⚠️ {label}: No news items found")
                    
            except Exception as e:
                print(f"❌ {label}: Test failed with error: {e}")
                logger.exception(f"Test failed for {label}")
                results[label] = 0
        
        # Test different impact levels with today's data
        print(f"\n🎯 Testing different impact levels for today...")
        print("-" * 40)
        
        impact_levels = ['high', 'medium', 'low', 'all']
        impact_results = {}
        
        for impact_level in impact_levels:
            try:
                news_items = await scraper.scrape_news(today, impact_level, debug=True)
                impact_results[impact_level] = len(news_items)
                print(f"  📊 {impact_level.upper()} impact: {len(news_items)} items")
            except Exception as e:
                print(f"  ❌ {impact_level.upper()} impact: Failed ({e})")
                impact_results[impact_level] = 0
        
        # Summary
        print(f"\n📈 TEST SUMMARY")
        print("=" * 60)
        
        total_items = sum(results.values())
        successful_tests = sum(1 for count in results.values() if count > 0)
        
        print(f"📊 Date-based tests:")
        for label, count in results.items():
            status = "✅" if count > 0 else "❌"
            print(f"  {status} {label}: {count} items")
        
        print(f"\n🎯 Impact level tests:")
        for level, count in impact_results.items():
            status = "✅" if count > 0 else "❌"
            print(f"  {status} {level.upper()}: {count} items")
        
        print(f"\n🏆 OVERALL RESULTS:")
        print(f"  📊 Total items found: {total_items}")
        print(f"  ✅ Successful tests: {successful_tests}/{len(results)}")
        
        if successful_tests > 0:
            print(f"  🎉 Status: SCRAPER IS WORKING! 🎉")
            return True
        else:
            print(f"  ⚠️ Status: SCRAPER NEEDS ATTENTION")
            return False
            
    except Exception as e:
        print(f"❌ Comprehensive test failed: {e}")
        logger.exception("Comprehensive test failed")
        return False

async def test_browser_launch():
    """Test if browser launches correctly in headless mode"""
    print("\n🌐 Testing browser launch...")
    print("-" * 30)
    
    try:
        from bot.scraper import get_browser_page
        
        async with get_browser_page() as page:
            # Test basic navigation
            await page.goto("https://www.google.com", timeout=30000)
            title = await page.title()
            print(f"✅ Browser launched successfully")
            print(f"  📄 Test page title: {title}")
            return True
            
    except Exception as e:
        print(f"❌ Browser launch failed: {e}")
        logger.exception("Browser launch test failed")
        return False

async def main():
    """Main test function"""
    print("🔧 FOREXFACTORY SCRAPER OVERHAUL TEST")
    print("=" * 60)
    print("Testing the completely overhauled scraper with:")
    print("  • Enhanced Cloudflare bypass")
    print("  • Production-ready headless browser")
    print("  • Modern ForexFactory selectors")
    print("  • Improved error handling")
    print("  • Better content parsing")
    print("=" * 60)
    
    # Test browser launch first
    browser_ok = await test_browser_launch()
    
    if not browser_ok:
        print("\n❌ Browser test failed - cannot proceed with scraper tests")
        return
    
    # Run comprehensive scraper tests
    scraper_ok = await test_scraper_comprehensive()
    
    print(f"\n🏁 FINAL RESULT")
    print("=" * 60)
    
    if scraper_ok:
        print("🎉 SUCCESS: ForexFactory scraper overhaul is working!")
        print("✅ The scraper can now:")
        print("  • Launch in headless production mode")
        print("  • Bypass Cloudflare protection")
        print("  • Parse modern ForexFactory structure")
        print("  • Extract forex news events")
        print("  • Handle errors gracefully")
    else:
        print("⚠️ ATTENTION NEEDED: Scraper requires further fixes")
        print("📋 Check the logs for detailed error information")
        print("🔍 Log file: /tmp/scraper_test.log")

if __name__ == "__main__":
    asyncio.run(main())
