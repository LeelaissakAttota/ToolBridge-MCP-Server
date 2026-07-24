"""Tests for Circuit Breaker implementation."""

import pytest
import asyncio
from datetime import datetime

from mcp_server.services.finance.circuit_breaker import (
    CircuitBreaker,
    CircuitBreakerConfig,
    CircuitBreakerRegistry,
    CircuitState,
    CircuitBreakerOpenError,
    CircuitBreakerMetrics,
)


class TestCircuitBreakerConfig:
    """Tests for CircuitBreakerConfig."""

    def test_default_config(self):
        """Test default configuration values."""
        config = CircuitBreakerConfig(name="test")
        assert config.failure_threshold == 5
        assert config.success_threshold == 3
        assert config.timeout == 30.0
        assert config.half_open_max_requests == 3
        assert config.excluded_exceptions == ()
        assert config.name == "test"

    def test_custom_config(self):
        """Test custom configuration values."""
        config = CircuitBreakerConfig(
            name="custom",
            failure_threshold=3,
            success_threshold=2,
            timeout=10.0,
            half_open_max_requests=5,
            excluded_exceptions=(ValueError,),
        )
        assert config.failure_threshold == 3
        assert config.success_threshold == 2
        assert config.timeout == 10.0
        assert config.half_open_max_requests == 5
        assert config.excluded_exceptions == (ValueError,)


class TestCircuitBreakerMetrics:
    """Tests for CircuitBreakerMetrics."""

    def test_initial_state(self):
        """Test initial metrics state."""
        metrics = CircuitBreakerMetrics(name="test")
        assert metrics.total_requests == 0
        assert metrics.successful_requests == 0
        assert metrics.failed_requests == 0
        assert metrics.rejected_requests == 0
        assert metrics.state_changes == 0
        assert metrics.current_state == CircuitState.CLOSED
        assert metrics.failure_rate == 0.0

    def test_failure_rate_calculation(self):
        """Test failure rate calculation."""
        metrics = CircuitBreakerMetrics(name="test")
        metrics.total_requests = 10
        metrics.successful_requests = 7
        metrics.failed_requests = 3
        assert metrics.failure_rate == 0.3

    def test_failure_rate_zero_requests(self):
        """Test failure rate when no requests."""
        metrics = CircuitBreakerMetrics(name="test")
        assert metrics.failure_rate == 0.0


class TestCircuitBreaker:
    """Tests for CircuitBreaker."""

    @pytest.fixture
    def config(self):
        """Create test configuration."""
        return CircuitBreakerConfig(
            name="test",
            failure_threshold=3,
            success_threshold=3,
            timeout=1.0,
            half_open_max_requests=2,
        )

    @pytest.fixture
    def breaker(self, config):
        """Create circuit breaker instance."""
        return CircuitBreaker(config)

    @pytest.mark.asyncio
    async def test_initial_state(self, breaker):
        """Test initial state is CLOSED."""
        assert breaker.state == CircuitState.CLOSED
        assert breaker.is_available is True

    @pytest.mark.asyncio
    async def test_successful_call(self, breaker):
        """Test successful call through breaker."""
        async def success_func():
            return "success"

        result = await breaker.call(success_func)
        assert result == "success"
        assert breaker.metrics.successful_requests == 1
        assert breaker.metrics.total_requests == 1
        assert breaker.state == CircuitState.CLOSED

    @pytest.mark.asyncio
    async def test_failed_call(self, breaker):
        """Test failed call increments failure count."""
        async def fail_func():
            raise Exception("Test failure")

        with pytest.raises(Exception, match="Test failure"):
            await breaker.call(fail_func)

        assert breaker.metrics.failed_requests == 1
        assert breaker.metrics.total_requests == 1
        assert breaker._failure_count == 1

    @pytest.mark.asyncio
    async def test_opens_after_threshold(self, breaker):
        """Test breaker opens after failure threshold."""
        async def fail_func():
            raise Exception("Test failure")

        # Fail up to threshold
        for i in range(3):
            with pytest.raises(Exception):
                await breaker.call(fail_func)

        assert breaker.state == CircuitState.OPEN
        assert breaker.is_available is False

    @pytest.mark.asyncio
    async def test_rejects_when_open(self, breaker):
        """Test calls are rejected when breaker is OPEN."""
        async def fail_func():
            raise Exception("Test failure")

        # Open the breaker
        for _ in range(3):
            with pytest.raises(Exception):
                await breaker.call(fail_func)

        # Now try a call - should be rejected
        async def success_func():
            return "success"

        with pytest.raises(CircuitBreakerOpenError):
            await breaker.call(success_func)

        assert breaker.metrics.rejected_requests == 1

    @pytest.mark.asyncio
    async def test_half_open_after_timeout(self, breaker):
        """Test breaker transitions to HALF_OPEN after timeout."""
        async def fail_func():
            raise Exception("Test failure")

        # Open the breaker
        for _ in range(3):
            with pytest.raises(Exception):
                await breaker.call(fail_func)

        assert breaker.state == CircuitState.OPEN

        # Wait for timeout
        await asyncio.sleep(1.1)

        # Now it should allow a request (transition to HALF_OPEN)
        async def success_func():
            return "success"

        result = await breaker.call(success_func)
        assert result == "success"
        assert breaker.state == CircuitState.HALF_OPEN

    @pytest.mark.asyncio
    async def test_closes_after_success_threshold(self, breaker):
        """Test breaker closes after success threshold in HALF_OPEN."""
        async def fail_func():
            raise Exception("Test failure")

        async def success_func():
            return "success"

        # Open the breaker
        for _ in range(3):
            with pytest.raises(Exception):
                await breaker.call(fail_func)

        await asyncio.sleep(1.1)

        # First success - HALF_OPEN
        result = await breaker.call(success_func)
        assert result == "success"
        assert breaker.state == CircuitState.HALF_OPEN

        # Second success - still HALF_OPEN
        result = await breaker.call(success_func)
        assert result == "success"
        assert breaker.state == CircuitState.HALF_OPEN

        # Third success - should close
        result = await breaker.call(success_func)
        assert result == "success"
        assert breaker.state == CircuitState.CLOSED

    @pytest.mark.asyncio
    async def test_reopens_on_failure_in_half_open(self, breaker):
        """Test breaker reopens on failure in HALF_OPEN state."""
        async def fail_func():
            raise Exception("Test failure")

        async def success_func():
            return "success"

        # Open the breaker
        for _ in range(3):
            with pytest.raises(Exception):
                await breaker.call(fail_func)

        await asyncio.sleep(1.1)

        # One success
        await breaker.call(success_func)
        assert breaker.state == CircuitState.HALF_OPEN

        # Failure should reopen
        with pytest.raises(Exception):
            await breaker.call(fail_func)

        assert breaker.state == CircuitState.OPEN

    @pytest.mark.asyncio
    async def test_excluded_exceptions(self, config):
        """Test excluded exceptions don't count as failures."""
        config.excluded_exceptions = (ValueError,)
        breaker = CircuitBreaker(config)

        async def value_error_func():
            raise ValueError("Excluded")

        with pytest.raises(ValueError):
            await breaker.call(value_error_func)

        # Should not count as failure
        assert breaker._failure_count == 0
        assert breaker.metrics.failed_requests == 0

    @pytest.mark.asyncio
    async def test_reset(self, breaker):
        """Test manual reset of breaker."""
        async def fail_func():
            raise Exception("Test failure")

        # Open the breaker
        for _ in range(3):
            with pytest.raises(Exception):
                await breaker.call(fail_func)

        assert breaker.state == CircuitState.OPEN

        # Reset
        breaker.reset()
        assert breaker.state == CircuitState.CLOSED
        assert breaker._failure_count == 0

    @pytest.mark.asyncio
    async def test_get_status(self, breaker):
        """Test get_status returns correct information."""
        status = breaker.get_status()
        assert status["name"] == "test"
        assert status["state"] == "closed"
        assert status["is_available"] is True
        assert "metrics" in status


class TestCircuitBreakerRegistry:
    """Tests for CircuitBreakerRegistry."""

    @pytest.fixture
    def registry(self):
        """Create fresh registry."""
        return CircuitBreakerRegistry()

    @pytest.mark.asyncio
    async def test_get_or_create(self, registry):
        """Test get_or_create returns new or existing breaker."""
        cb1 = registry.get_or_create("test1")
        cb2 = registry.get_or_create("test1")
        assert cb1 is cb2

    @pytest.mark.asyncio
    async def test_get_existing(self, registry):
        """Test get returns existing breaker."""
        registry.get_or_create("test")
        cb = registry.get("test")
        assert cb is not None
        assert cb.config.name == "test"

    @pytest.mark.asyncio
    async def test_get_nonexistent(self, registry):
        """Test get returns None for nonexistent."""
        cb = registry.get("nonexistent")
        assert cb is None

    @pytest.mark.asyncio
    async def test_remove(self, registry):
        """Test removing breaker."""
        registry.get_or_create("test")
        assert registry.remove("test") is True
        assert registry.get("test") is None
        assert registry.remove("nonexistent") is False

    @pytest.mark.asyncio
    async def test_get_all_status(self, registry):
        """Test getting status of all breakers."""
        registry.get_or_create("test1")
        registry.get_or_create("test2")

        status = registry.get_all_status()
        assert "test1" in status
        assert "test2" in status
        assert status["test1"]["state"] == "closed"

    @pytest.mark.asyncio
    async def test_reset_all(self, registry):
        """Test resetting all breakers."""
        # Create breakers with failure_threshold=3
        cb1 = registry.get_or_create("test1", CircuitBreakerConfig(name="test1", failure_threshold=3))
        cb2 = registry.get_or_create("test2", CircuitBreakerConfig(name="test2", failure_threshold=3))

        # Open both
        async def fail():
            raise Exception("fail")

        for _ in range(3):
            try:
                await cb1.call(fail)
            except:
                pass
            try:
                await cb2.call(fail)
            except:
                pass

        assert cb1.state == CircuitState.OPEN
        assert cb2.state == CircuitState.OPEN

        await registry.reset_all()

        assert cb1.state == CircuitState.CLOSED
        assert cb2.state == CircuitState.CLOSED


if __name__ == "__main__":
    pytest.main([__file__, "-v"])