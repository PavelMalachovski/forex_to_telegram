
"""Calendar utilities for the Telegram bot."""

import calendar
from datetime import datetime, date, timedelta
from typing import Optional, Tuple, Dict, Any
from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton


def create_calendar(
    year: Optional[int] = None,
    month: Optional[int] = None,
    selected_date: Optional[date] = None
) -> InlineKeyboardMarkup:
    """
    Create a calendar keyboard for date selection.
    
    Args:
        year: Year to display (defaults to current year)
        month: Month to display (defaults to current month)
        selected_date: Currently selected date
        
    Returns:
        InlineKeyboardMarkup with calendar
    """
    now = datetime.now()
    if year is None:
        year = now.year
    if month is None:
        month = now.month
    
    # Create calendar
    cal = calendar.monthcalendar(year, month)
    
    # Create keyboard
    keyboard = InlineKeyboardMarkup()
    
    # Header with month/year and navigation
    month_name = calendar.month_name[month]
    header_text = f"{month_name} {year}"
    
    # Navigation row
    nav_row = []
    
    # Previous month button
    prev_month = month - 1
    prev_year = year
    if prev_month < 1:
        prev_month = 12
        prev_year -= 1
    
    nav_row.append(InlineKeyboardButton(
        "◀️",
        callback_data=f"calendar_nav_{prev_year}_{prev_month}"
    ))
    
    # Current month/year (non-clickable)
    nav_row.append(InlineKeyboardButton(
        header_text,
        callback_data="calendar_ignore"
    ))
    
    # Next month button
    next_month = month + 1
    next_year = year
    if next_month > 12:
        next_month = 1
        next_year += 1
    
    nav_row.append(InlineKeyboardButton(
        "▶️",
        callback_data=f"calendar_nav_{next_year}_{next_month}"
    ))
    
    keyboard.row(*nav_row)
    
    # Days of week header
    days_header = []
    for day in ['Mo', 'Tu', 'We', 'Th', 'Fr', 'Sa', 'Su']:
        days_header.append(InlineKeyboardButton(
            day,
            callback_data="calendar_ignore"
        ))
    keyboard.row(*days_header)
    
    # Calendar days
    for week in cal:
        week_buttons = []
        for day in week:
            if day == 0:
                # Empty day
                week_buttons.append(InlineKeyboardButton(
                    " ",
                    callback_data="calendar_ignore"
                ))
            else:
                # Regular day
                day_date = date(year, month, day)
                
                # Check if this is the selected date
                if selected_date and day_date == selected_date:
                    button_text = f"[{day}]"
                else:
                    button_text = str(day)
                
                # Check if date is in the past
                if day_date < date.today():
                    # Past date - make it non-clickable
                    week_buttons.append(InlineKeyboardButton(
                        f"~{button_text}~",
                        callback_data="calendar_ignore"
                    ))
                else:
                    # Future or today - clickable
                    week_buttons.append(InlineKeyboardButton(
                        button_text,
                        callback_data=f"calendar_select_{year}_{month}_{day}"
                    ))
        
        keyboard.row(*week_buttons)
    
    # Action buttons
    action_row = []
    
    # Today button
    today = date.today()
    action_row.append(InlineKeyboardButton(
        "📅 Today",
        callback_data=f"calendar_select_{today.year}_{today.month}_{today.day}"
    ))
    
    # Cancel button
    action_row.append(InlineKeyboardButton(
        "❌ Cancel",
        callback_data="calendar_cancel"
    ))
    
    keyboard.row(*action_row)
    
    return keyboard


def process_calendar_callback(callback_data: str) -> Tuple[str, Optional[date], Optional[Dict[str, Any]]]:
    """
    Process calendar callback data.
    
    Args:
        callback_data: Callback data from the button
        
    Returns:
        Tuple of (action, selected_date, navigation_data)
    """
    parts = callback_data.split('_')
    
    if len(parts) < 2:
        return "ignore", None, None
    
    action = parts[1]
    
    if action == "ignore":
        return "ignore", None, None
    
    elif action == "nav":
        # Navigation to different month
        if len(parts) >= 4:
            try:
                year = int(parts[2])
                month = int(parts[3])
                return "navigate", None, {"year": year, "month": month}
            except ValueError:
                return "ignore", None, None
        return "ignore", None, None
    
    elif action == "select":
        # Date selection
        if len(parts) >= 5:
            try:
                year = int(parts[2])
                month = int(parts[3])
                day = int(parts[4])
                selected_date = date(year, month, day)
                return "select", selected_date, None
            except (ValueError, TypeError):
                return "ignore", None, None
        return "ignore", None, None
    
    elif action == "cancel":
        return "cancel", None, None
    
    else:
        return "ignore", None, None


def get_week_dates(target_date: date) -> Tuple[date, date]:
    """
    Get start and end dates of the week containing the target date.
    
    Args:
        target_date: Date to find the week for
        
    Returns:
        Tuple of (week_start, week_end)
    """
    # Monday is 0, Sunday is 6
    days_since_monday = target_date.weekday()
    
    week_start = target_date - timedelta(days=days_since_monday)
    week_end = week_start + timedelta(days=6)
    
    return week_start, week_end


def get_month_dates(target_date: date) -> Tuple[date, date]:
    """
    Get start and end dates of the month containing the target date.
    
    Args:
        target_date: Date to find the month for
        
    Returns:
        Tuple of (month_start, month_end)
    """
    month_start = target_date.replace(day=1)
    
    # Get last day of month
    if target_date.month == 12:
        next_month = target_date.replace(year=target_date.year + 1, month=1, day=1)
    else:
        next_month = target_date.replace(month=target_date.month + 1, day=1)
    
    month_end = next_month - timedelta(days=1)
    
    return month_start, month_end


def format_date_range(start_date: date, end_date: date) -> str:
    """
    Format a date range for display.
    
    Args:
        start_date: Start date
        end_date: End date
        
    Returns:
        Formatted date range string
    """
    if start_date == end_date:
        return start_date.strftime("%Y-%m-%d")
    
    if start_date.year == end_date.year:
        if start_date.month == end_date.month:
            return f"{start_date.strftime('%Y-%m-%d')} to {end_date.strftime('%d')}"
        else:
            return f"{start_date.strftime('%Y-%m-%d')} to {end_date.strftime('%m-%d')}"
    else:
        return f"{start_date.strftime('%Y-%m-%d')} to {end_date.strftime('%Y-%m-%d')}"


def is_weekend(target_date: date) -> bool:
    """
    Check if the date is a weekend.
    
    Args:
        target_date: Date to check
        
    Returns:
        True if weekend (Saturday or Sunday)
    """
    return target_date.weekday() >= 5  # Saturday = 5, Sunday = 6


def get_business_days(start_date: date, end_date: date) -> int:
    """
    Get number of business days between two dates.
    
    Args:
        start_date: Start date
        end_date: End date
        
    Returns:
        Number of business days
    """
    business_days = 0
    current_date = start_date
    
    while current_date <= end_date:
        if not is_weekend(current_date):
            business_days += 1
        current_date += timedelta(days=1)
    
    return business_days


def get_next_business_day(target_date: date) -> date:
    """
    Get the next business day after the target date.
    
    Args:
        target_date: Starting date
        
    Returns:
        Next business day
    """
    next_day = target_date + timedelta(days=1)
    
    while is_weekend(next_day):
        next_day += timedelta(days=1)
    
    return next_day


def get_previous_business_day(target_date: date) -> date:
    """
    Get the previous business day before the target date.
    
    Args:
        target_date: Starting date
        
    Returns:
        Previous business day
    """
    prev_day = target_date - timedelta(days=1)
    
    while is_weekend(prev_day):
        prev_day -= timedelta(days=1)
    
    return prev_day
