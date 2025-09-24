"""Redis caching service for performance optimization."""

import json
import asyncio
from typing import Any, Optional, Union, Callable
from functools import wraps
from datetime import timedelta
import redis.asyncio as redis
from redis.exceptions import RedisError

from app.core.config import settings
from app.core.logging import get_logger
from app.core.exceptions import ExternalAPIError

logger = get_logger(__name__)


class CacheService:
    """Redis-based caching service."""

    def __init__(self):
        self.redis_client: Optional[redis.Redis] = None
        self._initialized = False

    async def initialize(self) -> None:
        """Initialize Redis connection."""
        if self._initialized:
            return

        try:
            if not settings.redis.url:
                logger.warning("Redis URL not configured, caching disabled")
                return

            self.redis_client = redis.from_url(
                settings.redis.url,
                max_connections=settings.redis.max_connections,
                decode_responses=True
            )

            # Test connection
            await self.redis_client.ping()
            self._initialized = True
            logger.info("Redis cache service initialized successfully")

        except Exception as e:
            logger.error("Failed to initialize Redis cache service", error=str(e))
            self.redis_client = None

    async def close(self) -> None:
        """Close Redis connection."""
        if self.redis_client:
            await self.redis_client.close()
            self._initialized = False
            logger.info("Redis cache service closed")

    def _serialize_value(self, value: Any) -> str:
        """Serialize value for storage."""
        if isinstance(value, (str, int, float, bool)):
            return json.dumps(value)
        return json.dumps(value, default=str)

    def _deserialize_value(self, value: str) -> Any:
        """Deserialize value from storage."""
        try:
            return json.loads(value)
        except (json.JSONDecodeError, TypeError):
            return value

    async def get(self, key: str) -> Optional[Any]:
        """
        Get value from cache.

        Args:
            key: Cache key

        Returns:
            Cached value or None if not found
        """
        if not self._initialized or not self.redis_client:
            return None

        try:
            value = await self.redis_client.get(key)
            if value is not None:
                logger.debug("Cache hit", key=key)
                return self._deserialize_value(value)
            logger.debug("Cache miss", key=key)
            return None
        except RedisError as e:
            logger.error("Redis get error", key=key, error=str(e))
            return None

    async def set(
        self,
        key: str,
        value: Any,
        ttl: Optional[Union[int, timedelta]] = None
    ) -> bool:
        """
        Set value in cache.

        Args:
            key: Cache key
            value: Value to cache
            ttl: Time to live in seconds or timedelta

        Returns:
            True if successful, False otherwise
        """
        if not self._initialized or not self.redis_client:
            return False

        try:
            serialized_value = self._serialize_value(value)

            if isinstance(ttl, timedelta):
                ttl = int(ttl.total_seconds())

            await self.redis_client.set(key, serialized_value, ex=ttl)
            logger.debug("Cache set", key=key, ttl=ttl)
            return True
        except RedisError as e:
            logger.error("Redis set error", key=key, error=str(e))
            return False

    async def delete(self, key: str) -> bool:
        """
        Delete value from cache.

        Args:
            key: Cache key

        Returns:
            True if successful, False otherwise
        """
        if not self._initialized or not self.redis_client:
            return False

        try:
            result = await self.redis_client.delete(key)
            logger.debug("Cache delete", key=key, deleted=bool(result))
            return bool(result)
        except RedisError as e:
            logger.error("Redis delete error", key=key, error=str(e))
            return False

    async def exists(self, key: str) -> bool:
        """
        Check if key exists in cache.

        Args:
            key: Cache key

        Returns:
            True if key exists, False otherwise
        """
        if not self._initialized or not self.redis_client:
            return False

        try:
            result = await self.redis_client.exists(key)
            return bool(result)
        except RedisError as e:
            logger.error("Redis exists error", key=key, error=str(e))
            return False

    async def get_or_set(
        self,
        key: str,
        func: Callable,
        ttl: Optional[Union[int, timedelta]] = None,
        *args,
        **kwargs
    ) -> Any:
        """
        Get value from cache or set it using provided function.

        Args:
            key: Cache key
            func: Function to call if cache miss
            ttl: Time to live in seconds or timedelta
            *args: Arguments for func
            **kwargs: Keyword arguments for func

        Returns:
            Cached or computed value
        """
        # Try to get from cache first
        cached_value = await self.get(key)
        if cached_value is not None:
            return cached_value

        # Cache miss, compute value
        try:
            if asyncio.iscoroutinefunction(func):
                value = await func(*args, **kwargs)
            else:
                value = func(*args, **kwargs)

            # Store in cache
            await self.set(key, value, ttl)
            return value

        except Exception as e:
            logger.error("Error computing cached value", key=key, error=str(e))
            raise ExternalAPIError(f"Failed to compute cached value: {e}")

    async def invalidate_pattern(self, pattern: str) -> int:
        """
        Invalidate all keys matching pattern.

        Args:
            pattern: Redis key pattern (e.g., "user:*")

        Returns:
            Number of keys deleted
        """
        if not self._initialized or not self.redis_client:
            return 0

        try:
            keys = await self.redis_client.keys(pattern)
            if keys:
                result = await self.redis_client.delete(*keys)
                logger.info("Cache pattern invalidated", pattern=pattern, count=result)
                return result
            return 0
        except RedisError as e:
            logger.error("Redis pattern invalidation error", pattern=pattern, error=str(e))
            return 0

    async def get_stats(self) -> dict:
        """
        Get cache statistics.

        Returns:
            Dict containing cache statistics
        """
        if not self._initialized or not self.redis_client:
            return {"status": "not_initialized"}

        try:
            info = await self.redis_client.info()
            return {
                "status": "healthy",
                "connected_clients": info.get("connected_clients", 0),
                "used_memory": info.get("used_memory_human", "0B"),
                "keyspace_hits": info.get("keyspace_hits", 0),
                "keyspace_misses": info.get("keyspace_misses", 0),
                "total_commands_processed": info.get("total_commands_processed", 0)
            }
        except RedisError as e:
            logger.error("Redis stats error", error=str(e))
            return {"status": "error", "error": str(e)}


# Global cache service instance
cache_service = CacheService()


def cache_result(
    ttl: Optional[Union[int, timedelta]] = None,
    key_prefix: str = "",
    key_builder: Optional[Callable] = None
):
    """
    Decorator for caching function results.

    Args:
        ttl: Time to live in seconds or timedelta
        key_prefix: Prefix for cache key
        key_builder: Custom key builder function

    Returns:
        Decorated function
    """
    def decorator(func):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            # Build cache key
            if key_builder:
                cache_key = key_builder(func.__name__, *args, **kwargs)
            else:
                # Simple key building
                key_parts = [key_prefix, func.__name__]
                if args:
                    key_parts.extend(str(arg) for arg in args)
                if kwargs:
                    key_parts.extend(f"{k}={v}" for k, v in sorted(kwargs.items()))
                cache_key = ":".join(key_parts)

            return await cache_service.get_or_set(cache_key, func, ttl, *args, **kwargs)

        return wrapper
    return decorator


# Cache key builders
def user_cache_key(user_id: int) -> str:
    """Build cache key for user data."""
    return f"user:{user_id}"


def forex_news_cache_key(date_str: str, currency: str = None) -> str:
    """Build cache key for forex news."""
    if currency:
        return f"forex_news:{date_str}:{currency}"
    return f"forex_news:{date_str}"


def chart_cache_key(currency: str, event_time: str, window_hours: int) -> str:
    """Build cache key for chart data."""
    return f"chart:{currency}:{event_time}:{window_hours}h"
