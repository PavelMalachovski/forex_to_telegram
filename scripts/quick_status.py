#!/usr/bin/env python3
"""
Quick status check for Forex Bot system.
Provides a fast overview of system health.
"""

import os
import sys
import sqlite3
from datetime import datetime, date, timedelta

# Add app directory to Python path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'app'))

from app.config import config

def quick_status_check():
    """Perform a quick status check of the system."""
    print("🚀 Forex Bot Quick Status Check")
    print("=" * 40)
    
    # Configuration Status
    print("\n📋 CONFIGURATION")
    token_set = bool(config.TELEGRAM_BOT_TOKEN and not config.TELEGRAM_BOT_TOKEN.startswith('your_'))
    chat_id_set = bool(config.TELEGRAM_CHAT_ID and not config.TELEGRAM_CHAT_ID.startswith('your_'))
    
    print(f"{'✅' if token_set else '❌'} Telegram Token: {'SET' if token_set else 'NOT SET'}")
    print(f"{'✅' if chat_id_set else '⚠️'} Chat ID: {'SET' if chat_id_set else 'NOT SET'}")
    print(f"✅ Database: {config.DATABASE_URL}")
    print(f"✅ Timezone: {config.TIMEZONE}")
    
    # Database Status
    print("\n🗄️  DATABASE")
    try:
        if config.DATABASE_URL.startswith('sqlite:'):
            db_path = config.DATABASE_URL.replace('sqlite:///', './').replace('sqlite:///', '')
            
            if os.path.exists(db_path):
                conn = sqlite3.connect(db_path)
                cursor = conn.cursor()
                
                # Get total events
                cursor.execute("SELECT COUNT(*) FROM news_events")
                total_events = cursor.fetchone()[0]
                
                # Get events for today and tomorrow
                today = date.today().strftime('%Y-%m-%d')
                tomorrow = (date.today() + timedelta(days=1)).strftime('%Y-%m-%d')
                
                cursor.execute("SELECT COUNT(*) FROM news_events WHERE event_date = ?", (today,))
                events_today = cursor.fetchone()[0]
                
                cursor.execute("SELECT COUNT(*) FROM news_events WHERE event_date = ?", (tomorrow,))
                events_tomorrow = cursor.fetchone()[0]
                
                # Get users
                cursor.execute("SELECT COUNT(*) FROM bot_users")
                users_count = cursor.fetchone()[0]
                
                # Get notification settings
                cursor.execute("SELECT COUNT(*) FROM user_notification_settings WHERE notifications_enabled = 1")
                notifications_enabled = cursor.fetchone()[0]
                
                # Get high impact events
                cursor.execute("""
                    SELECT COUNT(*) FROM news_events ne 
                    JOIN impact_levels il ON ne.impact_level_id = il.id 
                    WHERE il.code = 'HIGH' AND ne.event_date >= ?
                """, (today,))
                high_impact_future = cursor.fetchone()[0]
                
                conn.close()
                
                print("✅ Connection: Working")
                print(f"✅ Total Events: {total_events}")
                print(f"{'✅' if events_today > 0 else '⚠️'} Events Today: {events_today}")
                print(f"{'✅' if events_tomorrow > 0 else '⚠️'} Events Tomorrow: {events_tomorrow}")
                print(f"{'✅' if users_count > 0 else '⚠️'} Users: {users_count}")
                print(f"{'✅' if notifications_enabled > 0 else '⚠️'} Notifications Enabled: {notifications_enabled}")
                print(f"{'✅' if high_impact_future > 0 else '⚠️'} High Impact Events (Future): {high_impact_future}")
                
            else:
                print("❌ Database file not found")
                
    except Exception as e:
        print(f"❌ Database Error: {e}")
    
    # System Status Summary
    print("\n🎯 SYSTEM STATUS")
    
    # Calculate overall health
    checks = [
        token_set,  # Telegram token
        os.path.exists(db_path) if config.DATABASE_URL.startswith('sqlite:') else False,  # DB exists
        total_events > 0 if 'total_events' in locals() else False,  # Has events
        events_today > 0 if 'events_today' in locals() else False,  # Current data
    ]
    
    health_score = sum(checks) / len(checks) * 100
    
    if health_score >= 75:
        status = "🟢 HEALTHY"
    elif health_score >= 50:
        status = "🟡 NEEDS ATTENTION"
    else:
        status = "🔴 CRITICAL"
    
    print(f"Overall Health: {health_score:.0f}% - {status}")
    
    # Quick recommendations
    print("\n💡 QUICK ACTIONS")
    if not token_set:
        print("❗ Set Telegram bot token in .env file")
    if 'events_today' in locals() and events_today == 0:
        print("❗ Run: python fix_system.py (to load current data)")
    if 'users_count' in locals() and users_count == 0:
        print("❗ Start bot and register users: python main.py")
    if 'notifications_enabled' in locals() and notifications_enabled == 0:
        print("❗ Enable notifications via /settings command")
    
    if health_score >= 75:
        print("🎉 System ready! Start with: python main.py")
    
    print(f"\n📅 Last checked: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

if __name__ == "__main__":
    try:
        quick_status_check()
    except Exception as e:
        print(f"❌ Status check failed: {e}")
        sys.exit(1)
