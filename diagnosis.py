#!/usr/bin/env python3
"""
Comprehensive diagnostic script for Forex Bot system.
Checks database, scraper, notifications, and all components.
"""

import os
import sys
import sqlite3
import logging
from datetime import datetime, timedelta, date
from typing import Dict, List, Any

# Add app directory to Python path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'app'))

from app.config import config
from app.database.connection import SessionLocal, init_database
from app.database.models import NewsEvent, BotUser, UserNotificationSettings, ScrapingLog
from app.scrapers.forex_factory_scraper import ForexFactoryScraper
from app.services.news_service import NewsService
from app.services.notification_scheduler import NotificationScheduler

# Setup basic logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class ForexBotDiagnostics:
    """Comprehensive diagnostics for Forex Bot system."""
    
    def __init__(self):
        self.results = {}
        self.errors = []
        self.warnings = []
        
    def run_full_diagnosis(self) -> Dict[str, Any]:
        """Run complete system diagnosis."""
        print("🔍 Starting Forex Bot System Diagnosis...")
        print("=" * 60)
        
        # 1. Configuration Check
        self._check_configuration()
        
        # 2. Database Connectivity & Structure
        self._check_database()
        
        # 3. Data Analysis
        self._analyze_data()
        
        # 4. Scraper Test
        self._test_scraper()
        
        # 5. Notification System Check
        self._check_notifications()
        
        # 6. Generate Summary
        self._generate_summary()
        
        return self.results
    
    def _check_configuration(self):
        """Check system configuration."""
        print("\n📋 1. CONFIGURATION CHECK")
        print("-" * 30)
        
        config_results = {
            'database_url': config.DATABASE_URL,
            'telegram_token_set': bool(config.TELEGRAM_BOT_TOKEN and not config.TELEGRAM_BOT_TOKEN.startswith('your_')),
            'telegram_chat_id_set': bool(config.TELEGRAM_CHAT_ID and not config.TELEGRAM_CHAT_ID.startswith('your_')),
            'timezone': config.TIMEZONE,
            'scraper_schedule': f"{config.SCRAPER_SCHEDULE_HOUR:02d}:{config.SCRAPER_SCHEDULE_MINUTE:02d}",
            'log_level': config.LOG_LEVEL
        }
        
        print(f"✅ Database URL: {config_results['database_url']}")
        print(f"{'✅' if config_results['telegram_token_set'] else '❌'} Telegram Token: {'Set' if config_results['telegram_token_set'] else 'NOT SET'}")
        print(f"{'✅' if config_results['telegram_chat_id_set'] else '❌'} Telegram Chat ID: {'Set' if config_results['telegram_chat_id_set'] else 'NOT SET'}")
        print(f"✅ Timezone: {config_results['timezone']}")
        print(f"✅ Scraper Schedule: {config_results['scraper_schedule']}")
        
        if not config_results['telegram_token_set']:
            self.errors.append("Telegram bot token not configured")
        if not config_results['telegram_chat_id_set']:
            self.warnings.append("Telegram chat ID not configured")
            
        self.results['configuration'] = config_results
    
    def _check_database(self):
        """Check database connectivity and structure."""
        print("\n🗄️  2. DATABASE CHECK")
        print("-" * 30)
        
        db_results = {
            'connection': False,
            'tables': {},
            'file_exists': False
        }
        
        try:
            # Check if database file exists
            if config.DATABASE_URL.startswith('sqlite:'):
                db_path = config.DATABASE_URL.replace('sqlite:///', './').replace('sqlite:///', '')
                db_results['file_exists'] = os.path.exists(db_path)
                print(f"{'✅' if db_results['file_exists'] else '❌'} Database file exists: {db_path}")
            
            # Test connection and get table info
            if config.DATABASE_URL.startswith('sqlite:'):
                conn = sqlite3.connect(db_path)
                cursor = conn.cursor()
                
                # Get tables and row counts
                cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
                tables = cursor.fetchall()
                
                for table in tables:
                    table_name = table[0]
                    cursor.execute(f"SELECT COUNT(*) FROM {table_name}")
                    count = cursor.fetchone()[0]
                    db_results['tables'][table_name] = count
                    print(f"✅ Table {table_name}: {count} rows")
                
                conn.close()
                db_results['connection'] = True
                print("✅ Database connection successful")
                
        except Exception as e:
            print(f"❌ Database connection failed: {e}")
            self.errors.append(f"Database connection failed: {e}")
            db_results['connection'] = False
        
        self.results['database'] = db_results
    
    def _analyze_data(self):
        """Analyze existing data in the database."""
        print("\n📊 3. DATA ANALYSIS")
        print("-" * 30)
        
        data_results = {
            'total_events': 0,
            'date_range': None,
            'events_today': 0,
            'events_tomorrow': 0,
            'events_by_impact': {},
            'recent_scraping_logs': [],
            'users_count': 0,
            'notification_settings_count': 0
        }
        
        try:
            db = SessionLocal()
            
            # Total events
            total_events = db.query(NewsEvent).count()
            data_results['total_events'] = total_events
            print(f"✅ Total events in database: {total_events}")
            
            if total_events > 0:
                # Date range
                oldest = db.query(NewsEvent).order_by(NewsEvent.event_date.asc()).first()
                newest = db.query(NewsEvent).order_by(NewsEvent.event_date.desc()).first()
                data_results['date_range'] = f"{oldest.event_date} to {newest.event_date}"
                print(f"✅ Date range: {data_results['date_range']}")
                
                # Events for today and tomorrow
                today = date.today()
                tomorrow = today + timedelta(days=1)
                
                events_today = db.query(NewsEvent).filter(NewsEvent.event_date == today).count()
                events_tomorrow = db.query(NewsEvent).filter(NewsEvent.event_date == tomorrow).count()
                
                data_results['events_today'] = events_today
                data_results['events_tomorrow'] = events_tomorrow
                
                print(f"{'✅' if events_today > 0 else '⚠️'} Events today ({today}): {events_today}")
                print(f"{'✅' if events_tomorrow > 0 else '⚠️'} Events tomorrow ({tomorrow}): {events_tomorrow}")
                
                if events_today == 0 and events_tomorrow == 0:
                    self.warnings.append("No events for today or tomorrow - scraper may need to run")
            
            # Users and notification settings
            users_count = db.query(BotUser).count()
            notification_settings_count = db.query(UserNotificationSettings).count()
            
            data_results['users_count'] = users_count
            data_results['notification_settings_count'] = notification_settings_count
            
            print(f"✅ Bot users: {users_count}")
            print(f"✅ Notification settings: {notification_settings_count}")
            
            if users_count == 0:
                self.warnings.append("No users registered - notifications won't work")
            
            # Recent scraping logs
            recent_logs = db.query(ScrapingLog).order_by(ScrapingLog.created_at.desc()).limit(5).all()
            for log in recent_logs:
                log_info = {
                    'timestamp': log.created_at.isoformat() if log.created_at else 'Unknown',
                    'status': log.status,
                    'events_scraped': log.events_scraped,
                    'error_message': log.error_message
                }
                data_results['recent_scraping_logs'].append(log_info)
                status_emoji = "✅" if log.status == "success" else "❌"
                print(f"{status_emoji} Scraping log: {log.created_at} - {log.status} - {log.events_scraped} events")
            
            db.close()
            
        except Exception as e:
            print(f"❌ Data analysis failed: {e}")
            self.errors.append(f"Data analysis failed: {e}")
        
        self.results['data_analysis'] = data_results
    
    def _test_scraper(self):
        """Test the scraper functionality."""
        print("\n🕷️  4. SCRAPER TEST")
        print("-" * 30)
        
        scraper_results = {
            'scraper_initialized': False,
            'test_scrape_successful': False,
            'test_events_count': 0,
            'test_error': None
        }
        
        try:
            # Initialize scraper
            scraper = ForexFactoryScraper()
            scraper_results['scraper_initialized'] = True
            print("✅ Scraper initialized successfully")
            
            # Test scraping for tomorrow (to avoid overwriting existing data)
            test_date = date.today() + timedelta(days=1)
            print(f"🔄 Testing scraper for date: {test_date}")
            
            # Run a quick test scrape
            test_events = scraper.scrape_single_date(test_date)
            scraper_results['test_events_count'] = len(test_events)
            scraper_results['test_scrape_successful'] = True
            
            print(f"✅ Test scrape successful: {len(test_events)} events found")
            
            if len(test_events) == 0:
                self.warnings.append(f"No events found for {test_date} - this might be normal for weekends/holidays")
            
        except Exception as e:
            print(f"❌ Scraper test failed: {e}")
            scraper_results['test_error'] = str(e)
            self.errors.append(f"Scraper test failed: {e}")
        
        self.results['scraper_test'] = scraper_results
    
    def _check_notifications(self):
        """Check notification system."""
        print("\n🔔 5. NOTIFICATION SYSTEM CHECK")
        print("-" * 30)
        
        notification_results = {
            'scheduler_initialized': False,
            'users_with_notifications': 0,
            'notification_logic_working': False,
            'test_error': None
        }
        
        try:
            # Check if we can initialize notification scheduler
            # Note: We won't actually start it to avoid conflicts
            db = SessionLocal()
            
            # Count users with notification settings enabled
            users_with_notifications = db.query(BotUser).join(
                UserNotificationSettings
            ).filter(
                UserNotificationSettings.notifications_enabled == True
            ).count()
            
            notification_results['users_with_notifications'] = users_with_notifications
            print(f"✅ Users with notifications enabled: {users_with_notifications}")
            
            if users_with_notifications == 0:
                self.warnings.append("No users have notifications enabled")
            
            # Check for high impact events that would trigger notifications
            high_impact_events = db.query(NewsEvent).filter(
                NewsEvent.event_date >= date.today(),
                NewsEvent.impact_level_id == 4  # HIGH impact
            ).count()
            
            print(f"✅ High impact events (future): {high_impact_events}")
            
            if high_impact_events == 0:
                self.warnings.append("No high impact events found for notifications")
            
            notification_results['notification_logic_working'] = True
            print("✅ Notification logic check passed")
            
            db.close()
            
        except Exception as e:
            print(f"❌ Notification system check failed: {e}")
            notification_results['test_error'] = str(e)
            self.errors.append(f"Notification system check failed: {e}")
        
        self.results['notification_check'] = notification_results
    
    def _generate_summary(self):
        """Generate diagnosis summary."""
        print("\n📋 DIAGNOSIS SUMMARY")
        print("=" * 60)
        
        total_checks = 5
        passed_checks = 0
        
        # Count successful checks
        if self.results.get('configuration', {}).get('database_url'):
            passed_checks += 1
        if self.results.get('database', {}).get('connection'):
            passed_checks += 1
        if self.results.get('data_analysis', {}).get('total_events', 0) > 0:
            passed_checks += 1
        if self.results.get('scraper_test', {}).get('scraper_initialized'):
            passed_checks += 1
        if self.results.get('notification_check', {}).get('notification_logic_working'):
            passed_checks += 1
        
        print(f"✅ Checks passed: {passed_checks}/{total_checks}")
        print(f"❌ Errors: {len(self.errors)}")
        print(f"⚠️  Warnings: {len(self.warnings)}")
        
        if self.errors:
            print("\n❌ CRITICAL ERRORS:")
            for error in self.errors:
                print(f"  • {error}")
        
        if self.warnings:
            print("\n⚠️  WARNINGS:")
            for warning in self.warnings:
                print(f"  • {warning}")
        
        # Recommendations
        print("\n💡 RECOMMENDATIONS:")
        
        if not self.results.get('configuration', {}).get('telegram_token_set'):
            print("  • Set up a valid Telegram bot token in .env file")
        
        if self.results.get('data_analysis', {}).get('events_today', 0) == 0:
            print("  • Run scraper to load current data: python -c 'from app.scrapers.forex_factory_scraper import ForexFactoryScraper; scraper = ForexFactoryScraper(); scraper.scrape_date_range(date.today(), date.today() + timedelta(days=7))'")
        
        if self.results.get('data_analysis', {}).get('users_count', 0) == 0:
            print("  • Register users with the bot to enable notifications")
        
        if self.results.get('notification_check', {}).get('users_with_notifications', 0) == 0:
            print("  • Enable notifications for users: /settings command in bot")
        
        # Overall status
        if len(self.errors) == 0:
            if len(self.warnings) == 0:
                print("\n🎉 SYSTEM STATUS: HEALTHY")
            else:
                print("\n⚠️  SYSTEM STATUS: FUNCTIONAL WITH WARNINGS")
        else:
            print("\n❌ SYSTEM STATUS: NEEDS ATTENTION")
        
        self.results['summary'] = {
            'total_checks': total_checks,
            'passed_checks': passed_checks,
            'errors_count': len(self.errors),
            'warnings_count': len(self.warnings),
            'errors': self.errors,
            'warnings': self.warnings,
            'status': 'healthy' if len(self.errors) == 0 and len(self.warnings) == 0 else 'needs_attention'
        }

def main():
    """Run the diagnostic script."""
    try:
        diagnostics = ForexBotDiagnostics()
        results = diagnostics.run_full_diagnosis()
        
        # Save results to file
        import json
        with open('diagnosis_results.json', 'w') as f:
            json.dump(results, f, indent=2, default=str)
        
        print(f"\n📄 Detailed results saved to: diagnosis_results.json")
        
        # Exit with appropriate code
        if results['summary']['status'] == 'healthy':
            sys.exit(0)
        else:
            sys.exit(1)
            
    except Exception as e:
        print(f"❌ Diagnosis script failed: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()
