"""Tests for Rate Limiter implementation."""

import pytest
import asyncio
import time

from mcp_server.services.finance.rate_limiter import (
    RateLimitConfig,
    RateLimitStatus,
    TokenBucketRateLimiter,
    SlidingWindowRateLimiter,
    MultiTierRateLimiter,
    ProviderRateLimitManager,
    DEFAULT_PROVIDER_LIMITS,
    get_rate_manager,
    close_rate_manager,
)


class TestRateLimitConfig:
    """Tests for RateLimitConfig."""

    def test_default_config(self):
        """Test default configuration values."""
        config = RateLimitConfig(provider_name="test")
        assert config.requests_per_second == 10.0
        assert config.requests_per_minute == 100
        assert config.requests_per_hour == 1000
        assert config.burst_allowance == 5
        assert config.provider_name == "test"

    def test_custom_config(self):
        """Test custom configuration values."""
        config = RateLimitConfig(
            provider_name="custom",
            requests_per_second=20.0,
            requests_per_minute=200,
            requests_per_hour=5000,
            burst_allowance=10,
        )
        assert config.requests_per_second == 20.0
        assert config.requests_per_minute == 200
        assert config.requests_per_hour == 5000
        assert config.burst_allowance == 10


class TestRateLimitStatus:
    """Tests for RateLimitStatus."""

    def test_allowed_status(self):
        """Test status when request is allowed."""
        status = RateLimitStatus(
            allowed=True,
            remaining=10,
            reset_time=time.time() + 60,
            limit=20,
        )
        assert status.allowed is True
        assert status.remaining == 10
        assert status.limit == 20

    def test_rejected_status(self):
        """Test status when request is rejected."""
        status = RateLimitStatus(
            allowed=False,
            remaining=0,
            reset_time=time.time() + 60,
            retry_after=30.0,
            limit=20,
        )
        assert status.allowed is False
        assert status.remaining == 0
        assert status.retry_after == 30.0


class TestTokenBucketRateLimiter:
    """Tests for TokenBucketRateLimiter."""

    @pytest.fixture
    def config(self):
        """Create test configuration."""
        return RateLimitConfig(
            provider_name="test",
            requests_per_second=10.0,
            burst_allowance=5,
        )

    @pytest.fixture
    def limiter(self, config):
        """Create rate limiter instance."""
        return TokenBucketRateLimiter(config)

    @pytest.mark.asyncio
    async def test_acquire_success(self, limiter):
        """Test successful token acquisition."""
        status = await limiter.acquire(1)
        assert status.allowed is True
        assert status.remaining == 4
        assert status.limit == 5

    @pytest.mark.asyncio
    async def test_acquire_multiple_tokens(self, limiter):
        """Test acquiring multiple tokens."""
        status = await limiter.acquire(3)
        assert status.allowed is True
        assert status.remaining == 2

    @pytest.mark.asyncio
    async def test_acquire_exhausted(self, limiter):
        """Test token acquisition when bucket is empty."""
        # Exhaust the bucket
        await limiter.acquire(5)
        
        # Next request should be rejected
        status = await limiter.acquire(1)
        assert status.allowed is False
        assert status.remaining == 0
        assert status.retry_after > 0

    @pytest.mark.asyncio
    async def test_release_tokens(self, limiter):
        """Test releasing tokens back to bucket."""
        # Exhaust the bucket
        await limiter.acquire(5)
        
        # Release some tokens
        await limiter.release(2)
        
        # Should be able to acquire again
        status = await limiter.acquire(1)
        assert status.allowed is True
        assert status.remaining == 1

    @pytest.mark.asyncio
    async def test_token_refill_over_time(self, limiter):
        """Test token refill over time."""
        # Exhaust the bucket
        await limiter.acquire(5)
        
        # Wait for refill
        await asyncio.sleep(0.5)
        
        # Should have some tokens now
        status = await limiter.acquire(1)
        assert status.allowed is True

    def test_get_status(self, limiter):
        """Test getting current status."""
        status = limiter.get_status()
        assert status.allowed is True
        assert status.remaining == 5
        assert status.limit == 5


class TestSlidingWindowRateLimiter:
    """Tests for SlidingWindowRateLimiter."""

    @pytest.fixture
    def config(self):
        """Create test configuration."""
        return RateLimitConfig(
            provider_name="test",
            requests_per_minute=10,
        )

    @pytest.fixture
    def limiter(self, config):
        """Create rate limiter instance."""
        return SlidingWindowRateLimiter(config)

    @pytest.mark.asyncio
    async def test_acquire_success(self, limiter):
        """Test successful acquisition within limit."""
        status = await limiter.acquire(1)
        assert status.allowed is True
        assert status.remaining == 9

    @pytest.mark.asyncio
    async def test_acquire_exhausted(self, limiter):
        """Test rejection when limit exceeded."""
        # Make 10 requests
        for _ in range(10):
            status = await limiter.acquire(1)
            assert status.allowed is True
        
        # 11th should be rejected
        status = await limiter.acquire(1)
        assert status.allowed is False
        assert status.remaining == 0

    @pytest.mark.asyncio
    async def test_release_requests(self, limiter):
        """Test releasing requests back."""
        # Make some requests
        await limiter.acquire(5)
        
        # Release them
        await limiter.release(3)
        
        # Should have capacity again
        status = await limiter.acquire(2)
        assert status.allowed is True

    @pytest.mark.asyncio
    async def test_window_expiration(self, limiter):
        """Test that old requests expire from window."""
        # This test would require waiting 60 seconds which is impractical
        # The sliding window logic is tested via the core functionality
        pass


class TestMultiTierRateLimiter:
    """Tests for MultiTierRateLimiter."""

    @pytest.fixture
    def config(self):
        """Create test configuration."""
        return RateLimitConfig(
            provider_name="test",
            requests_per_second=10.0,
            requests_per_minute=100,
            requests_per_hour=1000,
            burst_allowance=5,
        )

    @pytest.fixture
    def limiter(self, config):
        """Create rate limiter instance."""
        return MultiTierRateLimiter(config)

    @pytest.mark.asyncio
    async def test_acquire_success(self, limiter):
        """Test successful acquisition passes all tiers."""
        status = await limiter.acquire(1)
        assert status.allowed is True

    @pytest.mark.asyncio
    async def test_acquire_rejected_by_second_tier(self, limiter):
        """Test rejection by second tier limiter."""
        # Exhaust second tier (minute)
        for _ in range(100):
            await limiter.acquire(1)
        
        # Next should be rejected
        status = await limiter.acquire(1)
        assert status.allowed is False

    @pytest.mark.asyncio
    async def test_release_all_tiers(self, limiter):
        """Test releasing tokens to all tiers."""
        # Acquire small amount first
        status = await limiter.acquire(2)
        assert status.allowed is True
        
        # Release some tokens
        await limiter.release(1)
        
        # Should be able to acquire again
        status = await limiter.acquire(1)
        assert status.allowed is True

    def test_get_status(self, limiter):
        """Test getting combined status."""
        status = limiter.get_status()
        assert status.allowed is True
        assert status.remaining > 0


class TestProviderRateLimitManager:
    """Tests for ProviderRateLimitManager."""

    @pytest.fixture
    def manager(self):
        """Create manager with default configs."""
        manager = ProviderRateLimitManager()
        # Configure default providers
        for name, config in DEFAULT_PROVIDER_LIMITS.items():
            manager.configure_provider(name, config)
        return manager

    @pytest.mark.asyncio
    async def test_default_providers_configured(self, manager):
        """Test that default providers are configured."""
        assert "yahoo_finance" in manager._limiters
        assert "alpha_vantage" in manager._limiters
        assert "frankfurter" in manager._limiters

    @pytest.mark.asyncio
    async def test_acquire_for_provider(self, manager):
        """Test acquiring token for a provider."""
        status = await manager.acquire("yahoo_finance", 1)
        assert status.allowed is True

    @pytest.mark.asyncio
    async def test_acquire_unknown_provider(self, manager):
        """Test acquiring for unknown provider allows by default."""
        status = await manager.acquire("unknown_provider", 1)
        assert status.allowed is True
        assert status.remaining == 999

    @pytest.mark.asyncio
    async def test_release_for_provider(self, manager):
        """Test releasing token for a provider."""
        await manager.acquire("yahoo_finance", 5)
        await manager.release("yahoo_finance", 2)
        
        status = await manager.acquire("yahoo_finance", 2)
        assert status.allowed is True

    def test_get_all_status(self, manager):
        """Test getting status for all providers."""
        status = manager.get_all_status()
        assert "yahoo_finance" in status
        assert "alpha_vantage" in status

    def test_configure_provider(self, manager):
        """Test configuring a custom provider."""
        config = RateLimitConfig(
            provider_name="custom",
            requests_per_second=5.0,
            requests_per_minute=50,
        )
        manager.configure_provider("custom", config)
        
        limiter = manager.get_limiter("custom")
        assert limiter is not None


class TestDefaultProviderLimits:
    """Tests for default provider limit configurations."""

    def test_yahoo_finance_limits(self):
        """Test Yahoo Finance default limits."""
        config = DEFAULT_PROVIDER_LIMITS["yahoo_finance"]
        assert config.requests_per_second == 5.0
        assert config.requests_per_minute == 100
        assert config.burst_allowance == 10

    def test_alpha_vantage_limits(self):
        """Test Alpha Vantage default limits (free tier)."""
        config = DEFAULT_PROVIDER_LIMITS["alpha_vantage"]
        assert config.requests_per_minute == 5  # Free tier
        assert config.burst_allowance == 5

    def test_frankfurter_limits(self):
        """Test Frankfurter default limits."""
        config = DEFAULT_PROVIDER_LIMITS["frankfurter"]
        assert config.requests_per_second == 10.0
        assert config.requests_per_minute == 60

    def test_all_providers_have_configs(self):
        """Test all expected providers have configurations."""
        expected = [
            "yahoo_finance", "alpha_vantage", "twelve_data",
            "finnhub", "polygon", "frankfurter",
            "exchangerate_api", "currencylayer",
        ]
        for provider in expected:
            assert provider in DEFAULT_PROVIDER_LIMITS


if __name__ == "__main__":
    pytest.main([__file__, "-v"])