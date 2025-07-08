#!/usr/bin/env python3
"""
System fix script for Forex Bot.
Fixes identified issues and loads current data.
"""

import os
import sys
import logging
from datetime import datetime, timedelta, date
from typing import Dict, Any

# Add app directory to Python path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'app'))

from app.database.connection import SessionLocal
from app.database.models import BotUser, UserNotificationSettings
from app.scrapers.forex_factory_scraper import ForexFactoryScraper
from app.services.news_service import NewsService

# Setup logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class ForexBotFixer:
    """System fixer for Forex Bot."""
    
    def __init__(self):
        self.results = {}
        
    def fix_all_issues(self) -> Dict[str, Any]:
        """Fix all identified issues."""
        print("🔧 Starting Forex Bot System Fixes...")
        print("=" * 60)
        
        # 1. Load current data
        self._load_current_data()
        
        # 2. Test scraper with current date
        self._test_current_scraper()
        
        # 3. Create test user for notifications
        self._create_test_user()
        
        # 4. Generate summary
        self._generate_fix_summary()
        
        return self.results
    
    def _load_current_data(self):
        """Load data for current week."""
        print("\n📥 1. LOADING CURRENT DATA")
        print("-" * 30)
        
        load_results = {
            'dates_loaded': [],
            'total_events_loaded': 0,
            'errors': []
        }
        
        try:
            scraper = ForexFactoryScraper()
            db = SessionLocal()
            news_service = NewsService(db)
            
            # Load data for today + next 7 days
            start_date = date.today()
            end_date = start_date + timedelta(days=7)
            
            print(f"🔄 Loading data from {start_date} to {end_date}")
            
            current_date = start_date
            while current_date <= end_date:
                try:
                    # Check if data already exists
                    existing_events = news_service.get_news_by_date_range(current_date, current_date)
                    
                    if existing_events:
                        print(f"✅ Data already exists for {current_date}: {len(existing_events)} events")
                        load_results['dates_loaded'].append(str(current_date))
                        load_results['total_events_loaded'] += len(existing_events)
                    else:
                        print(f"🔄 Scraping data for {current_date}...")
                        
                        # Scrape data for this date
                        scraped_data = scraper.scrape_single_date(current_date)
                        
                        if scraped_data:
                            # Save to database
                            saved_count = 0
                            for event_data in scraped_data:
                                try:
                                    news_service.create_or_update_event(
                                        event_date=datetime.strptime(event_data['date'], '%Y-%m-%d').date(),
                                        event_time=event_data['time'],
                                        currency_code=event_data['currency'],
                                        event_name=event_data['event_name'],
                                        forecast=event_data.get('forecast'),
                                        previous_value=event_data.get('previous_value'),
                                        actual_value=event_data.get('actual_value'),
                                        impact_level_code=event_data.get('impact_level', 'LOW'),
                                        analysis=event_data.get('analysis'),
                                        source_url=event_data.get('source_url')
                                    )
                                    saved_count += 1
                                except Exception as e:
                                    logger.error(f"Error saving event: {e}")
                                    continue
                            
                            db.commit()
                            print(f"✅ Loaded {saved_count} events for {current_date}")
                            load_results['dates_loaded'].append(str(current_date))
                            load_results['total_events_loaded'] += saved_count
                            
                            # Log scraping session
                            news_service.log_scraping_session(
                                start_date=current_date,
                                end_date=current_date,
                                events_scraped=saved_count,
                                events_updated=0,
                                errors_count=len(scraped_data) - saved_count,
                                duration_seconds=0,
                                status='success'
                            )
                        else:
                            print(f"⚠️  No events found for {current_date}")
                
                except Exception as e:
                    error_msg = f"Error loading data for {current_date}: {e}"
                    print(f"❌ {error_msg}")
                    load_results['errors'].append(error_msg)
                
                current_date += timedelta(days=1)
            
            db.close()
            print(f"\n✅ Data loading completed: {load_results['total_events_loaded']} total events")
            
        except Exception as e:
            error_msg = f"Data loading failed: {e}"
            print(f"❌ {error_msg}")
            load_results['errors'].append(error_msg)
        
        self.results['data_loading'] = load_results
    
    def _test_current_scraper(self):
        """Test scraper with current date."""
        print("\n🕷️  2. TESTING CURRENT SCRAPER")
        print("-" * 30)
        
        scraper_results = {
            'test_successful': False,
            'events_found': 0,
            'test_date': str(date.today()),
            'error': None
        }
        
        try:
            scraper = ForexFactoryScraper()
            today = date.today()
            
            print(f"🔄 Testing scraper for today: {today}")
            
            # Test scraping for today
            test_events = scraper.scrape_single_date(today)
            scraper_results['events_found'] = len(test_events)
            scraper_results['test_successful'] = True
            
            print(f"✅ Scraper test successful: {len(test_events)} events found for today")
            
            # Show sample events
            if test_events:
                print("📋 Sample events:")
                for i, event in enumerate(test_events[:3]):
                    print(f"  {i+1}. {event['time']} - {event['currency']} - {event['event_name']} ({event['impact_level']})")
            
        except Exception as e:
            error_msg = f"Scraper test failed: {e}"
            print(f"❌ {error_msg}")
            scraper_results['error'] = error_msg
        
        self.results['scraper_test'] = scraper_results
    
    def _create_test_user(self):
        """Create a test user for notification testing."""
        print("\n👤 3. CREATING TEST USER")
        print("-" * 30)
        
        user_results = {
            'test_user_created': False,
            'notification_settings_created': False,
            'error': None
        }
        
        try:
            db = SessionLocal()
            
            # Check if test user already exists
            test_user = db.query(BotUser).filter(BotUser.telegram_user_id == 123456789).first()
            
            if not test_user:
                # Create test user
                test_user = BotUser(
                    telegram_user_id=123456789,
                    telegram_username="test_user",
                    first_name="Test",
                    last_name="User",
                    language_code="en",
                    is_active=True,
                    created_at=datetime.now(),
                    last_activity=datetime.now()
                )
                db.add(test_user)
                db.commit()
                user_results['test_user_created'] = True
                print("✅ Test user created")
            else:
                print("✅ Test user already exists")
                user_results['test_user_created'] = True
            
            # Check if notification settings exist
            notification_settings = db.query(UserNotificationSettings).filter(
                UserNotificationSettings.user_id == test_user.id
            ).first()
            
            if not notification_settings:
                # Create notification settings
                notification_settings = UserNotificationSettings(
                    user_id=test_user.id,
                    notifications_enabled=True,
                    notify_15_minutes=True,
                    notify_30_minutes=True,
                    notify_60_minutes=True,
                    created_at=datetime.now(),
                    updated_at=datetime.now()
                )
                db.add(notification_settings)
                db.commit()
                user_results['notification_settings_created'] = True
                print("✅ Notification settings created")
            else:
                print("✅ Notification settings already exist")
                user_results['notification_settings_created'] = True
            
            db.close()
            
        except Exception as e:
            error_msg = f"Test user creation failed: {e}"
            print(f"❌ {error_msg}")
            user_results['error'] = error_msg
        
        self.results['test_user'] = user_results
    
    def _generate_fix_summary(self):
        """Generate fix summary."""
        print("\n📋 FIX SUMMARY")
        print("=" * 60)
        
        fixes_applied = 0
        total_fixes = 3
        
        # Count successful fixes
        if self.results.get('data_loading', {}).get('total_events_loaded', 0) > 0:
            fixes_applied += 1
        if self.results.get('scraper_test', {}).get('test_successful'):
            fixes_applied += 1
        if self.results.get('test_user', {}).get('test_user_created'):
            fixes_applied += 1
        
        print(f"✅ Fixes applied: {fixes_applied}/{total_fixes}")
        
        # Data loading summary
        data_loading = self.results.get('data_loading', {})
        if data_loading.get('total_events_loaded', 0) > 0:
            print(f"✅ Loaded {data_loading['total_events_loaded']} events for {len(data_loading.get('dates_loaded', []))} dates")
        
        # Scraper test summary
        scraper_test = self.results.get('scraper_test', {})
        if scraper_test.get('test_successful'):
            print(f"✅ Scraper working: {scraper_test.get('events_found', 0)} events found for today")
        
        # Test user summary
        test_user = self.results.get('test_user', {})
        if test_user.get('test_user_created'):
            print("✅ Test user created for notification testing")
        
        # Remaining issues
        print("\n⚠️  REMAINING ISSUES TO FIX MANUALLY:")
        print("  • Set up valid Telegram bot token in .env file")
        print("  • Set up Telegram chat ID in .env file")
        print("  • Register real users with the bot")
        
        # Next steps
        print("\n🚀 NEXT STEPS:")
        print("  1. Update .env file with real Telegram credentials")
        print("  2. Start the bot: python main.py")
        print("  3. Register users by sending /start to the bot")
        print("  4. Enable notifications with /settings command")
        print("  5. Test notifications with /today command")
        
        self.results['summary'] = {
            'fixes_applied': fixes_applied,
            'total_fixes': total_fixes,
            'status': 'success' if fixes_applied == total_fixes else 'partial'
        }

def main():
    """Run the fix script."""
    try:
        fixer = ForexBotFixer()
        results = fixer.fix_all_issues()
        
        # Save results to file
        import json
        with open('fix_results.json', 'w') as f:
            json.dump(results, f, indent=2, default=str)
        
        print("\n📄 Detailed results saved to: fix_results.json")
        
        # Exit with appropriate code
        if results['summary']['status'] == 'success':
            print("\n🎉 ALL FIXES APPLIED SUCCESSFULLY!")
            sys.exit(0)
        else:
            print("\n⚠️  PARTIAL FIXES APPLIED - MANUAL INTERVENTION NEEDED")
            sys.exit(1)
            
    except Exception as e:
        print(f"❌ Fix script failed: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()
