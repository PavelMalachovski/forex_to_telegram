#!/usr/bin/env python3
"""Setup script for notification feature."""

import os
import sys
from datetime import datetime

# Add the bot directory to the path
sys.path.append(os.path.join(os.path.dirname(__file__), 'bot'))

def setup_notifications():
    """Set up the notification feature."""

    print("🔔 Setting up Notification Feature...")

    try:
        from bot.config import Config
        from bot.database_service import ForexNewsService
        from bot.models import DatabaseManager

        # Initialize config
        config = Config()
        print("✅ Config loaded")

        # Initialize database manager
        db_manager = DatabaseManager(config.get_database_url())
        print("✅ Database manager initialized")

        # Create tables (this will include the new notification fields)
        db_manager.create_tables()
        print("✅ Database tables created/updated")

        # Test database service
        db_service = ForexNewsService(config.get_database_url())
        print("✅ Database service initialized")

        # Test user creation with notification fields
        test_user_id = 999999999  # Use a test ID
        user = db_service.get_or_create_user(test_user_id)

        # Update notification preferences
        success = db_service.update_user_preferences(
            test_user_id,
            notifications_enabled=True,
            notification_minutes=30,
            notification_impact_levels="high,medium"
        )

        if success:
            print("✅ Notification preferences updated successfully")
        else:
            print("❌ Failed to update notification preferences")

        # Clean up test user
        try:
            with db_manager.get_session() as session:
                test_user = session.query(user.__class__).filter(
                    user.__class__.telegram_id == test_user_id
                ).first()
                if test_user:
                    session.delete(test_user)
                    session.commit()
                    print("✅ Test user cleaned up")
        except Exception as e:
            print(f"⚠️ Warning: Could not clean up test user: {e}")

        print("\n🎉 Notification feature setup completed successfully!")
        print("\n📋 Next steps:")
        print("1. Deploy the updated bot code")
        print("2. Users can now use /settings to configure notifications")
        print("3. The notification scheduler will automatically start")
        print("4. Users will receive alerts before high-impact news events")

    except Exception as e:
        print(f"❌ Error setting up notifications: {e}")
        import traceback
        traceback.print_exc()
        return False

    return True

if __name__ == "__main__":
    print("🚀 Starting Notification Feature Setup...")
    success = setup_notifications()

    if success:
        print("\n✅ Setup completed successfully!")
    else:
        print("\n❌ Setup failed!")
        sys.exit(1)
