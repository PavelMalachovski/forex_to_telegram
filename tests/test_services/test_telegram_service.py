"""Tests for telegram service."""

import pytest
import pytest_asyncio
from unittest.mock import AsyncMock, patch, MagicMock
from datetime import datetime

from app.services.telegram_service import TelegramService
from app.core.exceptions import TelegramError, ValidationError
from tests.factories import UserCreateFactory


@pytest.fixture
def telegram_service():
    """Create telegram service instance."""
    return TelegramService()


@pytest.fixture
def mock_bot():
    """Create mock telegram bot."""
    mock_bot = AsyncMock()
    mock_bot.send_message.return_value = AsyncMock()
    mock_bot.get_webhook_info.return_value = AsyncMock()
    mock_bot.set_webhook.return_value = AsyncMock()
    mock_bot.delete_webhook.return_value = AsyncMock()
    return mock_bot


@pytest.fixture
def mock_db_session():
    """Create mock database session."""
    return AsyncMock()


class TestTelegramService:
    """Test cases for TelegramService."""

    @pytest.mark.asyncio
    async def test_send_message_success(self, telegram_service, mock_bot):
        """Test successful message sending."""
        # Arrange
        chat_id = 123456789
        message = "Test message"
        mock_bot.send_message.return_value = AsyncMock(message_id=1)

        # Act
        result = await telegram_service.send_message(mock_bot, chat_id, message)

        # Assert
        assert result is not None
        mock_bot.send_message.assert_called_once_with(chat_id=chat_id, text=message)

    @pytest.mark.asyncio
    async def test_send_message_error(self, telegram_service, mock_bot):
        """Test message sending with error."""
        # Arrange
        chat_id = 123456789
        message = "Test message"
        mock_bot.send_message.side_effect = Exception("Telegram API error")

        # Act & Assert
        with pytest.raises(TelegramError):
            await telegram_service.send_message(mock_bot, chat_id, message)

    @pytest.mark.asyncio
    async def test_send_long_message_success(self, telegram_service, mock_bot):
        """Test successful long message sending."""
        # Arrange
        chat_id = 123456789
        long_message = "A" * 5000  # Long message
        mock_bot.send_message.return_value = AsyncMock(message_id=1)

        # Act
        result = await telegram_service.send_long_message(mock_bot, chat_id, long_message)

        # Assert
        assert result is not None
        # Should split into multiple messages
        assert mock_bot.send_message.call_count > 1

    @pytest.mark.asyncio
    async def test_send_formatted_message_success(self, telegram_service, mock_bot):
        """Test successful formatted message sending."""
        # Arrange
        chat_id = 123456789
        message = "**Bold text** and *italic text*"
        mock_bot.send_message.return_value = AsyncMock(message_id=1)

        # Act
        result = await telegram_service.send_formatted_message(mock_bot, chat_id, message)

        # Assert
        assert result is not None
        mock_bot.send_message.assert_called_once()

    @pytest.mark.asyncio
    async def test_setup_webhook_success(self, telegram_service, mock_bot):
        """Test successful webhook setup."""
        # Arrange
        webhook_url = "https://example.com/webhook"
        mock_bot.set_webhook.return_value = AsyncMock(ok=True)

        # Act
        result = await telegram_service.setup_webhook(mock_bot, webhook_url)

        # Assert
        assert result is True
        mock_bot.set_webhook.assert_called_once_with(url=webhook_url)

    @pytest.mark.asyncio
    async def test_setup_webhook_error(self, telegram_service, mock_bot):
        """Test webhook setup with error."""
        # Arrange
        webhook_url = "https://example.com/webhook"
        mock_bot.set_webhook.side_effect = Exception("Webhook setup failed")

        # Act & Assert
        with pytest.raises(TelegramError):
            await telegram_service.setup_webhook(mock_bot, webhook_url)

    @pytest.mark.asyncio
    async def test_delete_webhook_success(self, telegram_service, mock_bot):
        """Test successful webhook deletion."""
        # Arrange
        mock_bot.delete_webhook.return_value = AsyncMock(ok=True)

        # Act
        result = await telegram_service.delete_webhook(mock_bot)

        # Assert
        assert result is True
        mock_bot.delete_webhook.assert_called_once()

    @pytest.mark.asyncio
    async def test_get_webhook_info_success(self, telegram_service, mock_bot):
        """Test successful webhook info retrieval."""
        # Arrange
        mock_info = {"url": "https://example.com/webhook", "has_custom_certificate": False}
        mock_bot.get_webhook_info.return_value = AsyncMock(**mock_info)

        # Act
        result = await telegram_service.get_webhook_info(mock_bot)

        # Assert
        assert result is not None
        mock_bot.get_webhook_info.assert_called_once()

    @pytest.mark.asyncio
    async def test_handle_start_command(self, telegram_service, mock_bot, mock_db_session):
        """Test handling start command."""
        # Arrange
        chat_id = 123456789
        user_data = UserCreateFactory.build()
        mock_db_session.execute = AsyncMock()
        mock_result = AsyncMock()
        mock_result.scalar_one_or_none.return_value = None
        mock_db_session.execute.return_value = mock_result
        mock_db_session.add = AsyncMock()
        mock_db_session.commit = AsyncMock()
        mock_db_session.refresh = AsyncMock()

        with patch.object(telegram_service, 'send_message', return_value=AsyncMock()):
            # Act
            result = await telegram_service.handle_start_command(mock_bot, chat_id, user_data, mock_db_session)

            # Assert
            assert result is not None
            mock_db_session.add.assert_called_once()
            mock_db_session.commit.assert_called_once()

    @pytest.mark.asyncio
    async def test_handle_help_command(self, telegram_service, mock_bot):
        """Test handling help command."""
        # Arrange
        chat_id = 123456789

        with patch.object(telegram_service, 'send_message', return_value=AsyncMock()) as mock_send:
            # Act
            result = await telegram_service.handle_help_command(mock_bot, chat_id)

            # Assert
            assert result is not None
            mock_send.assert_called_once()

    @pytest.mark.asyncio
    async def test_handle_settings_command(self, telegram_service, mock_bot, mock_db_session):
        """Test handling settings command."""
        # Arrange
        chat_id = 123456789
        user_data = UserCreateFactory.build()
        mock_db_session.execute = AsyncMock()
        mock_result = AsyncMock()
        mock_result.scalar_one_or_none.return_value = user_data
        mock_db_session.execute.return_value = mock_result

        with patch.object(telegram_service, 'send_message', return_value=AsyncMock()):
            # Act
            result = await telegram_service.handle_settings_command(mock_bot, chat_id, mock_db_session)

            # Assert
            assert result is not None

    @pytest.mark.asyncio
    async def test_handle_currency_selection(self, telegram_service, mock_bot, mock_db_session):
        """Test handling currency selection."""
        # Arrange
        chat_id = 123456789
        currency = "USD"
        user_data = UserCreateFactory.build()
        mock_db_session.execute = AsyncMock()
        mock_result = AsyncMock()
        mock_result.scalar_one_or_none.return_value = user_data
        mock_db_session.execute.return_value = mock_result
        mock_db_session.commit = AsyncMock()

        with patch.object(telegram_service, 'send_message', return_value=AsyncMock()):
            # Act
            result = await telegram_service.handle_currency_selection(mock_bot, chat_id, currency, mock_db_session)

            # Assert
            assert result is not None
            mock_db_session.commit.assert_called_once()

    @pytest.mark.asyncio
    async def test_handle_impact_level_selection(self, telegram_service, mock_bot, mock_db_session):
        """Test handling impact level selection."""
        # Arrange
        chat_id = 123456789
        impact_level = "high"
        user_data = UserCreateFactory.build()
        mock_db_session.execute = AsyncMock()
        mock_result = AsyncMock()
        mock_result.scalar_one_or_none.return_value = user_data
        mock_db_session.execute.return_value = mock_result
        mock_db_session.commit = AsyncMock()

        with patch.object(telegram_service, 'send_message', return_value=AsyncMock()):
            # Act
            result = await telegram_service.handle_impact_level_selection(mock_bot, chat_id, impact_level, mock_db_session)

            # Assert
            assert result is not None
            mock_db_session.commit.assert_called_once()

    @pytest.mark.asyncio
    async def test_handle_timezone_selection(self, telegram_service, mock_bot, mock_db_session):
        """Test handling timezone selection."""
        # Arrange
        chat_id = 123456789
        timezone = "Europe/Prague"
        user_data = UserCreateFactory.build()
        mock_db_session.execute = AsyncMock()
        mock_result = AsyncMock()
        mock_result.scalar_one_or_none.return_value = user_data
        mock_db_session.execute.return_value = mock_result
        mock_db_session.commit = AsyncMock()

        with patch.object(telegram_service, 'send_message', return_value=AsyncMock()):
            # Act
            result = await telegram_service.handle_timezone_selection(mock_bot, chat_id, timezone, mock_db_session)

            # Assert
            assert result is not None
            mock_db_session.commit.assert_called_once()

    @pytest.mark.asyncio
    async def test_handle_notification_toggle(self, telegram_service, mock_bot, mock_db_session):
        """Test handling notification toggle."""
        # Arrange
        chat_id = 123456789
        user_data = UserCreateFactory.build()
        mock_db_session.execute = AsyncMock()
        mock_result = AsyncMock()
        mock_result.scalar_one_or_none.return_value = user_data
        mock_db_session.execute.return_value = mock_result
        mock_db_session.commit = AsyncMock()

        with patch.object(telegram_service, 'send_message', return_value=AsyncMock()):
            # Act
            result = await telegram_service.handle_notification_toggle(mock_bot, chat_id, mock_db_session)

            # Assert
            assert result is not None
            mock_db_session.commit.assert_called_once()

    @pytest.mark.asyncio
    async def test_handle_chart_toggle(self, telegram_service, mock_bot, mock_db_session):
        """Test handling chart toggle."""
        # Arrange
        chat_id = 123456789
        user_data = UserCreateFactory.build()
        mock_db_session.execute = AsyncMock()
        mock_result = AsyncMock()
        mock_result.scalar_one_or_none.return_value = user_data
        mock_db_session.execute.return_value = mock_result
        mock_db_session.commit = AsyncMock()

        with patch.object(telegram_service, 'send_message', return_value=AsyncMock()):
            # Act
            result = await telegram_service.handle_chart_toggle(mock_bot, chat_id, mock_db_session)

            # Assert
            assert result is not None
            mock_db_session.commit.assert_called_once()

    @pytest.mark.asyncio
    async def test_handle_unknown_command(self, telegram_service, mock_bot):
        """Test handling unknown command."""
        # Arrange
        chat_id = 123456789
        command = "/unknown"

        with patch.object(telegram_service, 'send_message', return_value=AsyncMock()):
            # Act
            result = await telegram_service.handle_unknown_command(mock_bot, chat_id, command)

            # Assert
            assert result is not None

    @pytest.mark.asyncio
    async def test_validation_error_handling(self, telegram_service, mock_bot):
        """Test validation error handling."""
        # Arrange
        chat_id = None  # Invalid chat ID
        message = "Test message"

        # Act & Assert
        with pytest.raises(ValidationError):
            await telegram_service.send_message(mock_bot, chat_id, message)

    @pytest.mark.asyncio
    async def test_telegram_error_handling(self, telegram_service, mock_bot):
        """Test telegram error handling."""
        # Arrange
        chat_id = 123456789
        message = "Test message"
        mock_bot.send_message.side_effect = Exception("Telegram API error")

        # Act & Assert
        with pytest.raises(TelegramError):
            await telegram_service.send_message(mock_bot, chat_id, message)
