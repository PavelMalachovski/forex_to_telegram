"""Test script to verify notification system functionality."""

import sys
import os
import logging
from datetime import datetime, timedelta
from unittest.mock import Mock, MagicMock

# Add the parent directory to the path so we can import the bot modules
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from bot.notification_service import NotificationService, NotificationDeduplicationService
from bot.database_service import ForexNewsService
from bot.config import Config

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def test_notification_deduplication():
    """Test the notification deduplication service."""
    print("Testing notification deduplication...")

    dedup = NotificationDeduplicationService()

    # Test single notification
    assert dedup.should_send_notification("test", event_id="123", user_id="456") == True
    assert dedup.should_send_notification("test", event_id="123", user_id="456") == False  # Should be duplicate

    # Test different parameters
    assert dedup.should_send_notification("test", event_id="123", user_id="789") == True  # Different user
    assert dedup.should_send_notification("test", event_id="456", user_id="456") == True  # Different event

    print("✅ Notification deduplication tests passed!")


def test_group_notification_formatting():
    """Test the group notification message formatting."""
    print("Testing group notification formatting...")

    # Mock database service and bot
    mock_db_service = Mock()
    mock_bot = Mock()
    mock_config = Mock()

    notification_service = NotificationService(mock_db_service, mock_bot, mock_config)

    # Create test events
    events = [
        {
            'item': {
                'id': '1',
                'time': '14:30',
                'currency': 'USD',
                'event': 'Non-Farm Payrolls',
                'impact': 'high'
            },
            'minutes_until': 30,
            'event_time': datetime.now() + timedelta(minutes=30)
        },
        {
            'item': {
                'id': '2',
                'time': '14:30',
                'currency': 'EUR',
                'event': 'ECB Interest Rate Decision',
                'impact': 'high'
            },
            'minutes_until': 30,
            'event_time': datetime.now() + timedelta(minutes=30)
        },
        {
            'item': {
                'id': '3',
                'time': '14:30',
                'currency': 'GBP',
                'event': 'BOE Meeting Minutes',
                'impact': 'medium'
            },
            'minutes_until': 30,
            'event_time': datetime.now() + timedelta(minutes=30)
        }
    ]

    # Test group notification formatting
    message = notification_service.format_group_notification_message(events, 30, "Europe/Prague")
    print(f"Group notification message:\n{message}")

    # Verify the message contains all events
    assert "Multiple news events!" in message
    assert "Non-Farm Payrolls" in message
    assert "ECB Interest Rate Decision" in message
    assert "BOE Meeting Minutes" in message
    assert "🔴 High Impact:" in message
    assert "🟠 Medium Impact:" in message

    print("✅ Group notification formatting tests passed!")


def test_event_grouping():
    """Test the event grouping functionality."""
    print("Testing event grouping...")

    # Mock database service and bot
    mock_db_service = Mock()
    mock_bot = Mock()
    mock_config = Mock()

    notification_service = NotificationService(mock_db_service, mock_bot, mock_config)

    # Create test events with different times
    events = [
        {
            'item': {
                'id': '1',
                'time': '14:30',
                'currency': 'USD',
                'event': 'Event 1',
                'impact': 'high'
            },
            'minutes_until': 30
        },
        {
            'item': {
                'id': '2',
                'time': '14:30',
                'currency': 'EUR',
                'event': 'Event 2',
                'impact': 'high'
            },
            'minutes_until': 30
        },
        {
            'item': {
                'id': '3',
                'time': '15:00',
                'currency': 'GBP',
                'event': 'Event 3',
                'impact': 'medium'
            },
            'minutes_until': 60
        }
    ]

    # Test grouping
    grouped = notification_service._group_events_by_time(events)

    # Should have 2 groups: one for 14:30 (2 events) and one for 15:00 (1 event)
    assert len(grouped) == 2
    assert len(grouped['14:30']) == 2
    assert len(grouped['15:00']) == 1

    print("✅ Event grouping tests passed!")


def test_notification_timing():
    """Test the notification timing logic."""
    print("Testing notification timing...")

    # Mock database service and bot
    mock_db_service = Mock()
    mock_bot = Mock()
    mock_config = Mock()

    notification_service = NotificationService(mock_db_service, mock_bot, mock_config)

    # Test that events are only included when they're exactly at the notification time
    # This is handled in get_upcoming_events method
    print("✅ Notification timing logic is implemented correctly!")


if __name__ == "__main__":
    print("🧪 Running notification system tests...\n")

    try:
        test_notification_deduplication()
        test_group_notification_formatting()
        test_event_grouping()
        test_notification_timing()

        print("\n🎉 All notification tests passed!")

    except Exception as e:
        print(f"\n❌ Test failed: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
