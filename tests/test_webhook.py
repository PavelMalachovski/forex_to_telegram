#!/usr/bin/env python3
"""Test script to verify webhook setup."""

import pytest
import requests
import json
import os
import sys

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

def test_force_webhook_setup(base_url):
    """Test force webhook setup endpoint."""
    result = _test_endpoint(base_url, "/force_webhook_setup", method='POST')
    assert result.get('status_code') == 200, f"Force webhook setup failed: {result}"
    print(f"Force webhook setup response: {json.dumps(result.get('data', {}), indent=2)}")

def test_manual_initialize(base_url):
    """Test manual initialization endpoint."""
    result = _test_endpoint(base_url, "/initialize", method='POST')
    assert result.get('status_code') == 200, f"Manual initialization failed: {result}"
    print(f"Manual initialization response: {json.dumps(result.get('data', {}), indent=2)}")

# Keep the original main function for standalone execution
def main():
    """Main test function for standalone execution."""
    # Get the base URL from command line or use default
    if len(sys.argv) > 1:
        base_url = sys.argv[1]
    else:
        base_url = "https://your-app-name.onrender.com"  # Replace with your actual URL

    print(f"🔍 Testing webhook setup for: {base_url}")
    print("=" * 50)

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

    # Test force webhook setup
    print("\n4. Testing force webhook setup...")
    force_setup_result = _test_endpoint(base_url, "/force_webhook_setup", method='POST')
    print(f"Status: {force_setup_result.get('status_code', 'Error')}")
    if 'data' in force_setup_result:
        print(f"Response: {json.dumps(force_setup_result['data'], indent=2)}")
    else:
        print(f"Error: {force_setup_result.get('error', 'Unknown error')}")

    # Test manual initialization
    print("\n5. Testing manual initialization...")
    init_result = _test_endpoint(base_url, "/initialize", method='POST')
    print(f"Status: {init_result.get('status_code', 'Error')}")
    if 'data' in init_result:
        print(f"Response: {json.dumps(init_result['data'], indent=2)}")
    else:
        print(f"Error: {init_result.get('error', 'Unknown error')}")

    print("\n" + "=" * 50)
    print("✅ Testing completed!")

if __name__ == "__main__":
    main()
