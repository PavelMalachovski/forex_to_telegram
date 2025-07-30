# Notification System Fixes

## Issues Fixed

### 1. Duplicate Notifications Every 5 Minutes
**Problem**: You were receiving notifications every 5 minutes instead of once at the specified time (30 minutes before events).

**Root Cause**:
- The scheduler was running every 5 minutes
- The notification logic was checking if events were within a 30-minute window (0-30 minutes before)
- This meant events would trigger notifications multiple times as they approached

**Solution**:
- Changed scheduler to run every 2 minutes for more precise timing
- Modified notification logic to only send notifications when events are exactly at the notification time (e.g., 30 minutes before)
- Added a 2.5-minute window tolerance for scheduling precision
- Improved deduplication logic to prevent duplicate notifications

### 2. Group Events Not Combined
**Problem**: Multiple events happening at the same time were sending separate notifications instead of one combined notification.

**Solution**:
- Added `_group_events_by_time()` method to group events by their time
- Created `format_group_notification_message()` method to format multiple events in a single message
- Events are grouped by impact level (High, Medium, Low) within the group notification
- Group notifications are properly deduplicated to prevent spam

## Key Changes Made

### 1. Notification Service (`bot/notification_service.py`)

#### Improved Timing Logic
```python
# OLD: Check if event is within notification window
if 0 <= minutes_diff <= minutes_before:

# NEW: Check if event is exactly at notification time
if abs(minutes_diff - minutes_before) <= 2.5:  # Allow 2.5 minute window
```

#### Added Group Notification Support
```python
def _group_events_by_time(self, events):
    """Group events by their time to identify events happening at the same time."""

def format_group_notification_message(self, events, minutes_before, user_timezone):
    """Format a notification message for multiple events happening at the same time."""
```

#### Enhanced Deduplication
```python
# For individual events
if not self.deduplication.should_send_notification("news_event",
                                                  event_id=item.get('id', 'unknown'),
                                                  user_id=user_id,
                                                  notification_minutes=user.notification_minutes):

# For group events
if not self.deduplication.should_send_notification("group_news_event",
                                                  user_id=user_id,
                                                  events_hash=events_hash,
                                                  notification_minutes=user.notification_minutes):
```

### 2. Notification Scheduler (`bot/notification_scheduler.py`)

#### Improved Timing
```python
# OLD: Check every 5 minutes
IntervalTrigger(minutes=5)

# NEW: Check every 2 minutes for more precise timing
IntervalTrigger(minutes=2)
```

#### Better Logging
```python
# Added more descriptive logging
logger.debug("No notifications sent - no events within notification windows")
```

## How It Works Now

### 1. Single Event Notifications
- When an event is exactly 30 minutes (or your set time) before the event, you receive one notification
- The notification includes the event details and impact level
- No duplicate notifications are sent

### 2. Group Event Notifications
- When multiple events happen at the same time, you receive one combined notification
- Events are grouped by impact level (High, Medium, Low)
- Each event shows: Time | Currency | Event Name
- Example group notification:
```
⚠️ In 30 minutes: Multiple news events!

🔴 High Impact:
• 14:30 | USD | Non-Farm Payrolls
• 14:30 | EUR | ECB Interest Rate Decision

🟠 Medium Impact:
• 14:30 | GBP | BOE Meeting Minutes
```

### 3. Deduplication
- Each notification is tracked to prevent duplicates
- Notifications are cleaned up after 24 hours
- Group notifications use a hash of event IDs for deduplication

## Testing

The notification system has been tested with:
- ✅ Notification deduplication
- ✅ Group notification formatting
- ✅ Event grouping by time
- ✅ Notification timing logic

## Configuration

Your notification settings remain the same:
- **Notification timing**: 30 minutes before events
- **Impact levels**: High, Medium, Low (as configured)
- **Enabled**: Yes

The system will now respect these settings and send notifications exactly once at the specified time, with group events combined into single notifications.
