#!/usr/bin/env python3
"""Test script to verify webhook setup and new features."""

import pytest
import requests
import json
import sys
import hashlib

@pytest.fixture
def base_url():
    """Fixture to provide the base URL for testing."""
    return "https://forex-to-telegram-kf7u.onrender.com"

def _test_endpoint(base_url, endpoint, method='GET', data=None):
    """Test an endpoint and return the response."""
    url = f"{base_url}{endpoint}"
    try:
        if method == 'GET':
            response = requests.get(url, timeout=10)
        elif method == 'POST':
            response = requests.post(url, json=data, timeout=10)
        else:
            return {"error": f"Unsupported method: {method}"}

        return {
            "status_code": response.status_code,
            "data": response.json() if response.headers.get('content-type', '').startswith('application/json') else response.text
        }
    except requests.exceptions.RequestException as e:
        return {"error": str(e)}

def test_health_check(base_url):
    """Test basic health check endpoint."""
    result = _test_endpoint(base_url, "/health")
    assert result.get('status_code') == 200, f"Health check failed: {result}"
    print(f"Health check response: {json.dumps(result.get('data', {}), indent=2)}")

def test_bot_status(base_url):
    """Test bot status endpoint."""
    result = _test_endpoint(base_url, "/bot_status")
    assert result.get('status_code') == 200, f"Bot status failed: {result}"
    print(f"Bot status response: {json.dumps(result.get('data', {}), indent=2)}")

def test_webhook_debug(base_url):
    """Test webhook debug endpoint."""
    result = _test_endpoint(base_url, "/webhook_debug")
    assert result.get('status_code') == 200, f"Webhook debug failed: {result}"
    print(f"Webhook debug response: {json.dumps(result.get('data', {}), indent=2)}")

def test_notification_stats(base_url):
    """Test notification stats endpoint."""
    result = _test_endpoint(base_url, "/notification_stats")
    assert result.get('status_code') == 200, f"Notification stats failed: {result}"
    print(f"Notification stats response: {json.dumps(result.get('data', {}), indent=2)}")

def test_webhook_with_mock_data(base_url):
    """Test webhook with mock data that should work."""
    mock_data = {
        "update_id": 123456789,
        "message": {
            "message_id": 1,
            "from": {
                "id": 123456789,
                "is_bot": False,
                "first_name": "Test User",
                "username": "testuser"
            },
            "chat": {
                "id": 123456789,
                "type": "private",
                "title": None,
                "username": "testuser"
            },
            "date": 1234567890,
            "text": "/start"
        }
    }

    result = _test_endpoint(base_url, "/webhook", method='POST', data=mock_data)
    assert result.get('status_code') == 200, f"Webhook with mock data failed: {result}"
    print(f"Webhook mock data response: {json.dumps(result.get('data', {}), indent=2)}")

def test_group_webhook(base_url):
    """Test webhook with group event data."""
    group_data = {
        "update_id": 123456790,
        "message": {
            "message_id": 2,
            "from": {
                "id": 987654321,
                "is_bot": False,
                "first_name": "Group User",
                "username": "groupuser"
            },
            "chat": {
                "id": -1001234567890,
                "type": "group",
                "title": "Test Group",
                "username": None
            },
            "date": 1234567890,
            "text": "Hello from group!"
        }
    }

    result = _test_endpoint(base_url, "/webhook", method='POST', data=group_data)
    assert result.get('status_code') == 200, f"Group webhook failed: {result}"
    print(f"Group webhook response: {json.dumps(result.get('data', {}), indent=2)}")

def test_force_webhook_setup(base_url):
    """Test force webhook setup endpoint."""
    result = _test_endpoint(base_url, "/force_webhook_setup", method='POST')
    assert result.get('status_code') == 200, f"Force webhook setup failed: {result}"
    print(f"Force webhook setup response: {json.dumps(result.get('data', {}), indent=2)}")

# Keep the original main function for standalone execution
def main():
    """Main test function for standalone execution."""
    # Get the base URL from command line or use default
    if len(sys.argv) > 1:
        base_url = sys.argv[1]
    else:
        base_url = "https://forex-to-telegram-kf7u.onrender.com"  # Your actual URL

    print(f"🔍 Testing webhook setup for: {base_url}")
    print("=" * 60)

    # Test basic health check
    print("\n1. Testing health check...")
    health_result = _test_endpoint(base_url, "/health")
    print(f"Status: {health_result.get('status_code', 'Error')}")
    if 'data' in health_result:
        print(f"Response: {json.dumps(health_result['data'], indent=2)}")
    else:
        print(f"Error: {health_result.get('error', 'Unknown error')}")

    # Test bot status
    print("\n2. Testing bot status...")
    bot_status_result = _test_endpoint(base_url, "/bot_status")
    print(f"Status: {bot_status_result.get('status_code', 'Error')}")
    if 'data' in bot_status_result:
        print(f"Response: {json.dumps(bot_status_result['data'], indent=2)}")
    else:
        print(f"Error: {bot_status_result.get('error', 'Unknown error')}")

    # Test webhook debug
    print("\n3. Testing webhook debug...")
    webhook_debug_result = _test_endpoint(base_url, "/webhook_debug")
    print(f"Status: {webhook_debug_result.get('status_code', 'Error')}")
    if 'data' in webhook_debug_result:
        print(f"Response: {json.dumps(webhook_debug_result['data'], indent=2)}")
    else:
        print(f"Error: {webhook_debug_result.get('error', 'Unknown error')}")

    # Test notification stats
    print("\n4. Testing notification stats...")
    notification_stats_result = _test_endpoint(base_url, "/notification_stats")
    print(f"Status: {notification_stats_result.get('status_code', 'Error')}")
    if 'data' in notification_stats_result:
        print(f"Response: {json.dumps(notification_stats_result['data'], indent=2)}")
    else:
        print(f"Error: {notification_stats_result.get('error', 'Unknown error')}")

    # Test webhook with mock data
    print("\n5. Testing webhook with mock data...")
    webhook_result = test_webhook_with_mock_data(base_url)
    print(f"Status: {webhook_result.get('status_code', 'Error')}")
    if 'data' in webhook_result:
        print(f"Response: {json.dumps(webhook_result['data'], indent=2)}")
    else:
        print(f"Error: {webhook_result.get('error', 'Unknown error')}")

    # Test group webhook
    print("\n6. Testing group webhook...")
    group_result = test_group_webhook(base_url)
    print(f"Status: {group_result.get('status_code', 'Error')}")
    if 'data' in group_result:
        print(f"Response: {json.dumps(group_result['data'], indent=2)}")
    else:
        print(f"Error: {group_result.get('error', 'Unknown error')}")

    # Test force webhook setup
    print("\n7. Testing force webhook setup...")
    force_setup_result = _test_endpoint(base_url, "/force_webhook_setup", method='POST')
    print(f"Status: {force_setup_result.get('status_code', 'Error')}")
    if 'data' in force_setup_result:
        print(f"Response: {json.dumps(force_setup_result['data'], indent=2)}")
    else:
        print(f"Error: {force_setup_result.get('error', 'Unknown error')}")

    print("\n" + "=" * 60)
    print("✅ Testing completed!")
    print("\n📋 Summary:")
    print("- Health check should show all components healthy")
    print("- Bot status should show webhook configuration")
    print("- Webhook debug should show current webhook info")
    print("- Notification stats should show deduplication status")
    print("- Webhook tests should process messages without User model errors")
    print("- Group webhook should handle group events properly")

if __name__ == "__main__":
    main()
