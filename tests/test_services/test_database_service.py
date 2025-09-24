"""Tests for database service."""

import pytest
import pytest_asyncio
from unittest.mock import AsyncMock, patch
from datetime import datetime, date
from sqlalchemy.ext.asyncio import AsyncSession

from app.services.database_service import DatabaseService
from app.core.exceptions import DatabaseError, ValidationError
from tests.factories import UserCreateFactory, ForexNewsCreateFactory


class TestDatabaseService:
    """Test cases for DatabaseService."""

    @pytest.fixture
    def database_service(self):
        """Create database service instance."""
        return DatabaseService()

    @pytest.fixture
    def mock_db_session(self):
        """Create mock database session."""
        return AsyncMock(spec=AsyncSession)

    @pytest.mark.asyncio
    async def test_create_user_success(self, database_service, mock_db_session):
        """Test successful user creation."""
        # Arrange
        user_data = UserCreateFactory.build()
        mock_db_session.add = AsyncMock()
        mock_db_session.commit = AsyncMock()
        mock_db_session.refresh = AsyncMock()

        # Act
        result = await database_service.create_user(mock_db_session, user_data)

        # Assert
        assert result is not None
        mock_db_session.add.assert_called_once()
        mock_db_session.commit.assert_called_once()
        mock_db_session.refresh.assert_called_once()

    @pytest.mark.asyncio
    async def test_create_user_database_error(self, database_service, mock_db_session):
        """Test user creation with database error."""
        # Arrange
        user_data = UserCreateFactory.build()
        mock_db_session.add = AsyncMock()
        mock_db_session.commit = AsyncMock(side_effect=Exception("Database error"))
        mock_db_session.rollback = AsyncMock()

        # Act & Assert
        with pytest.raises(DatabaseError):
            await database_service.create_user(mock_db_session, user_data)

        mock_db_session.rollback.assert_called_once()

    @pytest.mark.asyncio
    async def test_get_user_by_telegram_id_success(self, database_service, mock_db_session):
        """Test successful user retrieval by Telegram ID."""
        # Arrange
        telegram_id = 123456789
        mock_user = UserCreateFactory.build()
        mock_db_session.execute = AsyncMock()
        mock_result = AsyncMock()
        mock_result.scalar_one_or_none.return_value = mock_user
        mock_db_session.execute.return_value = mock_result

        # Act
        result = await database_service.get_user_by_telegram_id(mock_db_session, telegram_id)

        # Assert
        assert result == mock_user
        mock_db_session.execute.assert_called_once()

    @pytest.mark.asyncio
    async def test_get_user_by_telegram_id_not_found(self, database_service, mock_db_session):
        """Test user retrieval when user not found."""
        # Arrange
        telegram_id = 999999999
        mock_db_session.execute = AsyncMock()
        mock_result = AsyncMock()
        mock_result.scalar_one_or_none.return_value = None
        mock_db_session.execute.return_value = mock_result

        # Act
        result = await database_service.get_user_by_telegram_id(mock_db_session, telegram_id)

        # Assert
        assert result is None

    @pytest.mark.asyncio
    async def test_update_user_success(self, database_service, mock_db_session):
        """Test successful user update."""
        # Arrange
        telegram_id = 123456789
        update_data = {"first_name": "Updated Name"}
        mock_user = UserCreateFactory.build()

        mock_db_session.execute = AsyncMock()
        mock_result = AsyncMock()
        mock_result.scalar_one_or_none.return_value = mock_user
        mock_db_session.execute.return_value = mock_result
        mock_db_session.commit = AsyncMock()
        mock_db_session.refresh = AsyncMock()

        # Act
        result = await database_service.update_user(mock_db_session, telegram_id, update_data)

        # Assert
        assert result == mock_user
        mock_db_session.commit.assert_called_once()
        mock_db_session.refresh.assert_called_once()

    @pytest.mark.asyncio
    async def test_update_user_not_found(self, database_service, mock_db_session):
        """Test user update when user not found."""
        # Arrange
        telegram_id = 999999999
        update_data = {"first_name": "Updated Name"}

        mock_db_session.execute = AsyncMock()
        mock_result = AsyncMock()
        mock_result.scalar_one_or_none.return_value = None
        mock_db_session.execute.return_value = mock_result

        # Act
        result = await database_service.update_user(mock_db_session, telegram_id, update_data)

        # Assert
        assert result is None

    @pytest.mark.asyncio
    async def test_create_forex_news_success(self, database_service, mock_db_session):
        """Test successful forex news creation."""
        # Arrange
        news_data = ForexNewsCreateFactory.build()
        mock_db_session.add = AsyncMock()
        mock_db_session.commit = AsyncMock()
        mock_db_session.refresh = AsyncMock()

        # Act
        result = await database_service.create_forex_news(mock_db_session, news_data)

        # Assert
        assert result is not None
        mock_db_session.add.assert_called_once()
        mock_db_session.commit.assert_called_once()
        mock_db_session.refresh.assert_called_once()

    @pytest.mark.asyncio
    async def test_get_forex_news_by_date_success(self, database_service, mock_db_session):
        """Test successful forex news retrieval by date."""
        # Arrange
        target_date = date(2024, 1, 15)
        mock_news = [ForexNewsCreateFactory.build() for _ in range(3)]

        mock_db_session.execute = AsyncMock()
        mock_result = AsyncMock()
        mock_result.scalars.return_value.all.return_value = mock_news
        mock_db_session.execute.return_value = mock_result

        # Act
        result = await database_service.get_forex_news_by_date(mock_db_session, target_date)

        # Assert
        assert len(result) == 3
        assert result == mock_news
        mock_db_session.execute.assert_called_once()

    @pytest.mark.asyncio
    async def test_get_forex_news_by_currency_success(self, database_service, mock_db_session):
        """Test successful forex news retrieval by currency."""
        # Arrange
        currency = "USD"
        mock_news = [ForexNewsCreateFactory.build(currency=currency) for _ in range(2)]

        mock_db_session.execute = AsyncMock()
        mock_result = AsyncMock()
        mock_result.scalars.return_value.all.return_value = mock_news
        mock_db_session.execute.return_value = mock_result

        # Act
        result = await database_service.get_forex_news_by_currency(mock_db_session, currency)

        # Assert
        assert len(result) == 2
        assert result == mock_news
        mock_db_session.execute.assert_called_once()

    @pytest.mark.asyncio
    async def test_get_users_by_currency_success(self, database_service, mock_db_session):
        """Test successful user retrieval by currency preference."""
        # Arrange
        currency = "USD"
        mock_users = [UserCreateFactory.build() for _ in range(3)]

        mock_db_session.execute = AsyncMock()
        mock_result = AsyncMock()
        mock_result.scalars.return_value.all.return_value = mock_users
        mock_db_session.execute.return_value = mock_result

        # Act
        result = await database_service.get_users_by_currency(mock_db_session, currency)

        # Assert
        assert len(result) == 3
        assert result == mock_users
        mock_db_session.execute.assert_called_once()

    @pytest.mark.asyncio
    async def test_get_users_by_impact_level_success(self, database_service, mock_db_session):
        """Test successful user retrieval by impact level preference."""
        # Arrange
        impact_level = "high"
        mock_users = [UserCreateFactory.build() for _ in range(2)]

        mock_db_session.execute = AsyncMock()
        mock_result = AsyncMock()
        mock_result.scalars.return_value.all.return_value = mock_users
        mock_db_session.execute.return_value = mock_result

        # Act
        result = await database_service.get_users_by_impact_level(mock_db_session, impact_level)

        # Assert
        assert len(result) == 2
        assert result == mock_users
        mock_db_session.execute.assert_called_once()

    @pytest.mark.asyncio
    async def test_database_error_handling(self, database_service, mock_db_session):
        """Test database error handling."""
        # Arrange
        mock_db_session.execute = AsyncMock(side_effect=Exception("Database connection error"))

        # Act & Assert
        with pytest.raises(DatabaseError):
            await database_service.get_user_by_telegram_id(mock_db_session, 123456789)

    @pytest.mark.asyncio
    async def test_validation_error_handling(self, database_service, mock_db_session):
        """Test validation error handling."""
        # Arrange
        invalid_user_data = UserCreateFactory.build()
        # Simulate validation error
        mock_db_session.add = AsyncMock(side_effect=ValidationError("Invalid data"))

        # Act & Assert
        with pytest.raises(ValidationError):
            await database_service.create_user(mock_db_session, invalid_user_data)
