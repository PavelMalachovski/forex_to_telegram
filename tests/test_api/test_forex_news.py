"""Tests for forex news API endpoints."""

import pytest
from unittest.mock import AsyncMock, patch
from httpx import AsyncClient
from datetime import date, datetime

from app.models.forex_news import ForexNewsCreate, ForexNewsUpdate
from tests.factories import ForexNewsCreateFactory, ForexNewsModelFactory


@pytest.fixture
def sample_forex_news_data():
    """Sample forex news data for testing."""
    return ForexNewsCreateFactory.build()


@pytest.fixture
def sample_forex_news_model():
    """Sample forex news model for testing."""
    return ForexNewsModelFactory.build()


@pytest.mark.asyncio
async def test_create_forex_news_success(test_client: AsyncClient, sample_forex_news_data):
    """Test successful forex news creation via API."""
    # Arrange
    with patch('app.api.v1.endpoints.forex_news.forex_service') as mock_service:
        mock_service.create_forex_news.return_value = ForexNewsModelFactory.build()

        # Act
        response = await test_client.post(
            "/api/v1/forex-news/",
            json=sample_forex_news_data.model_dump()
        )

    # Assert
    assert response.status_code == 201
    data = response.json()
    assert "id" in data
    assert data["currency"] == sample_forex_news_data.currency
    assert data["event"] == sample_forex_news_data.event

    @pytest.mark.asyncio
    async def test_create_forex_news_validation_error(self, test_client: AsyncClient):
        """Test forex news creation with validation error."""
        # Arrange
        invalid_data = {
            "currency": "INVALID",  # Invalid currency
            "event": "",  # Empty event
            "impact_level": "invalid"  # Invalid impact level
        }

        # Act
        response = await test_client.post("/api/v1/forex-news/", json=invalid_data)

        # Assert
        assert response.status_code == 422

    @pytest.mark.asyncio
    async def test_get_forex_news_by_id_success(self, test_client: AsyncClient, sample_forex_news_model):
        """Test successful forex news retrieval by ID."""
        # Arrange
        with patch('app.api.v1.endpoints.forex_news.forex_service') as mock_service:
            mock_service.get_forex_news_by_id.return_value = sample_forex_news_model

            # Act
            response = await test_client.get(f"/api/v1/forex-news/{sample_forex_news_model.id}")

        # Assert
        assert response.status_code == 200
        data = response.json()
        assert data["id"] == sample_forex_news_model.id
        assert data["currency"] == sample_forex_news_model.currency

    @pytest.mark.asyncio
    async def test_get_forex_news_by_id_not_found(self, test_client: AsyncClient):
        """Test forex news retrieval when not found."""
        # Arrange
        with patch('app.api.v1.endpoints.forex_news.forex_service') as mock_service:
            mock_service.get_forex_news_by_id.return_value = None

            # Act
            response = await test_client.get("/api/v1/forex-news/999")

        # Assert
        assert response.status_code == 404

    @pytest.mark.asyncio
    async def test_get_forex_news_by_date_range(self, test_client: AsyncClient):
        """Test getting forex news by date range."""
        # Arrange
        start_date = "2024-01-01"
        end_date = "2024-01-31"
        news_items = [ForexNewsModelFactory.build() for _ in range(3)]

        with patch('app.api.v1.endpoints.forex_news.forex_service') as mock_service:
            mock_service.get_forex_news_by_date_range.return_value = news_items

            # Act
            response = await test_client.get(
                f"/api/v1/forex-news/by-date-range?start_date={start_date}&end_date={end_date}"
            )

        # Assert
        assert response.status_code == 200
        data = response.json()
        assert len(data) == 3

    @pytest.mark.asyncio
    async def test_get_forex_news_by_currency(self, test_client: AsyncClient):
        """Test getting forex news by currency."""
        # Arrange
        currency = "USD"
        news_items = [ForexNewsModelFactory.build(currency=currency) for _ in range(2)]

        with patch('app.api.v1.endpoints.forex_news.forex_service') as mock_service:
            mock_service.get_forex_news_by_currency.return_value = news_items

            # Act
            response = await test_client.get(f"/api/v1/forex-news/by-currency/{currency}")

        # Assert
        assert response.status_code == 200
        data = response.json()
        assert len(data) == 2
        assert all(item["currency"] == currency for item in data)

    @pytest.mark.asyncio
    async def test_get_forex_news_by_impact_level(self, test_client: AsyncClient):
        """Test getting forex news by impact level."""
        # Arrange
        impact_level = "high"
        news_items = [ForexNewsModelFactory.build(impact_level=impact_level) for _ in range(2)]

        with patch('app.api.v1.endpoints.forex_news.forex_service') as mock_service:
            mock_service.get_forex_news_by_impact_level.return_value = news_items

            # Act
            response = await test_client.get(f"/api/v1/forex-news/by-impact/{impact_level}")

        # Assert
        assert response.status_code == 200
        data = response.json()
        assert len(data) == 2
        assert all(item["impact_level"] == impact_level for item in data)

    @pytest.mark.asyncio
    async def test_get_todays_forex_news(self, test_client: AsyncClient):
        """Test getting today's forex news."""
        # Arrange
        news_items = [ForexNewsModelFactory.build() for _ in range(4)]

        with patch('app.api.v1.endpoints.forex_news.forex_service') as mock_service:
            mock_service.get_todays_forex_news.return_value = news_items

            # Act
            response = await test_client.get("/api/v1/forex-news/today")

        # Assert
        assert response.status_code == 200
        data = response.json()
        assert len(data) == 4

    @pytest.mark.asyncio
    async def test_get_upcoming_events(self, test_client: AsyncClient):
        """Test getting upcoming forex events."""
        # Arrange
        news_items = [ForexNewsModelFactory.build() for _ in range(3)]

        with patch('app.api.v1.endpoints.forex_news.forex_service') as mock_service:
            mock_service.get_upcoming_events.return_value = news_items

            # Act
            response = await test_client.get("/api/v1/forex-news/upcoming?hours=24")

        # Assert
        assert response.status_code == 200
        data = response.json()
        assert len(data) == 3

    @pytest.mark.asyncio
    async def test_update_forex_news_success(self, test_client: AsyncClient, sample_forex_news_model):
        """Test successful forex news update."""
        # Arrange
        update_data = {"analysis": "Updated analysis"}

        with patch('app.api.v1.endpoints.forex_news.forex_service') as mock_service:
            mock_service.update_forex_news.return_value = sample_forex_news_model

            # Act
            response = await test_client.put(
                f"/api/v1/forex-news/{sample_forex_news_model.id}",
                json=update_data
            )

        # Assert
        assert response.status_code == 200
        data = response.json()
        assert data["id"] == sample_forex_news_model.id

    @pytest.mark.asyncio
    async def test_update_forex_news_not_found(self, test_client: AsyncClient):
        """Test forex news update when not found."""
        # Arrange
        update_data = {"analysis": "Updated analysis"}

        with patch('app.api.v1.endpoints.forex_news.forex_service') as mock_service:
            mock_service.update_forex_news.side_effect = ValidationError("Forex news not found")

            # Act
            response = await test_client.put("/api/v1/forex-news/999", json=update_data)

        # Assert
        assert response.status_code == 400

    @pytest.mark.asyncio
    async def test_delete_forex_news_success(self, test_client: AsyncClient):
        """Test successful forex news deletion."""
        # Arrange
        with patch('app.api.v1.endpoints.forex_news.forex_service') as mock_service:
            mock_service.delete_forex_news.return_value = True

            # Act
            response = await test_client.delete("/api/v1/forex-news/1")

        # Assert
        assert response.status_code == 204

    @pytest.mark.asyncio
    async def test_delete_forex_news_not_found(self, test_client: AsyncClient):
        """Test forex news deletion when not found."""
        # Arrange
        with patch('app.api.v1.endpoints.forex_news.forex_service') as mock_service:
            mock_service.delete_forex_news.side_effect = ValidationError("Forex news not found")

            # Act
            response = await test_client.delete("/api/v1/forex-news/999")

        # Assert
        assert response.status_code == 400

    @pytest.mark.asyncio
    async def test_get_forex_news_with_pagination(self, test_client: AsyncClient):
        """Test getting forex news with pagination."""
        # Arrange
        news_items = [ForexNewsModelFactory.build() for _ in range(5)]

        with patch('app.api.v1.endpoints.forex_news.forex_service') as mock_service:
            mock_service.get_all_forex_news.return_value = news_items

            # Act
            response = await test_client.get("/api/v1/forex-news/?skip=0&limit=10")

        # Assert
        assert response.status_code == 200
        data = response.json()
        assert len(data) == 5

    @pytest.mark.asyncio
    async def test_get_forex_news_with_filters(self, test_client: AsyncClient):
        """Test getting forex news with multiple filters."""
        # Arrange
        news_items = [ForexNewsModelFactory.build() for _ in range(2)]

        with patch('app.api.v1.endpoints.forex_news.forex_service') as mock_service:
            mock_service.get_forex_news_with_filters.return_value = news_items

            # Act
            response = await test_client.get(
                "/api/v1/forex-news/filtered?currency=USD&impact_level=high"
            )

        # Assert
        assert response.status_code == 200
        data = response.json()
        assert len(data) == 2

    @pytest.mark.asyncio
    async def test_bulk_create_forex_news(self, test_client: AsyncClient):
        """Test bulk creation of forex news."""
        # Arrange
        news_data_list = [ForexNewsCreateFactory.build() for _ in range(3)]
        created_models = [ForexNewsModelFactory.build() for _ in range(3)]

        with patch('app.api.v1.endpoints.forex_news.forex_service') as mock_service:
            mock_service.bulk_create_forex_news.return_value = created_models

            # Act
            response = await test_client.post(
                "/api/v1/forex-news/bulk",
                json=[item.model_dump() for item in news_data_list]
            )

        # Assert
        assert response.status_code == 201
        data = response.json()
        assert len(data) == 3
