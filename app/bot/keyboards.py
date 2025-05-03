
"""
Telegram bot keyboards and inline markup.
"""

from datetime import datetime, timedelta
from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton
from app.config import config

class BotKeyboards:
    """Class for generating Telegram bot keyboards."""
    
    @staticmethod
    def generate_calendar(year: int, month: int) -> InlineKeyboardMarkup:
        """
        Generate calendar keyboard for date selection.
        
        Args:
            year: Year for the calendar
            month: Month for the calendar
            
        Returns:
            InlineKeyboardMarkup with calendar
        """
        markup = InlineKeyboardMarkup(row_width=7)
        
        # Add day headers
        markup.row(*[
            InlineKeyboardButton(d, callback_data="IGNORE") 
            for d in ["Mo", "Tu", "We", "Th", "Fr", "Sa", "Su"]
        ])
        
        # Calculate first day and number of days in month
        first_day = datetime(year, month, 1)
        start_day = first_day.weekday()  # Monday is 0
        
        # Get last day of month
        if month == 12:
            next_month = first_day.replace(year=year + 1, month=1)
        else:
            next_month = first_day.replace(month=month + 1)
        
        last_day = (next_month - timedelta(days=1)).day
        
        # Build calendar days
        days = []
        
        # Add empty cells for days before the first day of month
        for _ in range(start_day):
            days.append(InlineKeyboardButton(" ", callback_data="IGNORE"))
        
        # Add days of the month
        for day in range(1, last_day + 1):
            date_str = f"{year}-{month:02d}-{day:02d}"
            days.append(InlineKeyboardButton(str(day), callback_data=f"DAY_{date_str}"))
        
        # Fill remaining cells to complete the week
        while len(days) % 7 != 0:
            days.append(InlineKeyboardButton(" ", callback_data="IGNORE"))
        
        # Add days to markup in rows of 7
        for i in range(0, len(days), 7):
            markup.row(*days[i:i+7])
        
        # Add navigation buttons
        nav_buttons = [
            InlineKeyboardButton("<", callback_data=f"PREV_{year}-{month}"),
            InlineKeyboardButton(f"{first_day.strftime('%B')} {year}", callback_data="IGNORE"),
            InlineKeyboardButton(">", callback_data=f"NEXT_{year}-{month}")
        ]
        markup.row(*nav_buttons)
        
        # Add "Today" button
        today_str = datetime.today().strftime('%Y-%m-%d')
        markup.add(InlineKeyboardButton("📍 Today", callback_data=f"DAY_{today_str}"))
        
        return markup
    
    @staticmethod
    def generate_currency_selection(selected_currencies=None) -> InlineKeyboardMarkup:
        """
        Generate currency selection keyboard with multiple selection support.
        
        Args:
            selected_currencies: List of currently selected currency codes
            
        Returns:
            InlineKeyboardMarkup with currency options
        """
        if selected_currencies is None:
            selected_currencies = []
            
        markup = InlineKeyboardMarkup(row_width=3)
        
        # ИСПРАВЛЕНИЕ 4: Реализовать множественный выбор валют для уведомлений
        # Add currency buttons with checkmarks for selected ones
        currency_buttons = []
        for currency in config.AVAILABLE_CURRENCIES:
            # Add checkmark if currency is selected
            display_text = f"✅ {currency}" if currency in selected_currencies else currency
            currency_buttons.append(
                InlineKeyboardButton(display_text, callback_data=f"CURRENCY_TOGGLE_{currency}")
            )
        
        # Add buttons in rows of 3
        for i in range(0, len(currency_buttons), 3):
            markup.row(*currency_buttons[i:i+3])
        
        # Add control buttons
        markup.row(
            InlineKeyboardButton("🔄 Select All", callback_data="CURRENCY_SELECT_ALL"),
            InlineKeyboardButton("❌ Clear All", callback_data="CURRENCY_CLEAR_ALL")
        )
        markup.add(InlineKeyboardButton("✅ Done", callback_data="CURRENCY_DONE"))
        
        return markup
    
    @staticmethod
    def generate_impact_selection() -> InlineKeyboardMarkup:
        """
        Generate impact level selection keyboard.
        
        Returns:
            InlineKeyboardMarkup with impact level options
        """
        markup = InlineKeyboardMarkup()
        
        markup.row(
            InlineKeyboardButton("🔴 High Only", callback_data="IMPACT_HIGH"),
            InlineKeyboardButton("🟠 Medium + High", callback_data="IMPACT_MEDIUM")
        )
        markup.row(
            InlineKeyboardButton("🟡 Low + Medium + High", callback_data="IMPACT_LOW")
        )
        
        return markup
    
    @staticmethod
    def generate_main_menu() -> InlineKeyboardMarkup:
        """
        Generate main menu keyboard.
        
        Returns:
            InlineKeyboardMarkup with main menu options
        """
        markup = InlineKeyboardMarkup()
        
        markup.row(
            InlineKeyboardButton("📅 Today's News", callback_data="TODAY_NEWS"),
            InlineKeyboardButton("🗓️ Calendar", callback_data="SHOW_CALENDAR")
        )
        markup.row(
            InlineKeyboardButton("⚙️ Settings", callback_data="SETTINGS"),
            InlineKeyboardButton("❓ Help", callback_data="HELP")
        )
        
        return markup
    
    @staticmethod
    def generate_settings_menu() -> InlineKeyboardMarkup:
        """
        Generate settings menu keyboard.
        
        Returns:
            InlineKeyboardMarkup with settings options
        """
        markup = InlineKeyboardMarkup()
        
        markup.row(
            InlineKeyboardButton("💱 Currency Preferences", callback_data="CURRENCY_SETTINGS")
        )
        markup.row(
            InlineKeyboardButton("🔙 Back to Main Menu", callback_data="MAIN_MENU")
        )
        
        return markup
