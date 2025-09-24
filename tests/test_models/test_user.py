"""Tests for user data models."""

import pytest
from datetime import time
from pydantic import ValidationError
from src.models.user import User, UserCreate, UserUpdate, UserPreferences


class TestUserPreferences:
    """Test UserPreferences model."""

    def test_default_preferences(self):
        """Test default user preferences."""
        preferences = UserPreferences()

        assert preferences.preferred_currencies == []
        assert preferences.impact_levels == ["high", "medium"]
        assert preferences.analysis_required is True
        assert preferences.digest_time == time(8, 0)
        assert preferences.timezone == "Europe/Prague"
        assert preferences.notifications_enabled is False
        assert preferences.notification_minutes == 30
        assert preferences.notification_impact_levels == ["high"]
        assert preferences.charts_enabled is False
        assert preferences.chart_type == "single"
        assert preferences.chart_window_hours == 2

    def test_valid_currencies(self):
        """Test valid currency codes."""
        valid_currencies = ["USD", "EUR", "GBP", "JPY", "BTC", "ETH"]
        preferences = UserPreferences(preferred_currencies=valid_currencies)

        assert preferences.preferred_currencies == valid_currencies

    def test_invalid_currency(self):
        """Test invalid currency code validation."""
        with pytest.raises(ValidationError) as exc_info:
            UserPreferences(preferred_currencies=["INVALID"])

        assert "Invalid currency: INVALID" in str(exc_info.value)

    def test_valid_impact_levels(self):
        """Test valid impact levels."""
        valid_levels = ["high", "medium", "low"]
        preferences = UserPreferences(impact_levels=valid_levels)

        assert preferences.impact_levels == valid_levels

    def test_invalid_impact_level(self):
        """Test invalid impact level validation."""
        with pytest.raises(ValidationError) as exc_info:
            UserPreferences(impact_levels=["invalid"])

        assert "Invalid impact level: invalid" in str(exc_info.value)

    def test_valid_notification_minutes(self):
        """Test valid notification minutes."""
        valid_minutes = [15, 30, 60]
        for minutes in valid_minutes:
            preferences = UserPreferences(notification_minutes=minutes)
            assert preferences.notification_minutes == minutes

    def test_invalid_notification_minutes(self):
        """Test invalid notification minutes validation."""
        with pytest.raises(ValidationError) as exc_info:
            UserPreferences(notification_minutes=45)

        assert "Notification minutes must be 15, 30, or 60" in str(exc_info.value)

    def test_valid_chart_window_hours(self):
        """Test valid chart window hours."""
        valid_hours = [1, 2, 12, 24]
        for hours in valid_hours:
            preferences = UserPreferences(chart_window_hours=hours)
            assert preferences.chart_window_hours == hours

    def test_invalid_chart_window_hours(self):
        """Test invalid chart window hours validation."""
        with pytest.raises(ValidationError) as exc_info:
            UserPreferences(chart_window_hours=0)

        assert "Chart window must be between 1 and 24 hours" in str(exc_info.value)

        with pytest.raises(ValidationError) as exc_info:
            UserPreferences(chart_window_hours=25)

        assert "Chart window must be between 1 and 24 hours" in str(exc_info.value)


class TestUserBase:
    """Test UserBase model."""

    def test_user_base_creation(self):
        """Test UserBase model creation."""
        user_data = {
            "telegram_id": 123456789,
            "username": "testuser",
            "first_name": "Test",
            "last_name": "User",
            "language_code": "en",
            "is_bot": False,
            "is_premium": True
        }

        user = UserBase(**user_data)

        assert user.telegram_id == 123456789
        assert user.username == "testuser"
        assert user.first_name == "Test"
        assert user.last_name == "User"
        assert user.language_code == "en"
        assert user.is_bot is False
        assert user.is_premium is True

    def test_user_base_minimal(self):
        """Test UserBase with minimal required data."""
        user = UserBase(telegram_id=123456789)

        assert user.telegram_id == 123456789
        assert user.username is None
        assert user.first_name is None
        assert user.last_name is None
        assert user.language_code is None
        assert user.is_bot is False
        assert user.is_premium is False


class TestUserCreate:
    """Test UserCreate model."""

    def test_user_create_with_preferences(self):
        """Test UserCreate with preferences."""
        user_data = {
            "telegram_id": 123456789,
            "username": "testuser",
            "first_name": "Test",
            "preferences": UserPreferences(
                preferred_currencies=["USD", "EUR"],
                impact_levels=["high"]
            )
        }

        user = UserCreate(**user_data)

        assert user.telegram_id == 123456789
        assert user.username == "testuser"
        assert user.first_name == "Test"
        assert isinstance(user.preferences, UserPreferences)
        assert user.preferences.preferred_currencies == ["USD", "EUR"]
        assert user.preferences.impact_levels == ["high"]

    def test_user_create_default_preferences(self):
        """Test UserCreate with default preferences."""
        user_data = {
            "telegram_id": 123456789,
            "username": "testuser"
        }

        user = UserCreate(**user_data)

        assert user.telegram_id == 123456789
        assert user.username == "testuser"
        assert isinstance(user.preferences, UserPreferences)
        assert user.preferences.preferred_currencies == []


class TestUserUpdate:
    """Test UserUpdate model."""

    def test_user_update_partial(self):
        """Test partial user update."""
        update_data = {
            "username": "newusername",
            "is_premium": True
        }

        user_update = UserUpdate(**update_data)

        assert user_update.username == "newusername"
        assert user_update.is_premium is True
        assert user_update.first_name is None
        assert user_update.preferences is None

    def test_user_update_with_preferences(self):
        """Test user update with preferences."""
        preferences = UserPreferences(
            preferred_currencies=["GBP"],
            notifications_enabled=True
        )

        update_data = {
            "first_name": "NewName",
            "preferences": preferences
        }

        user_update = UserUpdate(**update_data)

        assert user_update.first_name == "NewName"
        assert isinstance(user_update.preferences, UserPreferences)
        assert user_update.preferences.preferred_currencies == ["GBP"]
        assert user_update.preferences.notifications_enabled is True


class TestUser:
    """Test User model."""

    def test_user_creation(self):
        """Test User model creation."""
        preferences = UserPreferences(preferred_currencies=["USD"])

        user_data = {
            "id": 1,
            "telegram_id": 123456789,
            "username": "testuser",
            "first_name": "Test",
            "preferences": preferences,
            "created_at": "2024-01-01T00:00:00Z",
            "updated_at": "2024-01-01T00:00:00Z",
            "is_active": True
        }

        user = User(**user_data)

        assert user.id == 1
        assert user.telegram_id == 123456789
        assert user.username == "testuser"
        assert user.first_name == "Test"
        assert isinstance(user.preferences, UserPreferences)
        assert user.preferences.preferred_currencies == ["USD"]
        assert user.is_active is True

    def test_user_json_encoding(self):
        """Test User JSON encoding."""
        preferences = UserPreferences(digest_time=time(9, 30))

        user_data = {
            "id": 1,
            "telegram_id": 123456789,
            "username": "testuser",
            "preferences": preferences,
            "created_at": "2024-01-01T00:00:00Z",
            "updated_at": "2024-01-01T00:00:00Z",
            "is_active": True
        }

        user = User(**user_data)

        # Test that the model can be serialized
        user_dict = user.model_dump()
        assert "id" in user_dict
        assert "telegram_id" in user_dict
        assert "preferences" in user_dict
        assert user_dict["preferences"]["digest_time"] == "09:30:00"
