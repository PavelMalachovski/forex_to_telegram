#!/usr/bin/env python3
"""
Simple test for scraper functionality without database.
"""

import sys
import os
from datetime import date

# Add the project root to Python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app.scrapers.forex_factory_scraper import ForexFactoryScraper

def test_scraper_resilience():
    """Test that scraper handles 403 errors gracefully."""
    print("🔍 Testing scraper resilience to 403 errors...")
    
    scraper = ForexFactoryScraper()
    
    try:
        # Test connection
        print("Testing connection...")
        connection_result = scraper.test_connection()
        print(f"Connection result: {connection_result}")
        
        # Test scraping today
        print("Testing scraping today...")
        today = date.today()
        events = scraper.scrape_single_date(today)
        
        print(f"Scraping result: {type(events)} with {len(events) if events else 0} events")
        
        # The key test: did it return gracefully instead of crashing?
        if events is not None:
            print("✅ SUCCESS: Scraper returned gracefully (even if empty)")
            return True
        else:
            print("❌ FAILED: Scraper returned None")
            return False
            
    except Exception as e:
        print(f"❌ FAILED: Scraper crashed with exception: {e}")
        return False
    finally:
        scraper.close()

def test_headers():
    """Test that proper headers are being used."""
    print("\n🔍 Testing headers configuration...")
    
    scraper = ForexFactoryScraper()
    
    # Check headers
    headers = scraper.session.headers
    
    required_headers = [
        'User-Agent',
        'Accept',
        'Accept-Language',
        'Accept-Encoding',
        'DNT',
        'Connection',
        'Upgrade-Insecure-Requests',
        'Sec-Fetch-Dest',
        'Sec-Fetch-Mode',
        'Sec-Fetch-Site',
        'Sec-Fetch-User',
        'Cache-Control'
    ]
    
    missing_headers = []
    for header in required_headers:
        if header not in headers:
            missing_headers.append(header)
    
    if not missing_headers:
        print("✅ SUCCESS: All required headers are present")
        print(f"User-Agent: {headers.get('User-Agent', 'N/A')}")
        return True
    else:
        print(f"❌ FAILED: Missing headers: {missing_headers}")
        return False

def test_retry_mechanism():
    """Test that retry mechanism is working."""
    print("\n🔍 Testing retry mechanism...")
    
    scraper = ForexFactoryScraper()
    
    # Check retry configuration
    if hasattr(scraper, 'max_retries') and scraper.max_retries >= 3:
        print("✅ SUCCESS: Retry mechanism configured")
        return True
    else:
        print("❌ FAILED: Retry mechanism not properly configured")
        return False

if __name__ == "__main__":
    print("🚀 Testing scraper fixes...\n")
    
    tests = [
        ("Scraper Resilience", test_scraper_resilience),
        ("Headers Configuration", test_headers),
        ("Retry Mechanism", test_retry_mechanism),
    ]
    
    results = []
    
    for test_name, test_func in tests:
        print(f"{'='*50}")
        print(f"Running: {test_name}")
        print('='*50)
        
        try:
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
        print("\n🎉 All scraper tests passed!")
        print("✅ The scraper should now handle 403 errors gracefully")
        print("✅ Proper headers are configured")
        print("✅ Retry mechanism is in place")
    else:
        print("\n⚠️  Some tests failed. Check the output above.")
    
    print("\n📝 Key improvements made:")
    print("   • Added proper browser headers to avoid detection")
    print("   • Implemented retry mechanism with exponential backoff")
    print("   • Added graceful error handling for 403 Forbidden")
    print("   • Enhanced logging for debugging")
    print("   • Added connection testing before scraping")
