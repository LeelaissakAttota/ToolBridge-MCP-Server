"""Tests for FinanceCache."""

import pytest
import asyncio
from datetime import datetime, timedelta

from mcp_server.services.finance.cache import (
    FinanceCache,
    CacheEntry,
    StockPriceCache,
    ExchangeRateCache,
    CurrencyListCache,
)


class TestCacheEntry:
    """Tests for CacheEntry."""

    def test_cache_entry_creation(self):
        """Test cache entry creation."""
        entry = CacheEntry("test_value", 60)
        assert entry.value == "test_value"
        assert entry.ttl == 60

    def test_is_expired_false(self):
        """Test is_expired returns False for fresh entry."""
        entry = CacheEntry("test", 60)
        assert entry.is_expired() is False

    def test_is_expired_true(self):
        """Test is_expired returns True for expired entry."""
        entry = CacheEntry("test", 0)  # TTL = 0 = instant expiry
        assert entry.is_expired() is True

    def test_age_seconds(self):
        """Test age_seconds property."""
        entry = CacheEntry("test", 60)
        # Age should be very small (just created)
        assert entry.age_seconds >= 0
        assert entry.age_seconds < 1


class TestFinanceCache:
    """Tests for FinanceCache."""

    @pytest.fixture
    async def cache(self):
        """Create a cache instance."""
        cache = FinanceCache(default_ttl=60, max_size=100)
        yield cache
        await cache.stop()

    @pytest.mark.asyncio
    async def test_get_set(self, cache):
        """Test basic get/set operations."""
        await cache.set("key1", "value1")
        value = await cache.get("key1")
        assert value == "value1"

    @pytest.mark.asyncio
    async def test_get_nonexistent(self, cache):
        """Test get on non-existent key."""
        value = await cache.get("nonexistent")
        assert value is None

    @pytest.mark.asyncio
    async def test_ttl_expiration(self, cache):
        """Test TTL expiration."""
        cache = FinanceCache(default_ttl=-1, max_size=100)  # Negative TTL = instant expiry
        await cache.set("key1", "value1")
        value = await cache.get("key1")
        assert value is None  # Should be expired immediately

    @pytest.mark.asyncio
    async def test_custom_ttl(self, cache):
        """Test custom TTL per entry."""
        await cache.set("key1", "value1", ttl=60)
        await cache.set("key2", "value2", ttl=0)  # Instant expiry

        assert await cache.get("key1") == "value1"
        assert await cache.get("key2") is None

    @pytest.mark.asyncio
    async def test_delete(self, cache):
        """Test delete operation."""
        await cache.set("key1", "value1")
        assert await cache.get("key1") == "value1"

        result = await cache.delete("key1")
        assert result is True
        assert await cache.get("key1") is None

    @pytest.mark.asyncio
    async def test_delete_nonexistent(self, cache):
        """Test delete on non-existent key."""
        result = await cache.delete("nonexistent")
        assert result is False

    @pytest.mark.asyncio
    async def test_clear(self, cache):
        """Test clear operation."""
        await cache.set("key1", "value1")
        await cache.set("key2", "value2")

        await cache.clear()
        assert await cache.get("key1") is None
        assert await cache.get("key2") is None

    @pytest.mark.asyncio
    async def test_get_or_set(self, cache):
        """Test get_or_set factory pattern."""
        call_count = 0

        async def factory():
            nonlocal call_count
            call_count += 1
            return "factory_value"

        # First call should invoke factory
        value1 = await cache.get_or_set("key1", factory)
        assert value1 == "factory_value"
        assert call_count == 1

        # Second call should use cache
        value2 = await cache.get_or_set("key1", factory)
        assert value2 == "factory_value"
        assert call_count == 1

    @pytest.mark.asyncio
    async def test_max_size_eviction(self):
        """Test LRU eviction when max size reached."""
        cache = FinanceCache(default_ttl=60, max_size=3)
        
        await cache.set("key1", "value1")
        await cache.set("key2", "value2")
        await cache.set("key3", "value3")
        
        # Access key1 to make it recently used
        await cache.get("key1")
        
        # Add key4, should evict key2 (least recently used)
        await cache.set("key4", "value4")
        
        assert await cache.get("key1") == "value1"
        assert await cache.get("key2") is None  # Evicted
        assert await cache.get("key3") == "value3"
        assert await cache.get("key4") == "value4"
        
        await cache.stop()

    @pytest.mark.asyncio
    async def test_stats(self, cache):
        """Test cache statistics."""
        await cache.set("key1", "value1")
        await cache.get("key1")  # Hit
        await cache.get("key2")  # Miss

        stats = cache.stats()
        assert stats["size"] == 1
        assert stats["hits"] >= 1
        assert stats["misses"] >= 1


class TestSpecializedCaches:
    """Tests for specialized cache classes."""

    @pytest.mark.asyncio
    async def test_stock_price_cache(self):
        """Test StockPriceCache with 30s TTL."""
        cache = StockPriceCache()
        await cache.set("AAPL", {"price": 150.0})
        assert await cache.get("AAPL") == {"price": 150.0}
        assert cache.default_ttl == 30
        await cache.stop()

    @pytest.mark.asyncio
    async def test_exchange_rate_cache(self):
        """Test ExchangeRateCache with 5min TTL."""
        cache = ExchangeRateCache()
        await cache.set("USD:EUR", {"rate": 0.92})
        assert await cache.get("USD:EUR") == {"rate": 0.92}
        assert cache.default_ttl == 300
        await cache.stop()

    @pytest.mark.asyncio
    async def test_currency_list_cache(self):
        """Test CurrencyListCache with 24h TTL."""
        cache = CurrencyListCache()
        await cache.set("currencies", ["USD", "EUR"])
        assert await cache.get("currencies") == ["USD", "EUR"]
        assert cache.default_ttl == 86400
        await cache.stop()