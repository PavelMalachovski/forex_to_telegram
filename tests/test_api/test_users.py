"""Tests for user API endpoints."""

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession
from app.database.models import UserModel
from app.models.user import UserCreate, UserUpdate, UserPreferences


@pytest.mark.asyncio
class TestUserEndpoints:
    """Test user API endpoints."""

    async def test_create_user(self, test_client: AsyncClient, sample_user_data):
        """Test user creation endpoint."""
        response = await test_client.post("/api/v1/users/", json=sample_user_data)

        assert response.status_code == 201
        data = response.json()

        assert data["telegram_id"] == sample_user_data["telegram_id"]
        assert data["username"] == sample_user_data["username"]
        assert data["first_name"] == sample_user_data["first_name"]
        assert "id" in data
        assert "created_at" in data
        assert "updated_at" in data

    async def test_create_user_duplicate(self, test_client: AsyncClient, sample_user_data):
        """Test creating duplicate user."""
        # Create first user
        await test_client.post("/api/v1/users/", json=sample_user_data)

        # Try to create duplicate
        response = await test_client.post("/api/v1/users/", json=sample_user_data)

        assert response.status_code == 400
        assert "already exists" in response.json()["detail"]

    async def test_get_user(self, test_client: AsyncClient, sample_user_data):
        """Test get user endpoint."""
        # Create user first
        create_response = await test_client.post("/api/v1/users/", json=sample_user_data)
        user_data = create_response.json()

        # Get user
        response = await test_client.get(f"/api/v1/users/{sample_user_data['telegram_id']}")

        assert response.status_code == 200
        data = response.json()

        assert data["telegram_id"] == sample_user_data["telegram_id"]
        assert data["username"] == sample_user_data["username"]
        assert data["id"] == user_data["id"]

    async def test_get_user_not_found(self, test_client: AsyncClient):
        """Test get non-existent user."""
        response = await test_client.get("/api/v1/users/999999999")

        assert response.status_code == 404
        assert "not found" in response.json()["detail"]

    async def test_update_user(self, test_client: AsyncClient, sample_user_data):
        """Test user update endpoint."""
        # Create user first
        await test_client.post("/api/v1/users/", json=sample_user_data)

        # Update user
        update_data = {
            "username": "updateduser",
            "first_name": "Updated",
            "is_premium": True
        }

        response = await test_client.put(
            f"/api/v1/users/{sample_user_data['telegram_id']}",
            json=update_data
        )

        assert response.status_code == 200
        data = response.json()

        assert data["username"] == "updateduser"
        assert data["first_name"] == "Updated"
        assert data["is_premium"] is True
        assert data["telegram_id"] == sample_user_data["telegram_id"]

    async def test_update_user_not_found(self, test_client: AsyncClient):
        """Test update non-existent user."""
        update_data = {"username": "updateduser"}

        response = await test_client.put("/api/v1/users/999999999", json=update_data)

        assert response.status_code == 404
        assert "not found" in response.json()["detail"]

    async def test_update_user_preferences(self, test_client: AsyncClient, sample_user_data):
        """Test user preferences update endpoint."""
        # Create user first
        await test_client.post("/api/v1/users/", json=sample_user_data)

        # Update preferences
        preferences_data = {
            "preferred_currencies": ["GBP", "JPY"],
            "impact_levels": ["high"],
            "notifications_enabled": True,
            "notification_minutes": 15,
            "charts_enabled": True,
            "chart_type": "multi"
        }

        response = await test_client.put(
            f"/api/v1/users/{sample_user_data['telegram_id']}/preferences",
            json=preferences_data
        )

        assert response.status_code == 200
        data = response.json()

        assert data["preferences"]["preferred_currencies"] == ["GBP", "JPY"]
        assert data["preferences"]["impact_levels"] == ["high"]
        assert data["preferences"]["notifications_enabled"] is True
        assert data["preferences"]["notification_minutes"] == 15
        assert data["preferences"]["charts_enabled"] is True
        assert data["preferences"]["chart_type"] == "multi"

    async def test_get_users(self, test_client: AsyncClient, sample_user_data):
        """Test get users endpoint."""
        # Create multiple users
        users_data = [
            {**sample_user_data, "telegram_id": 111111111, "username": "user1"},
            {**sample_user_data, "telegram_id": 222222222, "username": "user2"},
            {**sample_user_data, "telegram_id": 333333333, "username": "user3"}
        ]

        for user_data in users_data:
            await test_client.post("/api/v1/users/", json=user_data)

        # Get users
        response = await test_client.get("/api/v1/users/")

        assert response.status_code == 200
        data = response.json()

        assert len(data) == 3
        assert all("telegram_id" in user for user in data)
        assert all("username" in user for user in data)

    async def test_get_users_with_pagination(self, test_client: AsyncClient, sample_user_data):
        """Test get users with pagination."""
        # Create multiple users
        for i in range(5):
            user_data = {**sample_user_data, "telegram_id": 100000000 + i}
            await test_client.post("/api/v1/users/", json=user_data)

        # Get first page
        response = await test_client.get("/api/v1/users/?skip=0&limit=2")

        assert response.status_code == 200
        data = response.json()
        assert len(data) == 2

        # Get second page
        response = await test_client.get("/api/v1/users/?skip=2&limit=2")

        assert response.status_code == 200
        data = response.json()
        assert len(data) == 2

    async def test_get_users_by_currency(self, test_client: AsyncClient, sample_user_data):
        """Test get users by currency endpoint."""
        # Create users with different currency preferences
        user1_data = {
            **sample_user_data,
            "telegram_id": 111111111,
            "preferences": {"preferred_currencies": ["USD", "EUR"]}
        }
        user2_data = {
            **sample_user_data,
            "telegram_id": 222222222,
            "preferences": {"preferred_currencies": ["GBP", "JPY"]}
        }

        await test_client.post("/api/v1/users/", json=user1_data)
        await test_client.post("/api/v1/users/", json=user2_data)

        # Get users by USD currency
        response = await test_client.get("/api/v1/users/by-currency/USD")

        assert response.status_code == 200
        data = response.json()
        assert len(data) == 1
        assert data[0]["telegram_id"] == 111111111

    async def test_get_users_by_impact_level(self, test_client: AsyncClient, sample_user_data):
        """Test get users by impact level endpoint."""
        # Create users with different impact level preferences
        user1_data = {
            **sample_user_data,
            "telegram_id": 111111111,
            "preferences": {"impact_levels": ["high"]}
        }
        user2_data = {
            **sample_user_data,
            "telegram_id": 222222222,
            "preferences": {"impact_levels": ["medium", "low"]}
        }

        await test_client.post("/api/v1/users/", json=user1_data)
        await test_client.post("/api/v1/users/", json=user2_data)

        # Get users by high impact level
        response = await test_client.get("/api/v1/users/by-impact/high")

        assert response.status_code == 200
        data = response.json()
        assert len(data) == 1
        assert data[0]["telegram_id"] == 111111111

    async def test_update_user_activity(self, test_client: AsyncClient, sample_user_data):
        """Test update user activity endpoint."""
        # Create user first
        await test_client.post("/api/v1/users/", json=sample_user_data)

        # Update activity
        response = await test_client.post(
            f"/api/v1/users/{sample_user_data['telegram_id']}/update-activity"
        )

        assert response.status_code == 200
        data = response.json()
        assert "Activity updated successfully" in data["message"]

    async def test_create_user_invalid_data(self, test_client: AsyncClient):
        """Test user creation with invalid data."""
        invalid_data = {
            "telegram_id": "invalid",  # Should be integer
            "username": "testuser"
        }

        response = await test_client.post("/api/v1/users/", json=invalid_data)

        assert response.status_code == 422  # Validation error

    async def test_update_user_invalid_preferences(self, test_client: AsyncClient, sample_user_data):
        """Test user update with invalid preferences."""
        # Create user first
        await test_client.post("/api/v1/users/", json=sample_user_data)

        # Update with invalid preferences
        invalid_preferences = {
            "preferred_currencies": ["INVALID"],  # Invalid currency
            "notification_minutes": 45  # Invalid minutes
        }

        response = await test_client.put(
            f"/api/v1/users/{sample_user_data['telegram_id']}/preferences",
            json=invalid_preferences
        )

        assert response.status_code == 400
        assert "Invalid currency" in response.json()["detail"]
