"""Tests for cache service."""

import pytest
import pytest_asyncio
from unittest.mock import AsyncMock, patch, MagicMock
import json

from app.services.cache_service import CacheService
from app.core.exceptions import CacheError


class TestCacheService:
    """Test cases for CacheService."""

    @pytest_asyncio.fixture
    async def cache_service(self):
        """Create cache service instance."""
        return CacheService()

    @pytest_asyncio.fixture
    async def mock_redis(self):
        """Create mock Redis client."""
        mock_redis = AsyncMock()
        mock_redis.get.return_value = None
        mock_redis.set.return_value = True
        mock_redis.delete.return_value = True
        mock_redis.exists.return_value = False
        mock_redis.ping.return_value = True
        mock_redis.close.return_value = None
        return mock_redis

    @pytest.mark.asyncio
    async def test_initialize_success(self, cache_service, mock_redis):
        """Test successful cache service initialization."""
        # Arrange
        with patch('redis.asyncio.from_url', return_value=mock_redis):
            # Act
            await cache_service.initialize()

            # Assert
            assert cache_service.redis is not None
            mock_redis.ping.assert_called_once()

    @pytest.mark.asyncio
    async def test_initialize_connection_error(self, cache_service):
        """Test cache service initialization with connection error."""
        # Arrange
        with patch('redis.asyncio.from_url', side_effect=Exception("Connection failed")):
            # Act & Assert
            with pytest.raises(CacheError):
                await cache_service.initialize()

    @pytest.mark.asyncio
    async def test_close_success(self, cache_service, mock_redis):
        """Test successful cache service close."""
        # Arrange
        cache_service.redis = mock_redis

        # Act
        await cache_service.close()

        # Assert
        mock_redis.close.assert_called_once()

    @pytest.mark.asyncio
    async def test_close_no_redis(self, cache_service):
        """Test cache service close when Redis is not initialized."""
        # Arrange
        cache_service.redis = None

        # Act
        await cache_service.close()

        # Assert
        # Should not raise any exception

    @pytest.mark.asyncio
    async def test_get_success(self, cache_service, mock_redis):
        """Test successful cache get operation."""
        # Arrange
        cache_service.redis = mock_redis
        key = "test_key"
        value = {"data": "test_value"}
        mock_redis.get.return_value = json.dumps(value)

        # Act
        result = await cache_service.get(key)

        # Assert
        assert result == value
        mock_redis.get.assert_called_once_with(key)

    @pytest.mark.asyncio
    async def test_get_not_found(self, cache_service, mock_redis):
        """Test cache get operation when key not found."""
        # Arrange
        cache_service.redis = mock_redis
        key = "nonexistent_key"
        mock_redis.get.return_value = None

        # Act
        result = await cache_service.get(key)

        # Assert
        assert result is None
        mock_redis.get.assert_called_once_with(key)

    @pytest.mark.asyncio
    async def test_get_invalid_json(self, cache_service, mock_redis):
        """Test cache get operation with invalid JSON."""
        # Arrange
        cache_service.redis = mock_redis
        key = "invalid_key"
        mock_redis.get.return_value = "invalid json"

        # Act & Assert
        with pytest.raises(CacheError):
            await cache_service.get(key)

    @pytest.mark.asyncio
    async def test_set_success(self, cache_service, mock_redis):
        """Test successful cache set operation."""
        # Arrange
        cache_service.redis = mock_redis
        key = "test_key"
        value = {"data": "test_value"}
        expire = 3600

        # Act
        result = await cache_service.set(key, value, expire)

        # Assert
        assert result is True
        mock_redis.set.assert_called_once_with(key, json.dumps(value), ex=expire)

    @pytest.mark.asyncio
    async def test_set_without_expire(self, cache_service, mock_redis):
        """Test cache set operation without expiration."""
        # Arrange
        cache_service.redis = mock_redis
        key = "test_key"
        value = {"data": "test_value"}

        # Act
        result = await cache_service.set(key, value)

        # Assert
        assert result is True
        mock_redis.set.assert_called_once_with(key, json.dumps(value), ex=None)

    @pytest.mark.asyncio
    async def test_set_error(self, cache_service, mock_redis):
        """Test cache set operation with error."""
        # Arrange
        cache_service.redis = mock_redis
        key = "test_key"
        value = {"data": "test_value"}
        mock_redis.set.side_effect = Exception("Redis error")

        # Act & Assert
        with pytest.raises(CacheError):
            await cache_service.set(key, value)

    @pytest.mark.asyncio
    async def test_delete_success(self, cache_service, mock_redis):
        """Test successful cache delete operation."""
        # Arrange
        cache_service.redis = mock_redis
        key = "test_key"
        mock_redis.delete.return_value = True

        # Act
        result = await cache_service.delete(key)

        # Assert
        assert result is True
        mock_redis.delete.assert_called_once_with(key)

    @pytest.mark.asyncio
    async def test_delete_error(self, cache_service, mock_redis):
        """Test cache delete operation with error."""
        # Arrange
        cache_service.redis = mock_redis
        key = "test_key"
        mock_redis.delete.side_effect = Exception("Redis error")

        # Act & Assert
        with pytest.raises(CacheError):
            await cache_service.delete(key)

    @pytest.mark.asyncio
    async def test_exists_success(self, cache_service, mock_redis):
        """Test successful cache exists operation."""
        # Arrange
        cache_service.redis = mock_redis
        key = "test_key"
        mock_redis.exists.return_value = True

        # Act
        result = await cache_service.exists(key)

        # Assert
        assert result is True
        mock_redis.exists.assert_called_once_with(key)

    @pytest.mark.asyncio
    async def test_exists_error(self, cache_service, mock_redis):
        """Test cache exists operation with error."""
        # Arrange
        cache_service.redis = mock_redis
        key = "test_key"
        mock_redis.exists.side_effect = Exception("Redis error")

        # Act & Assert
        with pytest.raises(CacheError):
            await cache_service.exists(key)

    @pytest.mark.asyncio
    async def test_cache_result_decorator_success(self, cache_service, mock_redis):
        """Test successful cache_result decorator."""
        # Arrange
        cache_service.redis = mock_redis
        mock_redis.get.return_value = None
        mock_redis.set.return_value = True

        @cache_service.cache_result(expire=3600)
        async def test_function(param1: str, param2: int):
            return {"result": f"{param1}_{param2}"}

        # Act
        result = await test_function("test", 123)

        # Assert
        assert result == {"result": "test_123"}
        mock_redis.set.assert_called_once()

    @pytest.mark.asyncio
    async def test_cache_result_decorator_cache_hit(self, cache_service, mock_redis):
        """Test cache_result decorator with cache hit."""
        # Arrange
        cache_service.redis = mock_redis
        cached_value = {"result": "cached_value"}
        mock_redis.get.return_value = json.dumps(cached_value)

        @cache_service.cache_result(expire=3600)
        async def test_function(param1: str, param2: int):
            return {"result": f"{param1}_{param2}"}

        # Act
        result = await test_function("test", 123)

        # Assert
        assert result == cached_value
        mock_redis.get.assert_called_once()

    @pytest.mark.asyncio
    async def test_cache_result_decorator_error(self, cache_service, mock_redis):
        """Test cache_result decorator with error."""
        # Arrange
        cache_service.redis = mock_redis
        mock_redis.get.side_effect = Exception("Redis error")

        @cache_service.cache_result(expire=3600)
        async def test_function(param1: str, param2: int):
            return {"result": f"{param1}_{param2}"}

        # Act & Assert
        with pytest.raises(Exception):
            await test_function("test", 123)

    @pytest.mark.asyncio
    async def test_health_check_success(self, cache_service, mock_redis):
        """Test successful health check."""
        # Arrange
        cache_service.redis = mock_redis
        mock_redis.ping.return_value = True

        # Act
        result = await cache_service.health_check()

        # Assert
        assert result["status"] == "healthy"
        assert result["redis"] == "connected"

    @pytest.mark.asyncio
    async def test_health_check_redis_error(self, cache_service, mock_redis):
        """Test health check with Redis error."""
        # Arrange
        cache_service.redis = mock_redis
        mock_redis.ping.side_effect = Exception("Redis error")

        # Act
        result = await cache_service.health_check()

        # Assert
        assert result["status"] == "unhealthy"
        assert result["redis"] == "disconnected"

    @pytest.mark.asyncio
    async def test_health_check_no_redis(self, cache_service):
        """Test health check when Redis is not initialized."""
        # Arrange
        cache_service.redis = None

        # Act
        result = await cache_service.health_check()

        # Assert
        assert result["status"] == "unhealthy"
        assert result["redis"] == "not_initialized"

    @pytest.mark.asyncio
    async def test_clear_cache_success(self, cache_service, mock_redis):
        """Test successful cache clear operation."""
        # Arrange
        cache_service.redis = mock_redis
        mock_redis.flushdb.return_value = True

        # Act
        result = await cache_service.clear_cache()

        # Assert
        assert result is True
        mock_redis.flushdb.assert_called_once()

    @pytest.mark.asyncio
    async def test_clear_cache_error(self, cache_service, mock_redis):
        """Test cache clear operation with error."""
        # Arrange
        cache_service.redis = mock_redis
        mock_redis.flushdb.side_effect = Exception("Redis error")

        # Act & Assert
        with pytest.raises(CacheError):
            await cache_service.clear_cache()

    @pytest.mark.asyncio
    async def test_get_cache_stats_success(self, cache_service, mock_redis):
        """Test successful cache stats retrieval."""
        # Arrange
        cache_service.redis = mock_redis
        mock_redis.info.return_value = {
            "used_memory": 1024,
            "connected_clients": 1,
            "keyspace_hits": 100,
            "keyspace_misses": 50
        }

        # Act
        result = await cache_service.get_cache_stats()

        # Assert
        assert "memory_usage" in result
        assert "connected_clients" in result
        assert "hit_rate" in result
        mock_redis.info.assert_called_once()

    @pytest.mark.asyncio
    async def test_get_cache_stats_error(self, cache_service, mock_redis):
        """Test cache stats retrieval with error."""
        # Arrange
        cache_service.redis = mock_redis
        mock_redis.info.side_effect = Exception("Redis error")

        # Act & Assert
        with pytest.raises(CacheError):
            await cache_service.get_cache_stats()
