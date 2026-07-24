"""Enterprise cache layer with Redis support and memory fallback."""

from __future__ import annotations

import asyncio
import json
import time
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import Any, Optional, Union
from collections import OrderedDict

try:
    import redis.asyncio as redis
    REDIS_AVAILABLE = True
except ImportError:
    REDIS_AVAILABLE = False


@dataclass
class CacheConfig:
    """Cache configuration."""
    # Redis settings
    redis_url: str = "redis://localhost:6379/0"
    redis_enabled: bool = True
    redis_max_connections: int = 10
    redis_socket_timeout: float = 5.0
    redis_socket_connect_timeout: float = 5.0

    # Memory cache settings
    memory_max_size: int = 10000
    memory_ttl: int = 300  # 5 minutes default

    # TTL settings by data type
    stock_quote_ttl: int = 30           # 30 seconds
    historical_price_ttl: int = 600     # 10 minutes
    currency_rate_ttl: int = 300        # 5 minutes
    supported_currencies_ttl: int = 86400  # 24 hours
    company_info_ttl: int = 3600        # 1 hour
    market_movers_ttl: int = 60         # 1 minute
    news_ttl: int = 300                 # 5 minutes

    # Cache warming
    warming_enabled: bool = True
    warming_interval: int = 300         # 5 minutes
    warming_symbols: list[str] = field(default_factory=lambda: ["AAPL", "GOOGL", "MSFT", "AMZN", "TSLA"])


class CacheBackend(ABC):
    """Abstract cache backend."""

    @abstractmethod
    async def get(self, key: str) -> Optional[Any]:
        """Get value by key."""
        pass

    @abstractmethod
    async def set(self, key: str, value: Any, ttl: int) -> bool:
        """Set value with TTL."""
        pass

    @abstractmethod
    async def delete(self, key: str) -> bool:
        """Delete key."""
        pass

    @abstractmethod
    async def exists(self, key: str) -> bool:
        """Check if key exists."""
        pass

    @abstractmethod
    async def clear(self) -> bool:
        """Clear all keys."""
        pass

    @abstractmethod
    async def get_stats(self) -> dict[str, Any]:
        """Get cache statistics."""
        pass

    @abstractmethod
    async def close(self) -> None:
        """Close connections."""
        pass


class MemoryCacheBackend(CacheBackend):
    """In-memory LRU cache backend."""

    def __init__(self, max_size: int = 10000):
        self._cache: OrderedDict[str, tuple[Any, float]] = OrderedDict()
        self._max_size = max_size
        self._hits = 0
        self._misses = 0
        self._sets = 0
        self._deletes = 0
        self._lock = asyncio.Lock()

    def _is_expired(self, expiry: float) -> bool:
        return time.time() > expiry

    async def get(self, key: str) -> Optional[Any]:
        async with self._lock:
            if key not in self._cache:
                self._misses += 1
                return None

            value, expiry = self._cache[key]
            if self._is_expired(expiry):
                del self._cache[key]
                self._misses += 1
                return None

            # Move to end (LRU)
            self._cache.move_to_end(key)
            self._hits += 1
            return value

    async def set(self, key: str, value: Any, ttl: int) -> bool:
        async with self._lock:
            expiry = time.time() + ttl

            # Remove if exists to update position
            if key in self._cache:
                del self._cache[key]

            # Evict LRU if at max size (only for NEW keys)
            if key not in self._cache and len(self._cache) >= self._max_size:
                self._cache.popitem(last=False)

            self._cache[key] = (value, expiry)
            self._sets += 1
            return True

    async def delete(self, key: str) -> bool:
        async with self._lock:
            if key in self._cache:
                del self._cache[key]
                self._deletes += 1
                return True
            return False

    async def exists(self, key: str) -> bool:
        async with self._lock:
            if key not in self._cache:
                return False

            _, expiry = self._cache[key]
            if self._is_expired(expiry):
                del self._cache[key]
                return False
            return True

    async def clear(self) -> bool:
        async with self._lock:
            self._cache.clear()
            return True

    async def get_stats(self) -> dict[str, Any]:
        async with self._lock:
            total = self._hits + self._misses
            return {
                "type": "memory",
                "size": len(self._cache),
                "max_size": self._max_size,
                "hits": self._hits,
                "misses": self._misses,
                "hit_rate": self._hits / total if total > 0 else 0.0,
                "sets": self._sets,
                "deletes": self._deletes,
            }

    async def close(self) -> None:
        async with self._lock:
            self._cache.clear()


class RedisCacheBackend(CacheBackend):
    """Redis cache backend."""

    def __init__(
        self,
        url: str = "redis://localhost:6379/0",
        max_connections: int = 10,
        socket_timeout: float = 5.0,
        socket_connect_timeout: float = 5.0,
    ):
        if not REDIS_AVAILABLE:
            raise RuntimeError("redis.asyncio not available. Install with: pip install redis")

        self._url = url
        self._pool: Optional[redis.ConnectionPool] = None
        self._client: Optional[redis.Redis] = None
        self._max_connections = max_connections
        self._socket_timeout = socket_timeout
        self._socket_connect_timeout = socket_connect_timeout
        self._hits = 0
        self._misses = 0
        self._sets = 0
        self._deletes = 0

    async def _get_client(self) -> redis.Redis:
        if self._client is None:
            self._pool = redis.ConnectionPool.from_url(
                self._url,
                max_connections=self._max_connections,
                socket_timeout=self._socket_timeout,
                socket_connect_timeout=self._socket_connect_timeout,
                decode_responses=True,
            )
            self._client = redis.Redis(connection_pool=self._pool)
        return self._client

    async def get(self, key: str) -> Optional[Any]:
        try:
            client = await self._get_client()
            value = await client.get(key)
            if value is None:
                self._misses += 1
                return None
            self._hits += 1
            return json.loads(value)
        except Exception:
            self._misses += 1
            return None

    async def set(self, key: str, value: Any, ttl: int) -> bool:
        try:
            client = await self._get_client()
            serialized = json.dumps(value, default=str)
            await client.setex(key, ttl, serialized)
            self._sets += 1
            return True
        except Exception:
            return False

    async def delete(self, key: str) -> bool:
        try:
            client = await self._get_client()
            result = await client.delete(key)
            self._deletes += 1
            return result > 0
        except Exception:
            return False

    async def exists(self, key: str) -> bool:
        try:
            client = await self._get_client()
            return await client.exists(key) > 0
        except Exception:
            return False

    async def clear(self) -> bool:
        try:
            client = await self._get_client()
            await client.flushdb()
            return True
        except Exception:
            return False

    async def get_stats(self) -> dict[str, Any]:
        try:
            client = await self._get_client()
            info = await client.info("memory")
            total = self._hits + self._misses
            return {
                "type": "redis",
                "connected": True,
                "hits": self._hits,
                "misses": self._misses,
                "hit_rate": self._hits / total if total > 0 else 0.0,
                "sets": self._sets,
                "deletes": self._deletes,
                "memory_used_mb": info.get("used_memory", 0) / (1024 * 1024),
                "memory_peak_mb": info.get("used_memory_peak", 0) / (1024 * 1024),
            }
        except Exception as e:
            total = self._hits + self._misses
            return {
                "type": "redis",
                "connected": False,
                "error": str(e),
                "hits": self._hits,
                "misses": self._misses,
                "hit_rate": self._hits / total if total > 0 else 0.0,
            }

    async def close(self) -> None:
        if self._client:
            await self._client.close()
            self._client = None
        if self._pool:
            await self._pool.disconnect()
            self._pool = None


class EnterpriseCache:
    """Enterprise cache with Redis primary and memory fallback."""

    def __init__(self, config: CacheConfig):
        self.config = config
        self._memory_backend = MemoryCacheBackend(config.memory_max_size)
        self._redis_backend: Optional[RedisCacheBackend] = None
        self._use_redis = config.redis_enabled and REDIS_AVAILABLE
        self._current_backend: CacheBackend = self._memory_backend
        self._lock = asyncio.Lock()
        self._warming_task: Optional[asyncio.Task] = None

    async def initialize(self) -> None:
        """Initialize cache backends."""
        if self._use_redis:
            try:
                self._redis_backend = RedisCacheBackend(
                    url=self.config.redis_url,
                    max_connections=self.config.redis_max_connections,
                    socket_timeout=self.config.redis_socket_timeout,
                    socket_connect_timeout=self.config.redis_socket_connect_timeout,
                )
                # Test connection
                await self._redis_backend.get("health_check")
                self._current_backend = self._redis_backend
                self._use_redis = True
            except Exception as e:
                print(f"Redis unavailable, falling back to memory cache: {e}")
                self._use_redis = False
                self._current_backend = self._memory_backend

        # Start cache warming if enabled
        if self.config.warming_enabled:
            self._warming_task = asyncio.create_task(self._warm_cache_loop())

    async def get(self, key: str) -> Optional[Any]:
        """Get value from cache."""
        return await self._current_backend.get(key)

    async def set(self, key: str, value: Any, ttl: Optional[int] = None) -> bool:
        """Set value in cache."""
        return await self._current_backend.set(key, value, ttl or self.config.memory_ttl)

    async def delete(self, key: str) -> bool:
        """Delete key from cache."""
        return await self._current_backend.delete(key)

    async def exists(self, key: str) -> bool:
        """Check if key exists."""
        return await self._current_backend.exists(key)

    async def clear(self) -> bool:
        """Clear all caches."""
        memory_result = await self._memory_backend.clear()
        redis_result = True
        if self._redis_backend:
            redis_result = await self._redis_backend.clear()
        return memory_result and redis_result

    def get_ttl(self, data_type: str) -> int:
        """Get TTL for data type."""
        ttl_map = {
            "stock_quote": self.config.stock_quote_ttl,
            "historical_price": self.config.historical_price_ttl,
            "currency_rate": self.config.currency_rate_ttl,
            "supported_currencies": self.config.supported_currencies_ttl,
            "company_info": self.config.company_info_ttl,
            "market_movers": self.config.market_movers_ttl,
            "news": self.config.news_ttl,
        }
        return ttl_map.get(data_type, self.config.memory_ttl)

    async def set_with_ttl(self, key: str, value: Any, data_type: str) -> bool:
        """Set value with data-type specific TTL."""
        ttl = self.get_ttl(data_type)
        return await self.set(key, value, ttl)

    async def _warm_cache_loop(self) -> None:
        """Background cache warming task."""
        while True:
            try:
                await asyncio.sleep(self.config.warming_interval)
                await self._warm_cache()
            except asyncio.CancelledError:
                break
            except Exception as e:
                print(f"Cache warming error: {e}")

    async def _warm_cache(self) -> None:
        """Warm cache with common symbols."""
        # This would be integrated with finance services
        pass

    def get_stats(self) -> dict[str, Any]:
        """Get combined cache statistics."""
        return {
            "current_backend": "redis" if self._use_redis else "memory",
            "redis_available": REDIS_AVAILABLE and self.config.redis_enabled,
            "memory": asyncio.run(self._memory_backend.get_stats()) if not asyncio.get_event_loop().is_running() else "use async get_stats()",
            "redis": asyncio.run(self._redis_backend.get_stats()) if self._redis_backend and not asyncio.get_event_loop().is_running() else "use async get_stats()",
        }

    async def get_stats_async(self) -> dict[str, Any]:
        """Get combined cache statistics asynchronously."""
        memory_stats = await self._memory_backend.get_stats()
        redis_stats = await self._redis_backend.get_stats() if self._redis_backend else {"type": "redis", "connected": False}

        return {
            "current_backend": "redis" if self._use_redis else "memory",
            "redis_available": REDIS_AVAILABLE and self.config.redis_enabled,
            "memory": memory_stats,
            "redis": redis_stats,
        }

    async def close(self) -> None:
        """Close all cache connections."""
        if self._warming_task:
            self._warming_task.cancel()
            try:
                await self._warming_task
            except asyncio.CancelledError:
                pass

        await self._memory_backend.close()
        if self._redis_backend:
            await self._redis_backend.close()


# Default cache configuration
DEFAULT_CACHE_CONFIG = CacheConfig()

# Global cache instance
_global_cache: Optional[EnterpriseCache] = None


def get_cache() -> EnterpriseCache:
    """Get global cache instance."""
    global _global_cache
    if _global_cache is None:
        _global_cache = EnterpriseCache(DEFAULT_CACHE_CONFIG)
    return _global_cache


async def init_cache(config: Optional[CacheConfig] = None) -> EnterpriseCache:
    """Initialize global cache."""
    global _global_cache
    if config is None:
        config = DEFAULT_CACHE_CONFIG
    _global_cache = EnterpriseCache(config)
    await _global_cache.initialize()
    return _global_cache


async def close_cache() -> None:
    """Close global cache."""
    global _global_cache
    if _global_cache:
        await _global_cache.close()
        _global_cache = None