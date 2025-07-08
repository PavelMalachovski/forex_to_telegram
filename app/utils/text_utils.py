
"""Text utilities for formatting and processing text content."""

from datetime import datetime, date, time
from typing import Dict, List, Optional, Any, Union
from loguru import logger


def format_event_time(event_time: Optional[time]) -> str:
    """
    Format event time for display.
    
    Args:
        event_time: Time object or None
        
    Returns:
        Formatted time string
    """
    if not event_time:
        return "All Day"
    
    return event_time.strftime("%H:%M")


def format_event_date(event_date: date) -> str:
    """
    Format event date for display.
    
    Args:
        event_date: Date object
        
    Returns:
        Formatted date string
    """
    return event_date.strftime("%Y-%m-%d")


def format_currency_code(currency_code: Optional[str]) -> str:
    """
    Format currency code for display.
    
    Args:
        currency_code: Currency code or None
        
    Returns:
        Formatted currency code
    """
    if not currency_code:
        return "N/A"
    
    return currency_code.upper()


def format_impact_level(impact_code: Optional[str]) -> str:
    """
    Format impact level for display.
    
    Args:
        impact_code: Impact level code
        
    Returns:
        Formatted impact level with emoji
    """
    if not impact_code:
        return "❓ Unknown"
    
    impact_map = {
        "LOW": "🟢 Low",
        "MEDIUM": "🟡 Medium", 
        "HIGH": "🔴 High"
    }
    
    return impact_map.get(impact_code.upper(), f"❓ {impact_code}")


def truncate_text(text: str, max_length: int = 100, suffix: str = "...") -> str:
    """
    Truncate text to specified length.
    
    Args:
        text: Text to truncate
        max_length: Maximum length
        suffix: Suffix to add if truncated
        
    Returns:
        Truncated text
    """
    if len(text) <= max_length:
        return text
    
    return text[:max_length - len(suffix)] + suffix


def escape_markdown(text: str) -> str:
    """
    Escape markdown special characters.
    
    Args:
        text: Text to escape
        
    Returns:
        Escaped text
    """
    special_chars = ['_', '*', '[', ']', '(', ')', '~', '`', '>', '#', '+', '-', '=', '|', '{', '}', '.', '!']
    
    for char in special_chars:
        text = text.replace(char, f'\\{char}')
    
    return text


def format_news_event_message(event: Any) -> str:
    """
    Format a news event for Telegram message.
    
    Args:
        event: NewsEvent object
        
    Returns:
        Formatted message string
    """
    try:
        # Basic event info
        date_str = format_event_date(event.event_date)
        time_str = format_event_time(event.event_time)
        currency = format_currency_code(event.currency.code if event.currency else None)
        impact = format_impact_level(event.impact_level.code if event.impact_level else None)
        
        # Build message
        message_parts = [
            f"📅 *{date_str}* at *{time_str}*",
            f"💱 Currency: *{currency}*",
            f"📊 Impact: {impact}",
            f"📰 Event: *{escape_markdown(event.event_name)}*"
        ]
        
        # Add forecast/previous/actual if available
        if event.forecast:
            message_parts.append(f"🔮 Forecast: `{event.forecast}`")
        
        if event.previous:
            message_parts.append(f"📈 Previous: `{event.previous}`")
        
        if event.actual:
            message_parts.append(f"✅ Actual: `{event.actual}`")
        
        return "\n".join(message_parts)
        
    except Exception as e:
        logger.error(f"Error formatting news event message: {e}")
        return f"📰 {event.event_name} - {event.event_date}"


def format_daily_summary(events: List[Any], target_date: date) -> str:
    """
    Format daily summary of events.
    
    Args:
        events: List of NewsEvent objects
        target_date: Date for the summary
        
    Returns:
        Formatted summary message
    """
    if not events:
        return f"📅 *Daily Summary for {format_event_date(target_date)}*\n\nNo economic events scheduled for today."
    
    # Group events by impact level
    grouped_events: Dict[str, List[Any]] = {
        "HIGH": [],
        "MEDIUM": [],
        "LOW": []
    }
    
    for event in events:
        impact_code = event.impact_level.code if event.impact_level else "LOW"
        if impact_code in grouped_events:
            grouped_events[impact_code].append(event)
        else:
            grouped_events["LOW"].append(event)
    
    # Build summary message
    message_parts = [
        f"📅 *Daily Summary for {format_event_date(target_date)}*",
        f"📊 Total Events: {len(events)}\n"
    ]
    
    # Add events by impact level
    for impact_level in ["HIGH", "MEDIUM", "LOW"]:
        level_events = grouped_events[impact_level]
        if level_events:
            impact_emoji = {"HIGH": "🔴", "MEDIUM": "🟡", "LOW": "🟢"}[impact_level]
            message_parts.append(f"{impact_emoji} *{impact_level} Impact ({len(level_events)} events):*")
            
            for event in level_events:
                time_str = format_event_time(event.event_time)
                currency = format_currency_code(event.currency.code if event.currency else None)
                event_name = truncate_text(event.event_name, 50)
                
                message_parts.append(f"  • {time_str} | {currency} | {event_name}")
            
            message_parts.append("")  # Empty line
    
    return "\n".join(message_parts)


def format_currency_events(events: List[Any], currency_code: str) -> str:
    """
    Format events for a specific currency.
    
    Args:
        events: List of NewsEvent objects
        currency_code: Currency code
        
    Returns:
        Formatted message
    """
    if not events:
        return f"💱 *{currency_code} Events*\n\nNo events found for {currency_code}."
    
    message_parts = [
        f"💱 *{currency_code} Events ({len(events)} total)*\n"
    ]
    
    for event in events:
        date_str = format_event_date(event.event_date)
        time_str = format_event_time(event.event_time)
        impact = format_impact_level(event.impact_level.code if event.impact_level else None)
        event_name = truncate_text(event.event_name, 60)
        
        message_parts.append(f"📅 {date_str} {time_str}")
        message_parts.append(f"📊 {impact}")
        message_parts.append(f"📰 {event_name}\n")
    
    return "\n".join(message_parts)


def format_user_stats(stats: Dict[str, Any]) -> str:
    """
    Format user statistics.
    
    Args:
        stats: Dictionary with user statistics
        
    Returns:
        Formatted statistics message
    """
    message_parts = [
        "📊 *User Statistics*\n",
        f"👥 Total Users: {stats.get('total_users', 0)}",
        f"✅ Active Users: {stats.get('active_users', 0)}",
        f"🔔 Users with Notifications: {stats.get('users_with_notifications', 0)}",
        f"📱 Last 24h Activity: {stats.get('recent_activity', 0)}"
    ]
    
    return "\n".join(message_parts)


def format_system_stats(stats: Dict[str, Any]) -> str:
    """
    Format system statistics.
    
    Args:
        stats: Dictionary with system statistics
        
    Returns:
        Formatted statistics message
    """
    message_parts = [
        "🖥️ *System Statistics*\n",
        f"📰 Total Events: {stats.get('total_events', 0)}",
        f"📅 Today's Events: {stats.get('today_events', 0)}",
        f"🔄 Last Scraping: {stats.get('last_scraping', 'Never')}",
        f"✅ System Health: {stats.get('health_status', 'Unknown')}"
    ]
    
    return "\n".join(message_parts)


def clean_text(text: str) -> str:
    """
    Clean and normalize text.
    
    Args:
        text: Text to clean
        
    Returns:
        Cleaned text
    """
    if not text:
        return ""
    
    # Remove extra whitespace
    text = " ".join(text.split())
    
    # Remove special characters that might cause issues
    text = text.replace('\x00', '')  # Remove null bytes
    text = text.replace('\r', '')    # Remove carriage returns
    
    return text.strip()


def format_error_message(error: str, context: str = "") -> str:
    """
    Format error message for user display.
    
    Args:
        error: Error message
        context: Additional context
        
    Returns:
        Formatted error message
    """
    message_parts = ["❌ *Error*"]
    
    if context:
        message_parts.append(f"Context: {context}")
    
    message_parts.append(f"Details: {clean_text(error)}")
    
    return "\n".join(message_parts)


def format_success_message(message: str, details: str = "") -> str:
    """
    Format success message for user display.
    
    Args:
        message: Success message
        details: Additional details
        
    Returns:
        Formatted success message
    """
    message_parts = [f"✅ {message}"]
    
    if details:
        message_parts.append(f"Details: {details}")
    
    return "\n".join(message_parts)
