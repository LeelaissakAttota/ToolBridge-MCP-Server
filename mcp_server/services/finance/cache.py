"""Cache layer for finance services."""

from __future__ import annotations

import asyncio
import logging
import time
from typing import Any, Optional, Callable

logger = logging.getLogger(__name__)


class CacheEntry:
    """Cache entry with value and timestamp."""

    def __init__(self, value: Any, ttl: Optional[int] = None):
        self.value = value
        self.created_at = time.time()
        self.last_accessed = time.time()
        self._access_counter = 0
        # ttl = None means no expiration, ttl <= 0 means instant expiration
        self.ttl = ttl if ttl is not None else 0

    def is_expired(self) -> bool:
        if self.ttl is None:
            return False  # No expiration
        if self.ttl <= 0:
            return True  # Instant expiration
        return (time.time() - self.created_at) > self.ttl

    def touch(self) -> None:
        """Update access time and increment counter."""
        self.last_accessed = time.time()
        self._access_counter += 1

    @property
    def age_seconds(self) -> float:
        return time.time() - self.created_at

    @property
    def access_count(self) -> int:
        return self._access_counter


class FinanceCache:
    """Thread-safe cache with TTL and size limits."""

    def __init__(
        self,
        default_ttl: int = 300,
        max_size: int = 10000,
        cleanup_interval: int = 60,
    ):
        self._cache: dict[str, CacheEntry] = {}
        self._lock = asyncio.Lock()
        self.default_ttl = default_ttl
        self.max_size = max_size
        self.cleanup_interval = cleanup_interval
        self._cleanup_task: Optional[asyncio.Task] = None
        self._running = False
        # Stats
        self._hits = 0
        self._misses = 0

    async def start(self) -> None:
        """Start background cleanup task."""
        if self._running:
            return
        self._running = True
        self._cleanup_task = asyncio.create_task(self._cleanup_loop())
        logger.info("Cache started")

    async def stop(self) -> None:
        """Stop background cleanup task."""
        self._running = False
        if self._cleanup_task:
            self._cleanup_task.cancel()
            try:
                await self._cleanup_task
            except asyncio.CancelledError:
                pass
        logger.info("Cache stopped")

    async def _cleanup_loop(self) -> None:
        """Background task to remove expired entries."""
        while self._running:
            try:
                await asyncio.sleep(self.cleanup_interval)
                await self._cleanup_expired()
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Cache cleanup error: {e}")

    async def _cleanup_expired(self) -> int:
        """Remove expired entries. Returns count of removed entries."""
        async with self._lock:
            expired_keys = [
                key for key, entry in self._cache.items()
                if entry.is_expired()
            ]
            for key in expired_keys:
                del self._cache[key]
            if expired_keys:
                logger.debug(f"Cleaned up {len(expired_keys)} expired cache entries")
            return len(expired_keys)

    async def get(self, key: str) -> Optional[Any]:
        """Get value from cache."""
        async with self._lock:
            entry = self._cache.get(key)
            if entry and not entry.is_expired():
                entry.touch()
                self._hits += 1
                return entry.value
            elif entry:
                del self._cache[key]
            self._misses += 1
            return None

    async def set(self, key: str, value: Any, ttl: Optional[int] = None) -> None:
            """Set value in cache."""
            async with self._lock:
                # Evict oldest if at capacity
                if len(self._cache) >= self.max_size:
                    oldest_key = min(
                        self._cache.keys(),
                        key=lambda k: (self._cache[k]._access_counter, self._cache[k].last_accessed)
                    )
                    del self._cache[oldest_key]

                # Handle ttl=None as no expiration, ttl <= 0 as instant expiration
                effective_ttl = ttl if ttl is not None else self.default_ttl
                self._cache[key] = CacheEntry(value, effective_ttl)

    async def delete(self, key: str) -> bool:
        """Delete entry from cache."""
        async with self._lock:
            if key in self._cache:
                del self._cache[key]
                return True
            return False

    async def clear(self) -> None:
        """Clear all cache entries."""
        async with self._lock:
            self._cache.clear()

    async def get_or_set(
        self,
        key: str,
        factory: Callable[[], Any],
        ttl: Optional[int] = None,
    ) -> Any:
        """Get value or compute and cache it."""
        value = await self.get(key)
        if value is not None:
            return value

        value = await factory()
        await self.set(key, value, ttl)
        return value

    def stats(self) -> dict[str, Any]:
        """Get cache statistics."""
        total = self._hits + self._misses
        hit_rate = self._hits / total if total > 0 else 0.0
        return {
            "size": len(self._cache),
            "max_size": self.max_size,
            "utilization": len(self._cache) / self.max_size if self.max_size > 0 else 0,
            "default_ttl": self.default_ttl,
            "hits": self._hits,
            "misses": self._misses,
            "hit_rate": hit_rate,
        }


# Specialized caches with appropriate TTLs
class StockPriceCache(FinanceCache):
    """Cache for stock prices with 30-second TTL."""

    def __init__(self):
        super().__init__(default_ttl=30, max_size=5000)


class ExchangeRateCache(FinanceCache):
    """Cache for exchange rates with 5-minute TTL."""

    def __init__(self):
        super().__init__(default_ttl=300, max_size=2000)


class CurrencyListCache(FinanceCache):
    """Cache for currency lists with 24-hour TTL."""

    def __init__(self):
        super().__init__(default_ttl=86400, max_size=100)


# Global cache instances
stock_price_cache = StockPriceCache()
exchange_rate_cache = ExchangeRateCache()
currency_list_cache = CurrencyListCache()