"""Tests for health check endpoints."""

import pytest
import pytest_asyncio
from unittest.mock import AsyncMock, patch
from fastapi.testclient import TestClient
from httpx import AsyncClient

from app.main import app


class TestHealthEndpoints:
    """Test cases for health check endpoints."""

    @pytest_asyncio.fixture
    async def async_client(self, test_client: AsyncClient):
        """Create async test client."""
        return test_client

    @pytest.mark.asyncio
    async def test_health_check_success(self, async_client: AsyncClient):
        """Test successful basic health check."""
        # Act
        response = await async_client.get("/api/v1/health/health")

        # Assert
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "healthy"
        assert "timestamp" in data
        assert "version" in data
        assert "environment" in data

    @pytest.mark.asyncio
    async def test_detailed_health_check_success(self, async_client: AsyncClient):
        """Test successful detailed health check."""
        # Act
        response = await async_client.get("/api/v1/health/detailed")

        # Assert
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "healthy"
        assert "components" in data
        assert "database" in data["components"]

    @pytest.mark.asyncio
    async def test_detailed_health_check_database_error(self, async_client: AsyncClient):
        """Test detailed health check with database error."""
        # Arrange
        with patch('app.database.connection.db_manager.get_session_async') as mock_get_session:
            mock_session = AsyncMock()
            mock_session.execute.side_effect = Exception("Database error")
            mock_get_session.return_value.__aenter__.return_value = mock_session

            # Act
            response = await async_client.get("/api/v1/health/detailed")

            # Assert
            assert response.status_code == 503
            data = response.json()
            assert data["status"] == "unhealthy"
            assert data["components"]["database"]["status"] == "unhealthy"

    @pytest.mark.asyncio
    async def test_readiness_check_success(self, async_client: AsyncClient):
        """Test successful readiness check."""
        # Act
        response = await async_client.get("/api/v1/health/ready")

        # Assert
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "ready"
        assert "timestamp" in data

    @pytest.mark.asyncio
    async def test_readiness_check_database_error(self, async_client: AsyncClient):
        """Test readiness check with database error."""
        # Arrange
        with patch('app.database.connection.db_manager.get_session_async') as mock_get_session:
            mock_session = AsyncMock()
            mock_session.execute.side_effect = Exception("Database error")
            mock_get_session.return_value.__aenter__.return_value = mock_session

            # Act
            response = await async_client.get("/api/v1/health/ready")

            # Assert
            assert response.status_code == 503
            data = response.json()
            assert data["status"] == "not_ready"

    @pytest.mark.asyncio
    async def test_liveness_check_success(self, async_client: AsyncClient):
        """Test successful liveness check."""
        # Act
        response = await async_client.get("/api/v1/health/live")

        # Assert
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "alive"
        assert "timestamp" in data
        assert "uptime" in data

    @pytest.mark.asyncio
    async def test_metrics_endpoint_success(self, async_client: AsyncClient):
        """Test successful metrics endpoint."""
        # Act
        response = await async_client.get("/api/v1/health/metrics")

        # Assert
        assert response.status_code == 200
        data = response.json()
        assert "status" in data or "metrics" in data

    @pytest.mark.asyncio
    async def test_metrics_endpoint_no_prometheus(self, async_client: AsyncClient):
        """Test metrics endpoint without Prometheus client."""
        # Arrange
        with patch('prometheus_client.generate_latest', side_effect=ImportError):
            # Act
            response = await async_client.get("/api/v1/health/metrics")

            # Assert
            assert response.status_code == 200
            data = response.json()
            assert data["status"] == "metrics_not_available"
            assert "Prometheus client not installed" in data["message"]

    @pytest.mark.asyncio
    async def test_health_check_redis_configured(self, async_client: AsyncClient):
        """Test health check with Redis configured."""
        # Arrange
        with patch('app.core.config.settings.redis.url', "redis://localhost:6379"):
            with patch('redis.asyncio.from_url') as mock_redis:
                mock_redis_client = AsyncMock()
                mock_redis_client.ping.return_value = True
                mock_redis_client.close.return_value = None
                mock_redis.return_value = mock_redis_client

                # Act
                response = await async_client.get("/api/v1/health/detailed")

                # Assert
                assert response.status_code == 200
                data = response.json()
                assert data["components"]["redis"]["status"] == "healthy"

    @pytest.mark.asyncio
    async def test_health_check_redis_error(self, async_client: AsyncClient):
        """Test health check with Redis error."""
        # Arrange
        with patch('app.core.config.settings.redis.url', "redis://localhost:6379"):
            with patch('redis.asyncio.from_url') as mock_redis:
                mock_redis_client = AsyncMock()
                mock_redis_client.ping.side_effect = Exception("Redis error")
                mock_redis_client.close.return_value = None
                mock_redis.return_value = mock_redis_client

                # Act
                response = await async_client.get("/api/v1/health/detailed")

                # Assert
                assert response.status_code == 503
                data = response.json()
                assert data["components"]["redis"]["status"] == "unhealthy"

    @pytest.mark.asyncio
    async def test_health_check_openai_configured(self, async_client: AsyncClient):
        """Test health check with OpenAI configured."""
        # Arrange
        with patch('app.core.config.settings.api.openai_api_key', "test-key"):
            # Act
            response = await async_client.get("/api/v1/health/detailed")

            # Assert
            assert response.status_code == 200
            data = response.json()
            assert data["components"]["openai"]["status"] == "configured"

    @pytest.mark.asyncio
    async def test_health_check_openai_not_configured(self, async_client: AsyncClient):
        """Test health check with OpenAI not configured."""
        # Arrange
        with patch('app.core.config.settings.api.openai_api_key', None):
            # Act
            response = await async_client.get("/api/v1/health/detailed")

            # Assert
            assert response.status_code == 200
            data = response.json()
            assert data["components"]["openai"]["status"] == "not_configured"

    @pytest.mark.asyncio
    async def test_health_check_openai_error(self, async_client: AsyncClient):
        """Test health check with OpenAI error."""
        # Arrange
        with patch('app.core.config.settings.api.openai_api_key', "test-key"):
            with patch('app.core.config.settings.api.openai_api_key', side_effect=Exception("OpenAI error")):
                # Act
                response = await async_client.get("/api/v1/health/detailed")

                # Assert
                assert response.status_code == 200
                data = response.json()
                assert data["components"]["openai"]["status"] == "error"

    @pytest.mark.asyncio
    async def test_health_check_endpoints_exist(self, async_client: AsyncClient):
        """Test that all health check endpoints exist."""
        # Act & Assert
        endpoints = [
            "/api/v1/health/health",
            "/api/v1/health/detailed",
            "/api/v1/health/ready",
            "/api/v1/health/live",
            "/api/v1/health/metrics"
        ]

        for endpoint in endpoints:
            response = await async_client.get(endpoint)
            assert response.status_code in [200, 503]  # Either healthy or unhealthy
