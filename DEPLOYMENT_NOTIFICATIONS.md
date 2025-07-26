# Notification Feature Deployment Guide

## Overview

The notification feature has been implemented with backward compatibility. This means the bot will work even if the notification database columns haven't been added yet, but the notification functionality will be disabled until the database migration is run.

## Deployment Steps

### Step 1: Deploy the Code

Deploy the updated code to your environment. The bot will start normally, but notifications will be disabled.

### Step 2: Run Database Migration

When you have access to the database, run the migration script:

```bash
python migrations/add_notification_fields.py
```

This will add the following columns to the `users` table:
- `notifications_enabled` (BOOLEAN, default: FALSE)
- `notification_minutes` (INTEGER, default: 30)
- `notification_impact_levels` (TEXT, default: 'high')

### Step 3: Verify Migration

After running the migration, the notification feature will be automatically enabled. Users can then:

1. Use `/settings` command
2. Click "🔔 Notifications"
3. Configure their notification preferences

## Backward Compatibility

The implementation is designed to be backward compatible:

- **Before Migration**: Notification settings won't appear in `/settings`
- **After Migration**: Full notification functionality will be available

## Testing the Feature

### Before Migration
- `/settings` will show only currency, impact, analysis, and digest time settings
- No notification-related errors will occur

### After Migration
- `/settings` will include "🔔 Notifications" option
- Users can configure notification timing and impact levels
- Notifications will be sent automatically

## Troubleshooting

### If Migration Fails
1. Check database connection
2. Verify database permissions
3. Run migration manually with SQL:
   ```sql
   ALTER TABLE users ADD COLUMN notifications_enabled BOOLEAN DEFAULT FALSE;
   ALTER TABLE users ADD COLUMN notification_minutes INTEGER DEFAULT 30;
   ALTER TABLE users ADD COLUMN notification_impact_levels TEXT DEFAULT 'high';
   ```

### If Notifications Don't Work
1. Check if migration was successful
2. Verify notification scheduler is running
3. Check user notification settings via `/settings`
4. Review application logs for errors

## Monitoring

After deployment, monitor:
- Application startup logs for notification scheduler
- User interaction with `/settings` command
- Notification delivery success/failure rates

## Rollback Plan

If issues occur:
1. The notification feature can be disabled by not running the migration
2. The bot will continue to work normally without notifications
3. No existing functionality will be affected

---

**✅ The notification feature is ready for deployment with full backward compatibility!**
