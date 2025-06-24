"""
Timezone utilities for consistent time handling across the application.
"""

from datetime import datetime
import pytz
from app.config import config

def get_local_timezone():
    """Get the configured local timezone."""
    return pytz.timezone(config.TIMEZONE)

def get_current_time():
    """Get current time in the configured timezone."""
    local_tz = get_local_timezone()
    return datetime.now(local_tz)

def get_current_time_iso():
    """Get current time in ISO format with timezone."""
    return get_current_time().isoformat()

def format_time_for_display(dt):
    """Format datetime for user display."""
    if dt.tzinfo is None:
        # If naive datetime, assume it's in local timezone
        local_tz = get_local_timezone()
        dt = local_tz.localize(dt)
    else:
        # Convert to local timezone
        local_tz = get_local_timezone()
        dt = dt.astimezone(local_tz)
    
    return dt.strftime("%H:%M")

def format_datetime_for_display(dt):
    """Format datetime with date for user display."""
    if dt.tzinfo is None:
        # If naive datetime, assume it's in local timezone
        local_tz = get_local_timezone()
        dt = local_tz.localize(dt)
    else:
        # Convert to local timezone
        local_tz = get_local_timezone()
        dt = dt.astimezone(local_tz)
    
    return dt.strftime("%Y-%m-%d %H:%M")

def convert_utc_to_local(utc_dt):
    """Convert UTC datetime to local timezone."""
    if utc_dt.tzinfo is None:
        utc_dt = pytz.UTC.localize(utc_dt)
    
    local_tz = get_local_timezone()
    return utc_dt.astimezone(local_tz)
