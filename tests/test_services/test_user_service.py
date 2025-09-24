"""Tests for user service."""

import pytest
from sqlalchemy.ext.asyncio import AsyncSession
from src.services.user_service import UserService
from src.database.models import UserModel
from src.models.user import UserCreate, UserUpdate, UserPreferences
from src.core.exceptions import ValidationError, DatabaseError


@pytest.mark.asyncio
class TestUserService:
    """Test UserService."""

    @pytest.fixture
    def user_service(self):
        """Create user service instance."""
        return UserService()

    async def test_create_user(self, user_service: UserService, test_db_session: AsyncSession, sample_user_data):
        """Test user creation."""
        user_create = UserCreate(**sample_user_data)

        user = await user_service.create_user(test_db_session, user_create)

        assert isinstance(user, UserModel)
        assert user.telegram_id == sample_user_data["telegram_id"]
        assert user.username == sample_user_data["username"]
        assert user.first_name == sample_user_data["first_name"]
        assert user.id is not None
        assert user.created_at is not None
        assert user.updated_at is not None

    async def test_create_user_duplicate(self, user_service: UserService, test_db_session: AsyncSession, sample_user_data):
        """Test creating duplicate user."""
        user_create = UserCreate(**sample_user_data)

        # Create first user
        await user_service.create_user(test_db_session, user_create)

        # Try to create duplicate
        with pytest.raises(ValidationError) as exc_info:
            await user_service.create_user(test_db_session, user_create)

        assert "already exists" in str(exc_info.value)

    async def test_get_by_telegram_id(self, user_service: UserService, test_db_session: AsyncSession, sample_user_data):
        """Test get user by Telegram ID."""
        user_create = UserCreate(**sample_user_data)
        created_user = await user_service.create_user(test_db_session, user_create)

        user = await user_service.get_by_telegram_id(test_db_session, sample_user_data["telegram_id"])

        assert user is not None
        assert user.id == created_user.id
        assert user.telegram_id == sample_user_data["telegram_id"]
        assert user.username == sample_user_data["username"]

    async def test_get_by_telegram_id_not_found(self, user_service: UserService, test_db_session: AsyncSession):
        """Test get non-existent user by Telegram ID."""
        user = await user_service.get_by_telegram_id(test_db_session, 999999999)

        assert user is None

    async def test_update_user(self, user_service: UserService, test_db_session: AsyncSession, sample_user_data):
        """Test user update."""
        user_create = UserCreate(**sample_user_data)
        created_user = await user_service.create_user(test_db_session, user_create)

        update_data = UserUpdate(
            username="updateduser",
            first_name="Updated",
            is_premium=True
        )

        updated_user = await user_service.update_user(
            test_db_session,
            sample_user_data["telegram_id"],
            update_data
        )

        assert updated_user is not None
        assert updated_user.id == created_user.id
        assert updated_user.username == "updateduser"
        assert updated_user.first_name == "Updated"
        assert updated_user.is_premium is True
        assert updated_user.telegram_id == sample_user_data["telegram_id"]

    async def test_update_user_not_found(self, user_service: UserService, test_db_session: AsyncSession):
        """Test update non-existent user."""
        update_data = UserUpdate(username="updateduser")

        updated_user = await user_service.update_user(test_db_session, 999999999, update_data)

        assert updated_user is None

    async def test_update_preferences(self, user_service: UserService, test_db_session: AsyncSession, sample_user_data):
        """Test user preferences update."""
        user_create = UserCreate(**sample_user_data)
        await user_service.create_user(test_db_session, user_create)

        preferences = UserPreferences(
            preferred_currencies=["GBP", "JPY"],
            impact_levels=["high"],
            notifications_enabled=True,
            notification_minutes=15,
            charts_enabled=True,
            chart_type="multi"
        )

        updated_user = await user_service.update_preferences(
            test_db_session,
            sample_user_data["telegram_id"],
            preferences
        )

        assert updated_user is not None
        assert updated_user.preferred_currencies == ["GBP", "JPY"]
        assert updated_user.impact_levels == ["high"]
        assert updated_user.notifications_enabled is True
        assert updated_user.notification_minutes == 15
        assert updated_user.charts_enabled is True
        assert updated_user.chart_type == "multi"

    async def test_get_active_users(self, user_service: UserService, test_db_session: AsyncSession, sample_user_data):
        """Test get active users."""
        # Create multiple users
        users_data = [
            {**sample_user_data, "telegram_id": 111111111, "username": "user1"},
            {**sample_user_data, "telegram_id": 222222222, "username": "user2"},
            {**sample_user_data, "telegram_id": 333333333, "username": "user3"}
        ]

        for user_data in users_data:
            user_create = UserCreate(**user_data)
            await user_service.create_user(test_db_session, user_create)

        # Get active users
        active_users = await user_service.get_active_users(test_db_session)

        assert len(active_users) == 3
        assert all(user.is_active for user in active_users)
        assert all(user.username in ["user1", "user2", "user3"] for user in active_users)

    async def test_get_users_by_currency(self, user_service: UserService, test_db_session: AsyncSession, sample_user_data):
        """Test get users by currency."""
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

        user1_create = UserCreate(**user1_data)
        user2_create = UserCreate(**user2_data)

        await user_service.create_user(test_db_session, user1_create)
        await user_service.create_user(test_db_session, user2_create)

        # Get users by USD currency
        usd_users = await user_service.get_users_by_currency(test_db_session, "USD")

        assert len(usd_users) == 1
        assert usd_users[0].telegram_id == 111111111
        assert "USD" in usd_users[0].preferred_currencies

    async def test_get_users_by_impact_level(self, user_service: UserService, test_db_session: AsyncSession, sample_user_data):
        """Test get users by impact level."""
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

        user1_create = UserCreate(**user1_data)
        user2_create = UserCreate(**user2_data)

        await user_service.create_user(test_db_session, user1_create)
        await user_service.create_user(test_db_session, user2_create)

        # Get users by high impact level
        high_impact_users = await user_service.get_users_by_impact_level(test_db_session, "high")

        assert len(high_impact_users) == 1
        assert high_impact_users[0].telegram_id == 111111111
        assert "high" in high_impact_users[0].impact_levels

    async def test_update_last_active(self, user_service: UserService, test_db_session: AsyncSession, sample_user_data):
        """Test update last active timestamp."""
        user_create = UserCreate(**sample_user_data)
        created_user = await user_service.create_user(test_db_session, user_create)

        # Update last active
        await user_service.update_last_active(test_db_session, sample_user_data["telegram_id"])

        # Verify update
        updated_user = await user_service.get_by_telegram_id(test_db_session, sample_user_data["telegram_id"])

        assert updated_user.last_active is not None
        assert updated_user.last_active > created_user.created_at

    async def test_get_all_with_filters(self, user_service: UserService, test_db_session: AsyncSession, sample_user_data):
        """Test get all users with filters."""
        # Create users with different properties
        user1_data = {**sample_user_data, "telegram_id": 111111111, "is_premium": True}
        user2_data = {**sample_user_data, "telegram_id": 222222222, "is_premium": False}

        user1_create = UserCreate(**user1_data)
        user2_create = UserCreate(**user2_data)

        await user_service.create_user(test_db_session, user1_create)
        await user_service.create_user(test_db_session, user2_create)

        # Get premium users
        premium_users = await user_service.get_all(test_db_session, filters={"is_premium": True})

        assert len(premium_users) == 1
        assert premium_users[0].telegram_id == 111111111
        assert premium_users[0].is_premium is True

    async def test_count_users(self, user_service: UserService, test_db_session: AsyncSession, sample_user_data):
        """Test count users."""
        # Create multiple users
        for i in range(3):
            user_data = {**sample_user_data, "telegram_id": 100000000 + i}
            user_create = UserCreate(**user_data)
            await user_service.create_user(test_db_session, user_create)

        # Count all users
        total_count = await user_service.count(test_db_session)
        assert total_count == 3

        # Count with filter
        premium_count = await user_service.count(test_db_session, filters={"is_premium": False})
        assert premium_count == 3  # All users are non-premium by default
