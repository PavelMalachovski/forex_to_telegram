"""Performance tests for API endpoints."""

import pytest
import asyncio
import time
from httpx import AsyncClient
from src.models.user import UserCreate


@pytest.mark.asyncio
@pytest.mark.slow
class TestAPIPerformance:
    """Test API performance characteristics."""

    async def test_user_creation_performance(self, test_client: AsyncClient):
        """Test user creation performance."""
        user_data = {
            "telegram_id": 123456789,
            "username": "perftest",
            "first_name": "Performance",
            "last_name": "Test"
        }

        start_time = time.time()
        response = await test_client.post("/api/v1/users/", json=user_data)
        end_time = time.time()

        assert response.status_code == 201
        assert (end_time - start_time) < 1.0  # Should complete within 1 second

    async def test_concurrent_user_creation(self, test_client: AsyncClient):
        """Test concurrent user creation performance."""
        async def create_user(telegram_id: int):
            user_data = {
                "telegram_id": telegram_id,
                "username": f"user{telegram_id}",
                "first_name": "Concurrent",
                "last_name": "Test"
            }
            return await test_client.post("/api/v1/users/", json=user_data)

        # Create 10 users concurrently
        start_time = time.time()
        tasks = [create_user(100000000 + i) for i in range(10)]
        responses = await asyncio.gather(*tasks)
        end_time = time.time()

        # All requests should succeed
        for response in responses:
            assert response.status_code == 201

        # Should complete within reasonable time
        assert (end_time - start_time) < 5.0  # Should complete within 5 seconds

    async def test_user_retrieval_performance(self, test_client: AsyncClient):
        """Test user retrieval performance."""
        # Create a user first
        user_data = {
            "telegram_id": 123456789,
            "username": "perftest",
            "first_name": "Performance"
        }
        await test_client.post("/api/v1/users/", json=user_data)

        # Test retrieval performance
        start_time = time.time()
        response = await test_client.get("/api/v1/users/123456789")
        end_time = time.time()

        assert response.status_code == 200
        assert (end_time - start_time) < 0.5  # Should complete within 500ms

    async def test_bulk_user_operations(self, test_client: AsyncClient):
        """Test bulk user operations performance."""
        # Create multiple users
        users_data = []
        for i in range(20):
            users_data.append({
                "telegram_id": 200000000 + i,
                "username": f"bulkuser{i}",
                "first_name": "Bulk",
                "last_name": "Test"
            })

        # Create all users
        start_time = time.time()
        for user_data in users_data:
            await test_client.post("/api/v1/users/", json=user_data)
        end_time = time.time()

        creation_time = end_time - start_time
        assert creation_time < 10.0  # Should complete within 10 seconds

        # Test bulk retrieval
        start_time = time.time()
        response = await test_client.get("/api/v1/users/")
        end_time = time.time()

        assert response.status_code == 200
        data = response.json()
        assert len(data) >= 20  # Should have at least 20 users

        retrieval_time = end_time - start_time
        assert retrieval_time < 2.0  # Should complete within 2 seconds

    async def test_database_query_performance(self, test_client: AsyncClient):
        """Test database query performance with filters."""
        # Create users with different properties
        for i in range(15):
            user_data = {
                "telegram_id": 300000000 + i,
                "username": f"queryuser{i}",
                "first_name": "Query",
                "last_name": "Test",
                "is_premium": i % 3 == 0  # Every third user is premium
            }
            await test_client.post("/api/v1/users/", json=user_data)

        # Test filtered queries
        start_time = time.time()
        response = await test_client.get("/api/v1/users/?is_premium=true")
        end_time = time.time()

        assert response.status_code == 200
        data = response.json()
        assert len(data) == 5  # Should have 5 premium users

        query_time = end_time - start_time
        assert query_time < 1.0  # Should complete within 1 second

    async def test_preferences_update_performance(self, test_client: AsyncClient):
        """Test user preferences update performance."""
        # Create a user first
        user_data = {
            "telegram_id": 123456789,
            "username": "prefuser",
            "first_name": "Preferences"
        }
        await test_client.post("/api/v1/users/", json=user_data)

        # Test preferences update performance
        preferences_data = {
            "preferred_currencies": ["USD", "EUR", "GBP", "JPY"],
            "impact_levels": ["high", "medium"],
            "notifications_enabled": True,
            "notification_minutes": 30,
            "charts_enabled": True,
            "chart_type": "multi",
            "chart_window_hours": 4
        }

        start_time = time.time()
        response = await test_client.put(
            "/api/v1/users/123456789/preferences",
            json=preferences_data
        )
        end_time = time.time()

        assert response.status_code == 200
        assert (end_time - start_time) < 1.0  # Should complete within 1 second

    async def test_telegram_webhook_performance(self, test_client: AsyncClient):
        """Test Telegram webhook processing performance."""
        webhook_data = {
            "update_id": 123456789,
            "message": {
                "message_id": 1,
                "from": {
                    "id": 123456789,
                    "is_bot": False,
                    "first_name": "Performance",
                    "username": "perftest"
                },
                "chat": {
                    "id": 123456789,
                    "type": "private"
                },
                "date": 1640995200,
                "text": "/start"
            }
        }

        start_time = time.time()
        response = await test_client.post(
            "/api/v1/telegram/webhook",
            json=webhook_data
        )
        end_time = time.time()

        assert response.status_code == 200
        assert (end_time - start_time) < 0.5  # Should complete within 500ms

    async def test_concurrent_webhook_processing(self, test_client: AsyncClient):
        """Test concurrent webhook processing performance."""
        async def send_webhook(update_id: int):
            webhook_data = {
                "update_id": update_id,
                "message": {
                    "message_id": 1,
                    "from": {
                        "id": 123456789,
                        "is_bot": False,
                        "first_name": "Concurrent",
                        "username": "concurrenttest"
                    },
                    "chat": {
                        "id": 123456789,
                        "type": "private"
                    },
                    "date": 1640995200,
                    "text": f"Message {update_id}"
                }
            }
            return await test_client.post("/api/v1/telegram/webhook", json=webhook_data)

        # Send 20 webhooks concurrently
        start_time = time.time()
        tasks = [send_webhook(400000000 + i) for i in range(20)]
        responses = await asyncio.gather(*tasks)
        end_time = time.time()

        # All requests should succeed
        for response in responses:
            assert response.status_code == 200

        # Should complete within reasonable time
        assert (end_time - start_time) < 10.0  # Should complete within 10 seconds

    async def test_memory_usage_stability(self, test_client: AsyncClient):
        """Test memory usage stability over multiple operations."""
        import psutil
        import os

        process = psutil.Process(os.getpid())
        initial_memory = process.memory_info().rss

        # Perform many operations
        for i in range(100):
            user_data = {
                "telegram_id": 500000000 + i,
                "username": f"memoryuser{i}",
                "first_name": "Memory",
                "last_name": "Test"
            }

            # Create user
            await test_client.post("/api/v1/users/", json=user_data)

            # Retrieve user
            await test_client.get(f"/api/v1/users/{500000000 + i}")

            # Update user
            await test_client.put(
                f"/api/v1/users/{500000000 + i}",
                json={"username": f"updateduser{i}"}
            )

        final_memory = process.memory_info().rss
        memory_increase = final_memory - initial_memory

        # Memory increase should be reasonable (less than 50MB)
        assert memory_increase < 50 * 1024 * 1024  # 50MB in bytes

    async def test_response_time_consistency(self, test_client: AsyncClient):
        """Test response time consistency across multiple requests."""
        # Create a user first
        user_data = {
            "telegram_id": 123456789,
            "username": "consistencytest",
            "first_name": "Consistency"
        }
        await test_client.post("/api/v1/users/", json=user_data)

        # Measure response times for multiple requests
        response_times = []
        for _ in range(10):
            start_time = time.time()
            response = await test_client.get("/api/v1/users/123456789")
            end_time = time.time()

            assert response.status_code == 200
            response_times.append(end_time - start_time)

        # Calculate statistics
        avg_time = sum(response_times) / len(response_times)
        max_time = max(response_times)
        min_time = min(response_times)

        # Response times should be consistent
        assert avg_time < 0.5  # Average should be under 500ms
        assert max_time < 1.0  # Max should be under 1 second
        assert (max_time - min_time) < 0.5  # Range should be reasonable
