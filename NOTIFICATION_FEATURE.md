# Notification Feature Implementation

## Overview

The notification feature allows users to receive real-time alerts before high-impact news events. Users can configure when they want to be notified (15, 30, or 60 minutes before events) and which impact levels they want to be alerted about.

## Features

### 🔔 Notification Settings
- **Enable/Disable**: Users can turn notifications on or off
- **Timing Options**: 15, 30, or 60 minutes before events
- **Impact Filtering**: Choose High, Medium, or Low impact events
- **Smart Scheduling**: Automatic checks every 5 minutes

### 📱 Notification Format
```
⚠️ In 30 minutes: high news!
14:30 | USD | Non-Farm Payrolls | 🔴 High Impact
```

## Implementation Details

### Database Changes

#### User Model Updates (`bot/models.py`)
Added new fields to the User model:
- `notifications_enabled`: Boolean (default: False)
- `notification_minutes`: Integer (default: 30)
- `notification_impact_levels`: Text (default: "high")

#### Database Service Updates (`bot/database_service.py`)
Added method:
- `get_users_with_notifications_enabled()`: Get all users with notifications enabled

### New Services

#### Notification Service (`bot/notification_service.py`)
- `format_notification_message()`: Format notification messages
- `get_upcoming_events()`: Find events within notification window
- `send_notifications()`: Send notifications to specific user
- `check_and_send_notifications_for_all_users()`: Check all users

#### Notification Scheduler (`bot/notification_scheduler.py`)
- Runs every 5 minutes
- Checks for upcoming events
- Sends notifications to enabled users

### UI Updates

#### Settings Handler (`bot/user_settings.py`)
Added notification settings to `/settings` command:
- **🔔 Notifications**: Enable/disable toggle
- **⏱️ Alert Timing**: Choose 15, 30, or 60 minutes
- **📊 Alert Impact**: Select impact levels

## Usage

### For Users

1. **Access Settings**: Use `/settings` command
2. **Configure Notifications**: Click "🔔 Notifications"
3. **Enable Notifications**: Toggle notifications on/off
4. **Set Timing**: Choose 15, 30, or 60 minutes before events
5. **Select Impact Levels**: Choose High, Medium, or Low impact events

### For Developers

#### Running the Feature
```bash
# Set up the notification feature
python setup_notifications.py

# Test the notification functionality
python test_notifications.py

# Run the main application
python app.py
```

#### Database Migration
```bash
# Run the migration to add notification fields
python migrations/add_notification_fields.py
```

## Configuration

### Environment Variables
No additional environment variables required. The feature uses existing database and bot configuration.

### Database Schema
The User table now includes:
```sql
ALTER TABLE users ADD COLUMN notifications_enabled BOOLEAN DEFAULT FALSE;
ALTER TABLE users ADD COLUMN notification_minutes INTEGER DEFAULT 30;
ALTER TABLE users ADD COLUMN notification_impact_levels TEXT DEFAULT 'high';
```

## Technical Details

### Notification Logic
1. **Scheduler**: Runs every 5 minutes
2. **Event Detection**: Checks for events within user's notification window
3. **Time Parsing**: Handles various time formats (12h/24h)
4. **Message Formatting**: Creates user-friendly notification messages
5. **Delivery**: Sends via Telegram bot

### Error Handling
- Graceful handling of database connection issues
- Logging of all notification activities
- Fallback mechanisms for time parsing
- User preference validation

### Performance Considerations
- Efficient database queries for upcoming events
- Minimal impact on existing functionality
- Background processing for notification checks
- Smart filtering to reduce unnecessary notifications

## Testing

### Test Scripts
- `test_notifications.py`: Comprehensive notification testing
- `setup_notifications.py`: Feature setup and validation

### Test Coverage
- Notification message formatting
- Time parsing functionality
- User preference management
- Scheduler operation
- Database operations

## Deployment

### Prerequisites
1. Updated database schema with notification fields
2. Deployed bot code with notification services
3. Environment variables configured

### Steps
1. Run database migration: `python migrations/add_notification_fields.py`
2. Deploy updated code
3. Verify notification scheduler starts automatically
4. Test with `/settings` command

## Monitoring

### Logs to Watch
- Notification scheduler startup/shutdown
- Notification delivery success/failure
- User preference updates
- Database connection issues

### Metrics
- Number of notifications sent per day
- User adoption rate of notification feature
- Notification delivery success rate

## Future Enhancements

### Potential Improvements
- **Custom Notification Times**: Allow users to set specific times
- **Notification History**: Track sent notifications
- **Advanced Filtering**: Filter by currency pairs
- **Notification Templates**: Customizable message formats
- **Batch Notifications**: Group multiple events in one message

### Integration Opportunities
- **Webhook Support**: External notification endpoints
- **Email Notifications**: Alternative delivery method
- **Mobile Push**: Native mobile notifications
- **Analytics Dashboard**: Notification usage statistics

## Troubleshooting

### Common Issues

#### Notifications Not Sending
1. Check if notifications are enabled for user
2. Verify notification timing settings
3. Check scheduler logs for errors
4. Ensure database connection is working

#### Database Migration Issues
1. Verify database connection string
2. Check table permissions
3. Run migration script manually
4. Verify column existence

#### Scheduler Not Starting
1. Check APScheduler installation
2. Verify bot initialization
3. Check for conflicting schedulers
4. Review startup logs

### Debug Commands
```bash
# Test notification service
python test_notifications.py

# Check database schema
python -c "from bot.models import DatabaseManager; db = DatabaseManager(); print('Tables:', db.engine.table_names())"

# Verify user preferences
python -c "from bot.database_service import ForexNewsService; from bot.config import Config; db = ForexNewsService(Config().get_database_url()); user = db.get_or_create_user(YOUR_USER_ID); print('Notifications:', user.notifications_enabled)"
```

## Support

For issues with the notification feature:
1. Check the logs for error messages
2. Verify user settings via `/settings`
3. Test with the provided test scripts
4. Review this documentation for configuration details

---

**🎯 The notification feature is now ready for deployment and will provide users with timely alerts for important forex news events!**
