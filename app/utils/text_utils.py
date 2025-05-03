


"""
Text utility functions without external dependencies.
"""

import re
from typing import List
from datetime import datetime
from app.database.models import NewsEvent


def escape_markdown_v2(text: str) -> str:
    """
    Escape special characters for MarkdownV2.
    
    Args:
        text: Text to escape
        
    Returns:
        Escaped text safe for MarkdownV2
    """
    if not text or text.strip() == "":
        return "N/A"
    
    # ИСПРАВЛЕНИЕ 1 и 5: Исправить экранирование символов '.' и '=' в MarkdownV2
    # Добавляем точку и знак равенства в список символов для экранирования
    special_chars = r'([_.*\[\]()~`>#+=|{}.!\\=-])'
    escaped_text = re.sub(special_chars, r'\\\1', str(text))
    
    return escaped_text


def get_impact_emoji_and_color(impact_level: str) -> tuple:
    """
    Get emoji and color for impact level.
    
    Args:
        impact_level: Impact level string
        
    Returns:
        Tuple of (emoji, color_name)
    """
    impact_map = {
        "HIGH": ("🔴", "red"),
        "MEDIUM": ("🟠", "orange"), 
        "LOW": ("🟡", "yellow"),
        "NON_ECONOMIC": ("⚪", "gray")
    }
    return impact_map.get(impact_level.upper(), ("⚪", "gray"))

def get_currency_symbol(currency_code: str) -> str:
    """
    Get currency symbol from currency code.
    
    Args:
        currency_code: Currency code (e.g., 'USD', 'EUR')
        
    Returns:
        Currency symbol
    """
    currency_symbols = {
        "USD": "$",
        "EUR": "€", 
        "GBP": "£",
        "JPY": "¥",
        "CHF": "₣",
        "CAD": "C$",
        "AUD": "A$",
        "NZD": "NZ$",
        "CNY": "¥",
        "SEK": "kr",
        "NOK": "kr",
        "DKK": "kr",
        "PLN": "zł",
        "CZK": "Kč",
        "HUF": "Ft",
        "RUB": "₽",
        "TRY": "₺",
        "ZAR": "R",
        "BRL": "R$",
        "MXN": "$",
        "INR": "₹",
        "KRW": "₩",
        "SGD": "S$",
        "HKD": "HK$"
    }
    return currency_symbols.get(currency_code.upper(), currency_code)

def format_news_message(news_events: List[NewsEvent], date_str: str, impact_level: str = "HIGH") -> str:
    """
    Format news events into a readable message.
    
    Args:
        news_events: List of NewsEvent objects
        date_str: Date string for the header
        impact_level: Impact level for the header
        
    Returns:
        Formatted message string
    """
    # Format the date for display
    try:
        formatted_date = datetime.strptime(date_str, '%Y-%m-%d').strftime('%d.%m.%Y')
        # Escape the formatted date for MarkdownV2 since it contains dots
        formatted_date = escape_markdown_v2(formatted_date)
    except ValueError:
        formatted_date = escape_markdown_v2(date_str)
    
    header = f"🗓️ Forex News for {formatted_date} \\(CET\\):\n"
    if impact_level != "HIGH":
        header += f"Impact Level: {escape_markdown_v2(impact_level)}\n"
    header += "\n"
    
    if not news_events:
        return header + f"✅ No news found for {escape_markdown_v2(date_str)} with impact: {escape_markdown_v2(impact_level)}\nPlease check the website for updates."
    
    # Group events by currency and time locally to avoid service dependency
    grouped_events = {}
    for event in news_events:
        # Create key from date, time, and currency
        event_date = event.event_date.strftime('%Y-%m-%d')
        event_time = event.event_time.strftime('%H:%M') if event.event_time else 'N/A'
        currency = event.currency.code if event.currency else 'Unknown'
        
        key = (event_date, event_time, currency)
        
        if key not in grouped_events:
            grouped_events[key] = []
        grouped_events[key].append(event)
    
    message_parts = [header]
    
    # Sort by time
    sorted_groups = sorted(grouped_events.items(), key=lambda x: (x[0][0], x[0][1]))
    
    for (event_date, event_time, currency), events in sorted_groups:
        # Check if this is a group event (more than one event)
        is_group_event = len(events) > 1
        group_prefix = "🔥 **GROUP EVENT\\!** 🔥\n" if is_group_event else ""
        
        # Combine event details
        event_names = [event.event_name for event in events]
        forecasts = [event.forecast or 'N/A' for event in events]
        previous_values = [event.previous_value or 'N/A' for event in events]
        actual_values = [event.actual_value or 'N/A' for event in events]
        
        # ИСПРАВЛЕНИЕ 2: Убрать ограничения на длину анализа ChatGPT
        # Используем полный анализ без сокращения
        analysis = events[0].analysis or "No analysis available"
        
        impact = events[0].impact_level.code if events[0].impact_level else "LOW"
        impact_emoji, _ = get_impact_emoji_and_color(impact)
        currency_symbol = get_currency_symbol(currency)
        
        part = group_prefix
        part += f"{impact_emoji} **Impact: {escape_markdown_v2(impact.upper())}**\n\n"
        part += f"⏰ Time: {event_time}\n"
        # ИСПРАВЛЕНИЕ 3: Добавить символы валют в отображение Currency
        part += f"💱 Currency: {currency_symbol} {currency}\n"
        part += f"📰 Events: {escape_markdown_v2(' & '.join(event_names))}\n"
        part += f"📈 Forecast: {escape_markdown_v2(' & '.join(forecasts))}\n"
        part += f"📊 Previous: {escape_markdown_v2(' & '.join(previous_values))}\n"
        part += f"🎯 Actual: {escape_markdown_v2(' & '.join(actual_values))}\n"
        part += f"🔍 Analysis: {escape_markdown_v2(analysis)}\n\n"
        part += f"{escape_markdown_v2('-' * 40)}\n\n"
        
        message_parts.append(part)
    
    return "".join(message_parts)


def format_time_string(time_obj) -> str:
    """
    Format time object to string.
    
    Args:
        time_obj: Time object to format
        
    Returns:
        Formatted time string
    """
    if hasattr(time_obj, 'strftime'):
        return time_obj.strftime('%H:%M')
    return str(time_obj)


def safe_get_text(element, default: str = "N/A") -> str:
    """
    Safely get text from an element.
    
    Args:
        element: Element to get text from
        default: Default value if element is None or empty
        
    Returns:
        Text content or default value
    """
    if element is None:
        return default
    
    text = element.text.strip() if hasattr(element, 'text') else str(element).strip()
    return text if text else default


def validate_date_string(date_str: str) -> bool:
    """
    Validate date string format.
    
    Args:
        date_str: Date string to validate
        
    Returns:
        True if valid, False otherwise
    """
    try:
        datetime.strptime(date_str, '%Y-%m-%d')
        return True
    except ValueError:
        return False


def validate_time_string(time_str: str) -> bool:
    """
    Validate time string format.
    
    Args:
        time_str: Time string to validate
        
    Returns:
        True if valid, False otherwise
    """
    try:
        datetime.strptime(time_str, '%H:%M')
        return True
    except ValueError:
        return False
