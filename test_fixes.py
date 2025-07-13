#!/usr/bin/env python3
"""
Test script for checking the fixes to calendar and scraping issues.
"""

import sys
import os
import asyncio
from datetime import date, datetime, timedelta

# Add the project root to Python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app.scrapers.forex_factory_scraper import ForexFactoryScraper
from app.services.auto_scraper_service import AutoScraperService
from app.database.connection import get_db_session_factory
from app.config import config
from loguru import logger

def test_scraper_connection():
    """Test the scraper connection with new headers."""
    print("🔍 Testing ForexFactory scraper connection...")
    
    try:
        scraper = ForexFactoryScraper()
        
        # Test connection
        connection_ok = scraper.test_connection()
        
        if connection_ok:
            print("✅ Connection test passed!")
            return True
        else:
            print("❌ Connection test failed!")
            return False
            
    except Exception as e:
        print(f"❌ Connection test error: {e}")
        return False
    finally:
        try:
            scraper.close()
        except:
            pass

def test_single_date_scraping():
    """Test scraping a single date."""
    print("\n🔍 Testing single date scraping...")
    
    try:
        scraper = ForexFactoryScraper()
        
        # Test scraping today's data
        today = date.today()
        print(f"Scraping data for {today}...")
        
        events = scraper.scrape_single_date(today)
        
        if events is not None:
            print(f"✅ Scraping successful! Found {len(events)} events")
            
            # Show first few events
            for i, event in enumerate(events[:3]):
                print(f"  Event {i+1}: {event.get('event_name', 'Unknown')} - {event.get('currency', 'N/A')} - {event.get('impact', 'N/A')}")
            
            return True
        else:
            print("❌ Scraping returned None (likely blocked)")
            return False
            
    except Exception as e:
        print(f"❌ Scraping error: {e}")
        return False
    finally:
        try:
            scraper.close()
        except:
            pass

async def test_auto_scraper_service():
    """Test the auto scraper service."""
    print("\n🔍 Testing auto scraper service...")
    
    db = None
    try:
        SessionLocal = get_db_session_factory(config.DATABASE_URL)
        db = SessionLocal()
        auto_scraper = AutoScraperService(db)
        
        # Test with tomorrow's date (likely no data exists)
        tomorrow = date.today() + timedelta(days=1)
        print(f"Testing auto-scraping for {tomorrow}...")
        
        result = await auto_scraper.scrape_date_if_missing(tomorrow)
        
        print(f"✅ Auto-scraper result: {result['status']}")
        print(f"   Message: {result['message']}")
        print(f"   Events count: {result['events_count']}")
        print(f"   Was scraped: {result['scraped']}")
        
        return result['status'] not in ['error', 'connection_error', 'scraping_error']
        
    except Exception as e:
        print(f"❌ Auto-scraper error: {e}")
        return False
    finally:
        if db:
            db.close()

def test_error_handling():
    """Test error handling with invalid dates."""
    print("\n🔍 Testing error handling...")
    
    try:
        scraper = ForexFactoryScraper()
        
        # Test with a very old date (should handle gracefully)
        old_date = date(2020, 1, 1)
        print(f"Testing with old date: {old_date}")
        
        events = scraper.scrape_single_date(old_date)
        
        if events is not None:
            print(f"✅ Error handling test passed! Found {len(events)} events")
            return True
        else:
            print("✅ Error handling test passed! Gracefully handled no data")
            return True
            
    except Exception as e:
        print(f"❌ Error handling test failed: {e}")
        return False
    finally:
        try:
            scraper.close()
        except:
            pass

async def main():
    """Run all tests."""
    print("🚀 Starting forex bot fixes test suite...\n")
    
    tests = [
        ("Connection Test", test_scraper_connection),
        ("Single Date Scraping", test_single_date_scraping),
        ("Auto Scraper Service", test_auto_scraper_service),
        ("Error Handling", test_error_handling),
    ]
    
    results = []
    
    for test_name, test_func in tests:
        print(f"\n{'='*50}")
        print(f"Running: {test_name}")
        print('='*50)
        
        try:
            if asyncio.iscoroutinefunction(test_func):
                result = await test_func()
            else:
                result = test_func()
            
            results.append((test_name, result))
            
        except Exception as e:
            print(f"❌ Test {test_name} crashed: {e}")
            results.append((test_name, False))
    
    # Summary
    print(f"\n{'='*50}")
    print("TEST SUMMARY")
    print('='*50)
    
    passed = 0
    total = len(results)
    
    for test_name, result in results:
        status = "✅ PASSED" if result else "❌ FAILED"
        print(f"{test_name}: {status}")
        if result:
            passed += 1
    
    print(f"\nOverall: {passed}/{total} tests passed")
    
    if passed == total:
        print("🎉 All tests passed! The fixes should work correctly.")
    else:
        print("⚠️  Some tests failed. Check the output above for details.")
    
    return passed == total

if __name__ == "__main__":
    # Configure logging
    logger.remove()
    logger.add(sys.stdout, level="INFO", format="{time:HH:mm:ss} | {level} | {message}")
    
    # Run tests
    success = asyncio.run(main())
    sys.exit(0 if success else 1)
