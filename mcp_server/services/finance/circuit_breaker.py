"""Circuit breaker implementation for provider resilience."""

from __future__ import annotations

import asyncio
import time
from dataclasses import dataclass
from enum import Enum
from typing import Any, Callable, Optional, TypeVar

T = TypeVar('T')


class CircuitState(Enum):
    """Circuit breaker states."""
    CLOSED = "closed"      # Normal operation, requests pass through
    OPEN = "open"          # Failing, requests blocked
    HALF_OPEN = "half_open"  # Testing if service recovered


@dataclass
class CircuitBreakerConfig:
    """Configuration for circuit breaker."""
    failure_threshold: int = 5          # Failures before opening
    success_threshold: int = 3          # Successes in half-open before closing
    timeout: float = 30.0               # Time in open state before half-open
    half_open_max_requests: int = 3     # Max concurrent requests in half-open
    excluded_exceptions: tuple = ()     # Exceptions that don't count as failures
    name: str = "default"


@dataclass
class CircuitBreakerMetrics:
    """Metrics for circuit breaker."""
    total_requests: int = 0
    successful_requests: int = 0
    failed_requests: int = 0
    rejected_requests: int = 0
    state_changes: int = 0
    last_failure_time: Optional[float] = None
    last_success_time: Optional[float] = None
    last_state_change: Optional[float] = None
    current_state: CircuitState = CircuitState.CLOSED
    name: str = "default"

    @property
    def failure_rate(self) -> float:
        if self.total_requests == 0:
            return 0.0
        return self.failed_requests / self.total_requests


class CircuitBreakerOpenError(Exception):
    """Raised when circuit breaker is open and request is rejected."""
    def __init__(self, name: str, retry_after: float):
        self.name = name
        self.retry_after = retry_after
        super().__init__(f"Circuit breaker '{name}' is open. Retry after {retry_after:.1f}s")


class CircuitBreaker:
    """Circuit breaker implementation with three states."""

    def __init__(self, config: CircuitBreakerConfig):
        self.config = config
        self._state = CircuitState.CLOSED
        self._failure_count = 0
        self._success_count = 0
        self._half_open_requests = 0
        self._last_failure_time: Optional[float] = None
        self._lock = asyncio.Lock()
        self.metrics = CircuitBreakerMetrics(name=config.name)

    @property
    def state(self) -> CircuitState:
        return self._state

    @property
    def is_available(self) -> bool:
        """Check if requests are allowed."""
        if self._state == CircuitState.CLOSED:
            return True
        if self._state == CircuitState.OPEN:
            # Check if timeout has passed
            if self._last_failure_time and \
               time.monotonic() - self._last_failure_time >= self.config.timeout:
                return True  # Will transition to half-open on next request
            return False
        # HALF_OPEN
        return self._half_open_requests < self.config.half_open_max_requests

    async def _maybe_transition_to_half_open(self) -> None:
        """Transition from OPEN to HALF_OPEN if timeout has passed."""
        if self._state == CircuitState.OPEN and self._last_failure_time:
            if time.monotonic() - self._last_failure_time >= self.config.timeout:
                await self._transition_to(CircuitState.HALF_OPEN)

    async def call(self, func: Callable[..., T], *args, **kwargs) -> T:
        """Execute function with circuit breaker protection."""
        async with self._lock:
            # Check if we should transition to half-open
            await self._maybe_transition_to_half_open()

            if not self.is_available:
                retry_after = 0.0
                if self._state == CircuitState.OPEN and self._last_failure_time:
                    retry_after = self.config.timeout - (time.monotonic() - self._last_failure_time)
                self.metrics.rejected_requests += 1
                raise CircuitBreakerOpenError(self.config.name, max(0, retry_after))

            # Track half-open requests
            if self._state == CircuitState.HALF_OPEN:
                self._half_open_requests += 1

        self.metrics.total_requests += 1

        try:
            if asyncio.iscoroutinefunction(func):
                result = await func(*args, **kwargs)
            else:
                result = func(*args, **kwargs)

            await self._on_success()
            return result

        except self.config.excluded_exceptions:
            # Don't count as failure
            raise
        except Exception as e:
            await self._on_failure()
            raise

    async def _on_success(self) -> None:
        """Handle successful request."""
        async with self._lock:
            self.metrics.successful_requests += 1
            self.metrics.last_success_time = time.monotonic()

            if self._state == CircuitState.HALF_OPEN:
                self._success_count += 1
                self._half_open_requests = max(0, self._half_open_requests - 1)

                if self._success_count >= self.config.success_threshold:
                    await self._transition_to(CircuitState.CLOSED)

            elif self._state == CircuitState.CLOSED:
                # Reset failure count on success
                self._failure_count = 0

    async def _on_failure(self) -> None:
        """Handle failed request."""
        async with self._lock:
            self.metrics.failed_requests += 1
            self.metrics.last_failure_time = time.monotonic()
            self._last_failure_time = time.monotonic()

            if self._state == CircuitState.HALF_OPEN:
                self._half_open_requests = max(0, self._half_open_requests - 1)
                await self._transition_to(CircuitState.OPEN)

            elif self._state == CircuitState.CLOSED:
                self._failure_count += 1
                if self._failure_count >= self.config.failure_threshold:
                    await self._transition_to(CircuitState.OPEN)

    async def _transition_to(self, new_state: CircuitState) -> None:
        """Transition to new state."""
        old_state = self._state
        if old_state == new_state:
            return

        self._state = new_state
        self.metrics.current_state = new_state
        self.metrics.state_changes += 1
        self.metrics.last_state_change = time.monotonic()

        if new_state == CircuitState.CLOSED:
            self._failure_count = 0
            self._success_count = 0
        elif new_state == CircuitState.OPEN:
            self._success_count = 0
        elif new_state == CircuitState.HALF_OPEN:
            self._success_count = 0
            self._half_open_requests = 0

    def get_status(self) -> dict[str, Any]:
        """Get circuit breaker status."""
        return {
            "name": self.config.name,
            "state": self._state.value,
            "failure_count": self._failure_count,
            "success_count": self._success_count,
            "is_available": self.is_available,
            "metrics": {
                "total_requests": self.metrics.total_requests,
                "successful_requests": self.metrics.successful_requests,
                "failed_requests": self.metrics.failed_requests,
                "rejected_requests": self.metrics.rejected_requests,
                "failure_rate": self.metrics.failure_rate,
                "state_changes": self.metrics.state_changes,
            },
        }

    def reset(self) -> None:
        """Manually reset circuit breaker to closed state."""
        self._state = CircuitState.CLOSED
        self._failure_count = 0
        self._success_count = 0
        self._half_open_requests = 0
        self._last_failure_time = None
        self.metrics.current_state = CircuitState.CLOSED


class CircuitBreakerRegistry:
    """Registry for managing multiple circuit breakers."""

    def __init__(self):
        self._breakers: dict[str, CircuitBreaker] = {}
        self._lock = asyncio.Lock()

    def get_or_create(self, name: str, config: Optional[CircuitBreakerConfig] = None) -> CircuitBreaker:
        """Get existing or create new circuit breaker."""
        if name not in self._breakers:
            if config is None:
                config = CircuitBreakerConfig(name=name)
            self._breakers[name] = CircuitBreaker(config)
        return self._breakers[name]

    def get(self, name: str) -> Optional[CircuitBreaker]:
        """Get circuit breaker by name."""
        return self._breakers.get(name)

    def remove(self, name: str) -> bool:
        """Remove circuit breaker."""
        if name in self._breakers:
            del self._breakers[name]
            return True
        return False

    def get_all_status(self) -> dict[str, dict[str, Any]]:
        """Get status of all circuit breakers."""
        return {
            name: breaker.get_status()
            for name, breaker in self._breakers.items()
        }

    async def reset_all(self) -> None:
        """Reset all circuit breakers."""
        for breaker in self._breakers.values():
            breaker.reset()


# Default circuit breaker configurations for providers
DEFAULT_CIRCUIT_CONFIGS = {
    "yahoo_finance": CircuitBreakerConfig(
        name="yahoo_finance",
        failure_threshold=5,
        success_threshold=3,
        timeout=30.0,
        half_open_max_requests=3,
    ),
    "alpha_vantage": CircuitBreakerConfig(
        name="alpha_vantage",
        failure_threshold=3,
        success_threshold=2,
        timeout=60.0,
        half_open_max_requests=2,
    ),
    "twelve_data": CircuitBreakerConfig(
        name="twelve_data",
        failure_threshold=5,
        success_threshold=3,
        timeout=30.0,
        half_open_max_requests=3,
    ),
    "finnhub": CircuitBreakerConfig(
        name="finnhub",
        failure_threshold=5,
        success_threshold=3,
        timeout=30.0,
        half_open_max_requests=3,
    ),
    "polygon": CircuitBreakerConfig(
        name="polygon",
        failure_threshold=5,
        success_threshold=3,
        timeout=30.0,
        half_open_max_requests=3,
    ),
    "frankfurter": CircuitBreakerConfig(
        name="frankfurter",
        failure_threshold=5,
        success_threshold=3,
        timeout=30.0,
        half_open_max_requests=3,
    ),
    "exchangerate_api": CircuitBreakerConfig(
        name="exchangerate_api",
        failure_threshold=3,
        success_threshold=2,
        timeout=60.0,
        half_open_max_requests=2,
    ),
    "currencylayer": CircuitBreakerConfig(
        name="currencylayer",
        failure_threshold=3,
        success_threshold=2,
        timeout=60.0,
        half_open_max_requests=2,
    ),
}


# Global registry
_global_registry: Optional[CircuitBreakerRegistry] = None


def get_circuit_registry() -> CircuitBreakerRegistry:
    """Get global circuit breaker registry."""
    global _global_registry
    if _global_registry is None:
        _global_registry = CircuitBreakerRegistry()
        for name, config in DEFAULT_CIRCUIT_CONFIGS.items():
            _global_registry.get_or_create(name, config)
    return _global_registry


async def close_circuit_registry() -> None:
    """Close global circuit breaker registry."""
    global _global_registry
    if _global_registry:
        await _global_registry.reset_all()
    _global_registry = None