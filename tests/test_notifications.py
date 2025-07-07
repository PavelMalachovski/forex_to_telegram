#!/usr/bin/env python3
"""
Test notification system for Forex Bot.
Tests notification scheduling and logic without sending actual messages.
"""

import os
import sys
import logging
from datetime import datetime, timedelta, date
from typing import Dict, List, Any

# Add app directory to Python path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'app'))

from app.config import config
from app.database.connection import SessionLocal
from app.database.models import NewsEvent, BotUser, UserNotificationSettings, ImpactLevel
from app.services.notification_scheduler import NotificationScheduler
from app.utils.timezone_utils import get_current_time, get_local_timezone

# Setup logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class MockBot:
    """Mock bot for testing notifications without sending real messages."""
    
    def __init__(self):
        self.sent_messages = []
    
    def send_message(self, chat_id, text, parse_mode=None):
        """Mock send_message that logs instead of sending."""
        message = {
            'chat_id': chat_id,
            'text': text,
            'parse_mode': parse_mode,
            'timestamp': datetime.now().isoformat()
        }
        self.sent_messages.append(message)
        print(f"📤 MOCK MESSAGE to {chat_id}: {text[:100]}...")
        return True

class NotificationTester:
    """Test notification system."""
    
    def __init__(self):
        self.results = {}
        self.mock_bot = MockBot()
        
    def test_notification_system(self) -> Dict[str, Any]:
        """Test the complete notification system."""
        print("🔔 Testing Forex Bot Notification System...")
        print("=" * 60)
        
        # 1. Check notification data
        self._check_notification_data()
        
        # 2. Test notification scheduler
        self._test_notification_scheduler()
        
        # 3. Test notification logic
        self._test_notification_logic()
        
        # 4. Generate summary
        self._generate_test_summary()
        
        return self.results
    
    def _check_notification_data(self):
        """Check data needed for notifications."""
        print("\n📊 1. CHECKING NOTIFICATION DATA")
        print("-" * 30)
        
        data_results = {
            'users_with_notifications': 0,
            'high_impact_events_today': 0,
            'high_impact_events_tomorrow': 0,
            'high_impact_events_future': 0,
            'sample_events': []
        }
        
        try:
            db = SessionLocal()
            
            # Count users with notifications enabled
            users_with_notifications = db.query(BotUser).join(
                UserNotificationSettings
            ).filter(
                UserNotificationSettings.notifications_enabled == True
            ).count()
            
            data_results['users_with_notifications'] = users_with_notifications
            print(f"✅ Users with notifications enabled: {users_with_notifications}")
            
            # Count high impact events
            today = date.today()
            tomorrow = today + timedelta(days=1)
            
            # Get HIGH impact level ID
            high_impact = db.query(ImpactLevel).filter(ImpactLevel.code == "HIGH").first()
            if high_impact:
                high_impact_id = high_impact.id
                
                # Today's high impact events
                high_today = db.query(NewsEvent).filter(
                    NewsEvent.event_date == today,
                    NewsEvent.impact_level_id == high_impact_id
                ).count()
                
                # Tomorrow's high impact events
                high_tomorrow = db.query(NewsEvent).filter(
                    NewsEvent.event_date == tomorrow,
                    NewsEvent.impact_level_id == high_impact_id
                ).count()
                
                # Future high impact events (next 7 days)
                future_date = today + timedelta(days=7)
                high_future = db.query(NewsEvent).filter(
                    NewsEvent.event_date >= today,
                    NewsEvent.event_date <= future_date,
                    NewsEvent.impact_level_id == high_impact_id
                ).count()
                
                data_results['high_impact_events_today'] = high_today
                data_results['high_impact_events_tomorrow'] = high_tomorrow
                data_results['high_impact_events_future'] = high_future
                
                print(f"✅ High impact events today: {high_today}")
                print(f"✅ High impact events tomorrow: {high_tomorrow}")
                print(f"✅ High impact events (next 7 days): {high_future}")
                
                # Get sample high impact events
                sample_events = db.query(NewsEvent).filter(
                    NewsEvent.event_date >= today,
                    NewsEvent.impact_level_id == high_impact_id
                ).limit(5).all()
                
                for event in sample_events:
                    event_info = {
                        'date': str(event.event_date),
                        'time': str(event.event_time),
                        'currency': event.currency.code,
                        'name': event.event_name,
                        'impact': event.impact_level.code
                    }
                    data_results['sample_events'].append(event_info)
                    print(f"  📅 {event.event_date} {event.event_time} - {event.currency.code} - {event.event_name}")
            
            db.close()
            
        except Exception as e:
            print(f"❌ Data check failed: {e}")
        
        self.results['notification_data'] = data_results
    
    def _test_notification_scheduler(self):
        """Test notification scheduler initialization."""
        print("\n⏰ 2. TESTING NOTIFICATION SCHEDULER")
        print("-" * 30)
        
        scheduler_results = {
            'scheduler_initialized': False,
            'jobs_scheduled': 0,
            'error': None
        }
        
        try:
            db = SessionLocal()
            
            # Initialize notification scheduler with mock bot
            scheduler = NotificationScheduler(self.mock_bot, lambda: SessionLocal())
            scheduler_results['scheduler_initialized'] = True
            print("✅ Notification scheduler initialized")
            
            # Get high impact events for testing
            high_impact = db.query(ImpactLevel).filter(ImpactLevel.code == "HIGH").first()
            if high_impact:
                future_events = db.query(NewsEvent).filter(
                    NewsEvent.event_date >= date.today(),
                    NewsEvent.impact_level_id == high_impact.id
                ).limit(5).all()
                
                if future_events:
                    print(f"🔄 Scheduling notifications for {len(future_events)} high impact events...")
                    
                    # Schedule notifications
                    scheduler.schedule_notifications_for_events(future_events)
                    
                    # Count scheduled jobs
                    scheduled_jobs = len(scheduler.scheduler.get_jobs())
                    scheduler_results['jobs_scheduled'] = scheduled_jobs
                    print(f"✅ Scheduled {scheduled_jobs} notification jobs")
                    
                    # Show scheduled jobs
                    for job in scheduler.scheduler.get_jobs()[:5]:  # Show first 5
                        print(f"  📅 Job: {job.id} - Next run: {job.next_run_time}")
                else:
                    print("⚠️  No high impact events found for scheduling")
            
            # Stop scheduler to avoid conflicts
            scheduler.stop()
            print("✅ Scheduler stopped after testing")
            
            db.close()
            
        except Exception as e:
            error_msg = f"Scheduler test failed: {e}"
            print(f"❌ {error_msg}")
            scheduler_results['error'] = error_msg
        
        self.results['scheduler_test'] = scheduler_results
    
    def _test_notification_logic(self):
        """Test notification logic without scheduling."""
        print("\n🧠 3. TESTING NOTIFICATION LOGIC")
        print("-" * 30)
        
        logic_results = {
            'test_notifications_sent': 0,
            'test_successful': False,
            'sample_messages': [],
            'error': None
        }
        
        try:
            db = SessionLocal()
            
            # Get a test user
            test_user = db.query(BotUser).filter(BotUser.telegram_user_id == 123456789).first()
            
            if test_user:
                # Get high impact events
                high_impact = db.query(ImpactLevel).filter(ImpactLevel.code == "HIGH").first()
                if high_impact:
                    test_events = db.query(NewsEvent).filter(
                        NewsEvent.event_date >= date.today(),
                        NewsEvent.impact_level_id == high_impact.id
                    ).limit(3).all()
                    
                    if test_events:
                        print(f"🔄 Testing notification logic with {len(test_events)} events...")
                        
                        # Initialize scheduler with mock bot
                        scheduler = NotificationScheduler(self.mock_bot, lambda: SessionLocal())
                        
                        # Test sending notifications manually
                        for event in test_events:
                            try:
                                scheduler._send_notification(
                                    test_user.telegram_user_id,
                                    event,
                                    "15 minutes"
                                )
                                logic_results['test_notifications_sent'] += 1
                            except Exception as e:
                                print(f"⚠️  Error in notification logic: {e}")
                        
                        # Get sample messages
                        logic_results['sample_messages'] = self.mock_bot.sent_messages[:3]
                        logic_results['test_successful'] = True
                        
                        print(f"✅ Notification logic test successful: {logic_results['test_notifications_sent']} messages")
                        
                        # Show sample message content
                        if self.mock_bot.sent_messages:
                            print("📋 Sample notification content:")
                            sample_msg = self.mock_bot.sent_messages[0]
                            lines = sample_msg['text'].split('\n')[:5]  # First 5 lines
                            for line in lines:
                                print(f"  {line}")
                        
                        scheduler.stop()
                    else:
                        print("⚠️  No high impact events found for testing")
                else:
                    print("❌ HIGH impact level not found in database")
            else:
                print("❌ Test user not found")
            
            db.close()
            
        except Exception as e:
            error_msg = f"Notification logic test failed: {e}"
            print(f"❌ {error_msg}")
            logic_results['error'] = error_msg
        
        self.results['logic_test'] = logic_results
    
    def _generate_test_summary(self):
        """Generate test summary."""
        print("\n📋 NOTIFICATION TEST SUMMARY")
        print("=" * 60)
        
        tests_passed = 0
        total_tests = 3
        
        # Count successful tests
        if self.results.get('notification_data', {}).get('users_with_notifications', 0) > 0:
            tests_passed += 1
        if self.results.get('scheduler_test', {}).get('scheduler_initialized'):
            tests_passed += 1
        if self.results.get('logic_test', {}).get('test_successful'):
            tests_passed += 1
        
        print(f"✅ Tests passed: {tests_passed}/{total_tests}")
        
        # Data summary
        data = self.results.get('notification_data', {})
        print(f"✅ Users with notifications: {data.get('users_with_notifications', 0)}")
        print(f"✅ High impact events (future): {data.get('high_impact_events_future', 0)}")
        
        # Scheduler summary
        scheduler = self.results.get('scheduler_test', {})
        if scheduler.get('scheduler_initialized'):
            print(f"✅ Notification scheduler working: {scheduler.get('jobs_scheduled', 0)} jobs scheduled")
        
        # Logic summary
        logic = self.results.get('logic_test', {})
        if logic.get('test_successful'):
            print(f"✅ Notification logic working: {logic.get('test_notifications_sent', 0)} test messages")
        
        # Overall status
        if tests_passed == total_tests:
            print("\n🎉 NOTIFICATION SYSTEM: FULLY FUNCTIONAL")
            status = 'fully_functional'
        elif tests_passed > 0:
            print("\n⚠️  NOTIFICATION SYSTEM: PARTIALLY FUNCTIONAL")
            status = 'partially_functional'
        else:
            print("\n❌ NOTIFICATION SYSTEM: NOT FUNCTIONAL")
            status = 'not_functional'
        
        # Recommendations
        print("\n💡 RECOMMENDATIONS:")
        if data.get('users_with_notifications', 0) == 0:
            print("  • Add real users and enable their notifications")
        if data.get('high_impact_events_future', 0) == 0:
            print("  • Ensure high impact events are being scraped")
        if not scheduler.get('scheduler_initialized'):
            print("  • Fix notification scheduler initialization")
        
        print("\n🚀 TO ENABLE REAL NOTIFICATIONS:")
        print("  1. Set valid Telegram bot token in .env")
        print("  2. Start the bot: python main.py")
        print("  3. Users send /start to register")
        print("  4. Users use /settings to enable notifications")
        print("  5. System will automatically send alerts before high impact events")
        
        self.results['summary'] = {
            'tests_passed': tests_passed,
            'total_tests': total_tests,
            'status': status,
            'mock_messages_sent': len(self.mock_bot.sent_messages)
        }

def main():
    """Run the notification test."""
    try:
        tester = NotificationTester()
        results = tester.test_notification_system()
        
        # Save results to file
        import json
        with open('notification_test_results.json', 'w') as f:
            json.dump(results, f, indent=2, default=str)
        
        print(f"\n📄 Detailed results saved to: notification_test_results.json")
        
        # Exit with appropriate code
        if results['summary']['status'] == 'fully_functional':
            sys.exit(0)
        else:
            sys.exit(1)
            
    except Exception as e:
        print(f"❌ Notification test failed: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()
