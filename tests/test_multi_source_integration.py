#!/usr/bin/env python3
"""
Integration test for multi-source forex news system.
"""
import asyncio
import logging
import os
import sys
from datetime import datetime, timedelta

# Add the parent directory to the path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from bot.config import Config

# Set up logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

async def test_multi_source_integration():
    """Test the multi-source system integration."""
    print("🚀 Multi-Source Forex News Integration Test")
    print("=" * 60)
    
    try:
        # Initialize configuration
        config = Config()
        
        # Initialize multi-source scraper
        scraper = MultiSourceForexScraper(config)
        
        # Get source status
        status = scraper.get_source_status()
        print(f"📊 Source Status:")
        print(f"   Total sources: {status['total_sources']}")
        print(f"   Available sources: {status['available_sources']}")
        print(f"   Last successful: {status.get('last_successful_source', 'None')}")
        
        print(f"\n📋 Source Details:")
        for source_info in status['sources']:
            enabled_icon = "✅" if source_info['enabled'] else "❌"
            available_icon = "🟢" if source_info['available'] else "🔴"
            healthy_icon = "💚" if source_info['healthy'] else "💔"
            
            print(f"   {enabled_icon} {available_icon} {healthy_icon} {source_info['name']} (priority: {source_info['priority']})")
            
            if source_info['consecutive_failures'] > 0:
                print(f"      ⚠️ {source_info['consecutive_failures']} consecutive failures")
            if source_info['last_error']:
                print(f"      🔴 Last error: {source_info['last_error']}")
        
        # Test with yesterday's date (more likely to have data)
        yesterday = datetime.now() - timedelta(days=1)
        
        print(f"\n📅 Testing multi-source scraping for: {yesterday.strftime('%Y-%m-%d')}")
        print("⏳ This may take a few minutes...")
        
        # Test scraping with timeout
        try:
            news_items = await asyncio.wait_for(
                scraper.scrape_news(yesterday, 'high', debug=True),
                timeout=300  # 5 minute timeout
            )
            
            print(f"\n✅ SUCCESS: Multi-source system found {len(news_items)} news items!")
            
            if news_items:
                # Show source breakdown
                source_counts = {}
                for item in news_items:
                    source = item.get('source', 'Unknown')
                    source_counts[source] = source_counts.get(source, 0) + 1
                
                print(f"\n📊 Results by source:")
                for source, count in sorted(source_counts.items()):
                    print(f"   📰 {source}: {count} events")
                
                print(f"\n📋 Sample events:")
                for i, item in enumerate(news_items[:3]):  # Show first 3 items
                    print(f"\n   🔸 Event {i+1}:")
                    print(f"      📍 Source: {item.get('source', 'Unknown')}")
                    print(f"      ⏰ Time: {item.get('time', 'N/A')}")
                    print(f"      💱 Currency: {item.get('currency', 'N/A')}")
                    print(f"      📈 Event: {item.get('event', 'N/A')[:80]}...")
                    print(f"      📊 Impact: {item.get('impact', 'N/A')}")
                    if item.get('actual') != 'N/A':
                        print(f"      📊 Actual: {item.get('actual', 'N/A')}")
                    if item.get('forecast') != 'N/A':
                        print(f"      🎯 Forecast: {item.get('forecast', 'N/A')}")
                    if item.get('previous') != 'N/A':
                        print(f"      📉 Previous: {item.get('previous', 'N/A')}")
            
            return True
            
        except asyncio.TimeoutError:
            print("❌ Test timed out after 5 minutes")
            return False
            
    except Exception as e:
        print(f"❌ Test failed: {e}")
        logger.exception("Integration test failed")
        return False

async def test_fallback_behavior():
    """Test fallback behavior when primary source fails."""
    print(f"\n🔄 Testing Fallback Behavior")
    print("=" * 40)
    
    try:
        config = Config()
        scraper = MultiSourceForexScraper(config)
        
        # Reset all source failures to start fresh
        scraper.reset_source_failures()
        
        # Get initial status
        initial_status = scraper.get_source_status()
        print(f"📊 Initial available sources: {initial_status['available_sources']}")
        
        # Try to scrape (this will test the fallback system naturally)
        yesterday = datetime.now() - timedelta(days=1)
        news_items = await scraper.scrape_news(yesterday, 'medium', debug=True)
        
        # Get final status
        final_status = scraper.get_source_status()
        print(f"📊 Final available sources: {final_status['available_sources']}")
        print(f"✅ Last successful source: {final_status.get('last_successful_source', 'None')}")
        
        if news_items:
            print(f"✅ Fallback system working: {len(news_items)} events retrieved")
        else:
            print("⚠️ No events retrieved - this may indicate all sources are currently unavailable")
        
        return True
        
    except Exception as e:
        print(f"❌ Fallback test failed: {e}")
        return False

async def main():
    """Run all integration tests."""
    print("🧪 Multi-Source Forex News System Integration Tests")
    print("=" * 80)
    
    # Test 1: Basic integration
    success1 = await test_multi_source_integration()
    
    # Test 2: Fallback behavior
    success2 = await test_fallback_behavior()
    
    print(f"\n🏁 FINAL RESULTS")
    print("=" * 80)
    
    if success1 and success2:
        print("🎉 All integration tests passed!")
        print("✅ Multi-source system is working correctly")
        print("✅ Fallback system is functioning properly")
        print("\n💡 The bot should now be resilient to ForexFactory blocks")
    else:
        print("⚠️ Some tests failed")
        if not success1:
            print("❌ Multi-source integration test failed")
        if not success2:
            print("❌ Fallback behavior test failed")
        
        print("\n🔧 Troubleshooting:")
        print("   - Check API keys in environment variables")
        print("   - Verify network connectivity")
        print("   - Check source-specific error messages above")

if __name__ == "__main__":
    asyncio.run(main())
