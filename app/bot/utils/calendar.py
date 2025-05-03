

"""
Inline calendar utility for Telegram bot using telebot.
"""

import calendar
from datetime import datetime, date, timedelta
from typing import Tuple, Optional
from telebot import types


class InlineCalendar:
    """Simple inline calendar for date selection."""
    
    def __init__(self):
        # ИСПРАВЛЕНИЕ 5: Перевести календарь на английский язык
        self.months = [
            "January", "February", "March", "April", "May", "June",
            "July", "August", "September", "October", "November", "December"
        ]
        self.weekdays = ["Mo", "Tu", "We", "Th", "Fr", "Sa", "Su"]
    
    def create_calendar(self, year: int = None, month: int = None) -> types.InlineKeyboardMarkup:
        """
        Create calendar markup for given year and month.
        
        Args:
            year: Year to display (default: current year)
            month: Month to display (default: current month)
            
        Returns:
            InlineKeyboardMarkup with calendar
        """
        now = datetime.now()
        if year is None:
            year = now.year
        if month is None:
            month = now.month
        
        markup = types.InlineKeyboardMarkup(row_width=7)
        
        # Header with month and year
        header_text = f"{self.months[month - 1]} {year}"
        markup.add(types.InlineKeyboardButton(header_text, callback_data="calendar_ignore"))
        
        # Navigation buttons
        prev_month = month - 1 if month > 1 else 12
        prev_year = year if month > 1 else year - 1
        next_month = month + 1 if month < 12 else 1
        next_year = year if month < 12 else year + 1
        
        markup.add(
            types.InlineKeyboardButton("◀", callback_data=f"calendar_prev_{prev_year}_{prev_month}"),
            types.InlineKeyboardButton("Today", callback_data=f"calendar_today"),
            types.InlineKeyboardButton("▶", callback_data=f"calendar_next_{next_year}_{next_month}")
        )
        
        # Weekday headers
        weekday_buttons = [types.InlineKeyboardButton(day, callback_data="calendar_ignore") for day in self.weekdays]
        markup.add(*weekday_buttons)
        
        # Calendar days
        cal = calendar.monthcalendar(year, month)
        today = datetime.now().date()
        
        for week in cal:
            week_buttons = []
            for day in week:
                if day == 0:
                    # Empty cell
                    week_buttons.append(types.InlineKeyboardButton(" ", callback_data="calendar_ignore"))
                else:
                    current_date = date(year, month, day)
                    
                    # Mark today with special formatting
                    if current_date == today:
                        day_text = f"[{day}]"
                    else:
                        day_text = str(day)
                    
                    # Allow selection of all dates (past and future)
                    callback_data = f"calendar_select_{year}_{month}_{day}"
                    week_buttons.append(types.InlineKeyboardButton(day_text, callback_data=callback_data))
            
            markup.add(*week_buttons)
        
        # Close button
        markup.add(types.InlineKeyboardButton("❌ Close", callback_data="calendar_close"))
        
        return markup
    
    def process_callback(self, callback_data: str) -> Tuple[str, Optional[date], Optional[Tuple[int, int]]]:
        """
        Process calendar callback data.
        
        Args:
            callback_data: Callback data from button press
            
        Returns:
            Tuple of (action, selected_date, navigation_data)
            - action: 'select', 'prev', 'next', 'today', 'close', 'ignore'
            - selected_date: Selected date if action is 'select' or 'today'
            - navigation_data: (year, month) if action is 'prev' or 'next'
        """
        if not callback_data.startswith("calendar_"):
            return "ignore", None, None
        
        parts = callback_data.split("_")
        action = parts[1]
        
        if action == "select":
            year, month, day = int(parts[2]), int(parts[3]), int(parts[4])
            selected_date = date(year, month, day)
            return "select", selected_date, None
        
        elif action == "prev" or action == "next":
            year, month = int(parts[2]), int(parts[3])
            return action, None, (year, month)
        
        elif action == "today":
            return "today", datetime.now().date(), None
        
        elif action == "close":
            return "close", None, None
        
        else:  # ignore
            return "ignore", None, None
    
    def create_date_selection_message(self) -> str:
        """Create message text for date selection."""
        return "📅 Select a date to search for news:"


# Convenience functions
def create_calendar_markup(year: int = None, month: int = None) -> types.InlineKeyboardMarkup:
    """Create calendar markup."""
    calendar_obj = InlineCalendar()
    return calendar_obj.create_calendar(year, month)


def process_calendar_callback(callback_data: str) -> Tuple[str, Optional[date], Optional[Tuple[int, int]]]:
    """Process calendar callback."""
    calendar_obj = InlineCalendar()
    return calendar_obj.process_callback(callback_data)


def get_date_selection_message() -> str:
    """Get date selection message."""
    calendar_obj = InlineCalendar()
    return calendar_obj.create_date_selection_message()
