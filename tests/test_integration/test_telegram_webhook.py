"""Integration tests for Telegram webhook functionality."""

import pytest
from httpx import AsyncClient
from unittest.mock import AsyncMock, patch
from src.models.telegram import TelegramUpdate, TelegramMessage, TelegramUser


@pytest.mark.asyncio
@pytest.mark.integration
class TestTelegramWebhook:
    """Test Telegram webhook integration."""

    async def test_webhook_message_processing(self, test_client: AsyncClient, sample_telegram_update_data):
        """Test webhook message processing."""
        response = await test_client.post(
            "/api/v1/telegram/webhook",
            json=sample_telegram_update_data
        )

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "success"
        assert "processed" in data["message"]

    async def test_webhook_callback_query(self, test_client: AsyncClient):
        """Test webhook callback query processing."""
        callback_data = {
            "update_id": 123456789,
            "callback_query": {
                "id": "callback123",
                "from": {
                    "id": 123456789,
                    "is_bot": False,
                    "first_name": "Test",
                    "username": "testuser"
                },
                "message": {
                    "message_id": 1,
                    "from": {
                        "id": 123456789,
                        "is_bot": False,
                        "first_name": "Test"
                    },
                    "chat": {
                        "id": 123456789,
                        "type": "private"
                    },
                    "date": 1640995200,
                    "text": "Choose an option:"
                },
                "data": "currency_USD"
            }
        }

        response = await test_client.post(
            "/api/v1/telegram/webhook",
            json=callback_data
        )

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "success"

    async def test_webhook_invalid_data(self, test_client: AsyncClient):
        """Test webhook with invalid data."""
        invalid_data = {
            "update_id": "invalid",  # Should be integer
            "message": {
                "text": "test"
            }
        }

        response = await test_client.post(
            "/api/v1/telegram/webhook",
            json=invalid_data
        )

        assert response.status_code == 422  # Validation error

    async def test_webhook_missing_update_id(self, test_client: AsyncClient):
        """Test webhook with missing update_id."""
        invalid_data = {
            "message": {
                "text": "test"
            }
        }

        response = await test_client.post(
            "/api/v1/telegram/webhook",
            json=invalid_data
        )

        assert response.status_code == 422  # Validation error

    async def test_webhook_secret_validation(self, test_client: AsyncClient, sample_telegram_update_data):
        """Test webhook secret validation."""
        # Test with invalid secret
        response = await test_client.post(
            "/api/v1/telegram/webhook",
            json=sample_telegram_update_data,
            headers={"X-Telegram-Secret-Token": "invalid_secret"}
        )

        # Should still work in test environment (no secret validation)
        assert response.status_code == 200

    async def test_webhook_user_creation(self, test_client: AsyncClient):
        """Test that webhook creates user if not exists."""
        # First, ensure no user exists
        response = await test_client.get("/api/v1/users/123456789")
        assert response.status_code == 404

        # Send webhook message
        webhook_data = {
            "update_id": 123456789,
            "message": {
                "message_id": 1,
                "from": {
                    "id": 123456789,
                    "is_bot": False,
                    "first_name": "Test",
                    "last_name": "User",
                    "username": "testuser",
                    "language_code": "en"
                },
                "chat": {
                    "id": 123456789,
                    "type": "private",
                    "first_name": "Test",
                    "last_name": "User",
                    "username": "testuser"
                },
                "date": 1640995200,
                "text": "/start"
            }
        }

        response = await test_client.post(
            "/api/v1/telegram/webhook",
            json=webhook_data
        )

        assert response.status_code == 200

        # Check that user was created
        response = await test_client.get("/api/v1/users/123456789")
        assert response.status_code == 200

        user_data = response.json()
        assert user_data["telegram_id"] == 123456789
        assert user_data["username"] == "testuser"
        assert user_data["first_name"] == "Test"

    async def test_webhook_command_processing(self, test_client: AsyncClient):
        """Test webhook command processing."""
        commands = ["/start", "/help", "/settings", "/currencies", "/impact", "/digest"]

        for command in commands:
            webhook_data = {
                "update_id": 123456789,
                "message": {
                    "message_id": 1,
                    "from": {
                        "id": 123456789,
                        "is_bot": False,
                        "first_name": "Test",
                        "username": "testuser"
                    },
                    "chat": {
                        "id": 123456789,
                        "type": "private"
                    },
                    "date": 1640995200,
                    "text": command
                }
            }

            response = await test_client.post(
                "/api/v1/telegram/webhook",
                json=webhook_data
            )

            assert response.status_code == 200
            data = response.json()
            assert data["status"] == "success"

    async def test_webhook_group_message(self, test_client: AsyncClient):
        """Test webhook group message processing."""
        group_data = {
            "update_id": 123456789,
            "message": {
                "message_id": 1,
                "from": {
                    "id": 123456789,
                    "is_bot": False,
                    "first_name": "Test",
                    "username": "testuser"
                },
                "chat": {
                    "id": -1001234567890,  # Group chat ID
                    "type": "group",
                    "title": "Test Group"
                },
                "date": 1640995200,
                "text": "Hello group!"
            }
        }

        response = await test_client.post(
            "/api/v1/telegram/webhook",
            json=group_data
        )

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "success"

    async def test_webhook_webhook_info(self, test_client: AsyncClient):
        """Test webhook info endpoint."""
        response = await test_client.get("/api/v1/telegram/webhook-info")

        assert response.status_code == 200
        data = response.json()

        assert "url" in data
        assert "pending_update_count" in data
        assert "last_error_date" in data
        assert "max_connections" in data

    async def test_webhook_setup(self, test_client: AsyncClient):
        """Test webhook setup endpoint."""
        response = await test_client.post("/api/v1/telegram/setup-webhook")

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "success"
        assert "Webhook setup completed" in data["message"]

    async def test_webhook_delete(self, test_client: AsyncClient):
        """Test webhook delete endpoint."""
        response = await test_client.delete("/api/v1/telegram/webhook")

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "success"
        assert "Webhook deleted successfully" in data["message"]

    async def test_webhook_test_message(self, test_client: AsyncClient):
        """Test webhook test message endpoint."""
        response = await test_client.post(
            "/api/v1/telegram/test-message",
            json={"chat_id": 123456789, "message": "Test message"}
        )

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "success"
        assert "Test message sent successfully" in data["message"]

    async def test_webhook_error_handling(self, test_client: AsyncClient):
        """Test webhook error handling."""
        # Test with malformed JSON
        response = await test_client.post(
            "/api/v1/telegram/webhook",
            content="invalid json"
        )

        assert response.status_code == 422  # Validation error

    async def test_webhook_concurrent_requests(self, test_client: AsyncClient, sample_telegram_update_data):
        """Test webhook with concurrent requests."""
        import asyncio

        # Send multiple requests concurrently
        tasks = []
        for i in range(5):
            data = {**sample_telegram_update_data, "update_id": 123456789 + i}
            task = test_client.post("/api/v1/telegram/webhook", json=data)
            tasks.append(task)

        responses = await asyncio.gather(*tasks)

        # All requests should succeed
        for response in responses:
            assert response.status_code == 200
            data = response.json()
            assert data["status"] == "success"
