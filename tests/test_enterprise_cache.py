"""Tests for Enterprise Cache Layer."""

import pytest
import asyncio
import time

from mcp_server.services.finance.enterprise_cache import (
    CacheConfig,
    CacheBackend,
    MemoryCacheBackend,
    RedisCacheBackend,
    EnterpriseCache,
    DEFAULT_CACHE_CONFIG,
    get_cache,
    init_cache,
    close_cache,
)
from mcp_server.services.finance.cache import FinanceCache


class TestCacheConfig:
    """Tests for CacheConfig."""

    def test_default_config(self):
        """Test default configuration values."""
        config = CacheConfig()
        assert config.redis_url == "redis://localhost:6379/0"
        assert config.redis_enabled is True
        assert config.memory_max_size == 10000
        assert config.stock_quote_ttl == 30
        assert config.historical_price_ttl == 600
        assert config.currency_rate_ttl == 300
        assert config.supported_currencies_ttl == 86400

    def test_custom_config(self):
        """Test custom configuration values."""
        config = CacheConfig(
            redis_url="redis://custom:6379/1",
            redis_enabled=False,
            memory_max_size=5000,
            stock_quote_ttl=60,
        )
        assert config.redis_url == "redis://custom:6379/1"
        assert config.redis_enabled is False
        assert config.memory_max_size == 5000
        assert config.stock_quote_ttl == 60


class TestMemoryCacheBackend:
    """Tests for MemoryCacheBackend."""

    @pytest.fixture
    def backend(self):
        """Create a fresh memory cache backend."""
        return MemoryCacheBackend(max_size=100)

    @pytest.mark.asyncio
    async def test_basic_get_set(self, backend):
        """Test basic get/set operations."""
        await backend.set("key1", {"data": "value1"}, 60)
        value = await backend.get("key1")
        assert value == {"data": "value1"}

    @pytest.mark.asyncio
    async def test_get_nonexistent(self, backend):
        """Test getting non-existent key."""
        value = await backend.get("nonexistent")
        assert value is None

    @pytest.mark.asyncio
    async def test_ttl_expiration(self, backend):
        """Test TTL expiration."""
        await backend.set("expire_key", "value", 1)  # 1 second TTL
        value = await backend.get("expire_key")
        assert value == "value"
        
        await asyncio.sleep(1.5)
        value = await backend.get("expire_key")
        assert value is None

    @pytest.mark.asyncio
    async def test_delete(self, backend):
        """Test delete operation."""
        await backend.set("delete_key", "value", 60)
        assert await backend.get("delete_key") == "value"
        
        result = await backend.delete("delete_key")
        assert result is True
        assert await backend.get("delete_key") is None
        
        # Deleting non-existent should return False
        result = await backend.delete("nonexistent")
        assert result is False

    @pytest.mark.asyncio
    async def test_exists(self, backend):
        """Test exists operation."""
        assert await backend.exists("key1") is False
        await backend.set("key1", "value", 60)
        assert await backend.exists("key1") is True

    @pytest.mark.asyncio
    async def test_lru_eviction(self, backend):
        """Test LRU eviction when max size reached."""
        # Fill cache to max size (100)
        for i in range(100):
            await backend.set(f"key{i}", f"value{i}", 3600)
        
        # Access key0 to make it recently used
        await backend.get("key0")
        
        # Add one more, should evict LRU (key1, not key0 since key0 was accessed)
        await backend.set("key100", "value100", 3600)
        
        # key0 should still be there (recently accessed)
        assert await backend.get("key0") == "value0"
        # key1 should be evicted (least recently used)
        assert await backend.get("key1") is None
        # key100 should be there
        assert await backend.get("key100") == "value100"

    @pytest.mark.asyncio
    async def test_clear(self, backend):
        """Test clear operation."""
        await backend.set("key1", "value1", 60)
        await backend.set("key2", "value2", 60)
        
        result = await backend.clear()
        assert result is True
        
        assert await backend.get("key1") is None
        assert await backend.get("key2") is None

    @pytest.mark.asyncio
    async def test_get_stats(self, backend):
        """Test getting cache statistics."""
        await backend.set("key1", "value1", 60)
        await backend.get("key1")  # hit
        await backend.get("key2")  # miss
        
        stats = await backend.get_stats()
        assert stats["type"] == "memory"
        assert stats["size"] == 1
        assert stats["hits"] == 1
        assert stats["misses"] == 1
        assert stats["sets"] == 1
        assert 0.0 <= stats["hit_rate"] <= 1.0

    @pytest.mark.asyncio
    async def test_close(self, backend):
        """Test closing the backend."""
        await backend.set("key1", "value1", 60)
        await backend.close()
        
        # After close, operations should fail gracefully
        value = await backend.get("key1")
        assert value is None


class TestEnterpriseCache:
    """Tests for EnterpriseCache with Redis/Memory fallback."""

    @pytest.fixture
    def config(self):
        """Create test cache config."""
        return CacheConfig(
            redis_enabled=False,
            memory_max_size=1000,
            stock_quote_ttl=30,
            historical_price_ttl=600,
            currency_rate_ttl=300,
            supported_currencies_ttl=86400,
            warming_enabled=False,
        )

    @pytest.fixture
    async def cache(self, config):
        """Create and initialize enterprise cache."""
        cache = EnterpriseCache(config)
        await cache.initialize()
        yield cache
        await cache.close()

    @pytest.mark.asyncio
    async def test_basic_operations(self, cache):
        """Test basic get/set operations."""
        await cache.set("test_key", {"data": "test_value"}, 60)
        value = await cache.get("test_key")
        assert value == {"data": "test_value"}

    @pytest.mark.asyncio
    async def test_ttl_by_data_type(self, cache):
        """Test TTL selection by data type."""
        # Test stock quote TTL
        await cache.set_with_ttl("quote:AAPL", {"price": 150}, "stock_quote")
        assert await cache.get("quote:AAPL") is not None
        
        # Test historical price TTL
        await cache.set_with_ttl("historical:AAPL", [{"price": 150}], "historical_price")
        assert await cache.get("historical:AAPL") is not None
        
        # Test currency rate TTL
        await cache.set_with_ttl("rate:USD:EUR", 0.92, "currency_rate")
        assert await cache.get("rate:USD:EUR") is not None

    @pytest.mark.asyncio
    async def test_delete_and_exists(self, cache):
        """Test delete and exists operations."""
        await cache.set("exist_key", "value", 60)
        assert await cache.exists("exist_key") is True
        
        await cache.delete("exist_key")
        assert await cache.exists("exist_key") is False

    @pytest.mark.asyncio
    async def test_clear(self, cache):
        """Test clearing all caches."""
        await cache.set("key1", "value1", 60)
        await cache.set("key2", "value2", 60)
        
        await cache.clear()
        
        assert await cache.get("key1") is None
        assert await cache.get("key2") is None

    @pytest.mark.asyncio
    async def test_get_stats(self, cache):
        """Test getting cache statistics."""
        await cache.set("key1", "value1", 60)
        await cache.get("key1")
        
        stats = await cache.get_stats_async()
        assert "current_backend" in stats
        assert "memory" in stats
        assert "redis" in stats
        assert stats["memory"]["hits"] >= 1


class TestFinanceCache:
    """Tests for FinanceCache (legacy)."""

    @pytest.fixture
    def cache(self):
        """Create FinanceCache instance."""
        return FinanceCache()

    @pytest.mark.asyncio
    async def test_get_set(self, cache):
        """Test basic get/set with async methods."""
        await cache.set("test", "value", 60)
        result = await cache.get("test")
        assert result == "value"

    @pytest.mark.asyncio
    async def test_expiration(self, cache):
        """Test expiration."""
        await cache.set("expire", "value", 1)
        assert await cache.get("expire") == "value"
        await asyncio.sleep(1.5)
        assert await cache.get("expire") is None

    @pytest.mark.asyncio
    async def test_lru_eviction(self, cache):
        """Test LRU eviction."""
        cache = FinanceCache(max_size=3)
        await cache.set("a", 1, 60)
        await cache.set("b", 2, 60)
        await cache.set("c", 3, 60)
        await cache.get("a")  # Access 'a'
        await cache.set("d", 4, 60)  # Should evict 'b'
        assert await cache.get("a") == 1
        assert await cache.get("b") is None


if __name__ == "__main__":
    pytest.main([__file__, "-v"])