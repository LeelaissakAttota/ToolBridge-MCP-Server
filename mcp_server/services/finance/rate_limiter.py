"""Rate limiting implementation for finance providers."""

from __future__ import annotations

import asyncio
import time
from abc import ABC, abstractmethod
from collections import deque
from dataclasses import dataclass, field
from typing import Any, Optional


@dataclass
class RateLimitConfig:
    """Configuration for rate limiting."""
    requests_per_second: float = 10.0
    requests_per_minute: int = 100
    requests_per_hour: int = 1000
    burst_allowance: int = 5
    provider_name: str = "default"


@dataclass
class RateLimitStatus:
    """Current rate limit status."""
    allowed: bool
    remaining: int
    reset_time: float
    retry_after: float = 0.0
    limit: int = 0


class RateLimiter(ABC):
    """Abstract base class for rate limiters."""

    @abstractmethod
    async def acquire(self, tokens: int = 1) -> RateLimitStatus:
        """Acquire tokens for a request."""
        pass

    @abstractmethod
    async def release(self, tokens: int = 1) -> None:
        """Release tokens back (for canceled requests)."""
        pass

    @abstractmethod
    def get_status(self) -> RateLimitStatus:
        """Get current rate limit status."""
        pass


class TokenBucketRateLimiter(RateLimiter):
    """Token bucket rate limiter implementation."""

    def __init__(self, config: RateLimitConfig):
        self.config = config
        self._tokens = float(config.burst_allowance)
        self._max_tokens = float(config.burst_allowance)
        self._refill_rate = config.requests_per_second
        self._last_refill = time.monotonic()
        self._lock = asyncio.Lock()

    async def acquire(self, tokens: int = 1) -> RateLimitStatus:
        async with self._lock:
            now = time.monotonic()
            elapsed = now - self._last_refill
            self._tokens = min(self._max_tokens, self._tokens + elapsed * self._refill_rate)
            self._last_refill = now

            if self._tokens >= tokens:
                self._tokens -= tokens
                return RateLimitStatus(
                    allowed=True,
                    remaining=int(self._tokens),
                    reset_time=now + (tokens / self._refill_rate) if self._refill_rate > 0 else now,
                    limit=self.config.burst_allowance,
                )

            # Calculate wait time
            wait_time = (tokens - self._tokens) / self._refill_rate if self._refill_rate > 0 else float('inf')
            return RateLimitStatus(
                allowed=False,
                remaining=0,
                reset_time=now + wait_time,
                retry_after=wait_time,
                limit=self.config.burst_allowance,
            )

    async def release(self, tokens: int = 1) -> None:
        async with self._lock:
            self._tokens = min(self._max_tokens, self._tokens + tokens)

    def get_status(self) -> RateLimitStatus:
        now = time.monotonic()
        elapsed = now - self._last_refill
        current_tokens = min(self._max_tokens, self._tokens + elapsed * self._refill_rate)
        return RateLimitStatus(
            allowed=current_tokens >= 1,
            remaining=int(current_tokens),
            reset_time=now + (1 / self._refill_rate) if self._refill_rate > 0 else now,
            limit=self.config.burst_allowance,
        )


class SlidingWindowRateLimiter(RateLimiter):
    """Sliding window rate limiter for more precise limiting."""

    def __init__(self, config: RateLimitConfig):
        self.config = config
        self._requests: deque[float] = deque()
        self._lock = asyncio.Lock()

    def _clean_old_requests(self, now: float) -> None:
        """Remove requests outside the sliding window."""
        cutoff = now - 60.0  # 1 minute window
        while self._requests and self._requests[0] < cutoff:
            self._requests.popleft()

    async def acquire(self, tokens: int = 1) -> RateLimitStatus:
        async with self._lock:
            now = time.monotonic()
            self._clean_old_requests(now)

            if len(self._requests) < self.config.requests_per_minute:
                for _ in range(tokens):
                    self._requests.append(now)
                return RateLimitStatus(
                    allowed=True,
                    remaining=self.config.requests_per_minute - len(self._requests),
                    reset_time=now + 60.0,
                    limit=self.config.requests_per_minute,
                )

            # Calculate wait time until oldest request expires
            wait_time = (self._requests[0] + 60.0) - now
            return RateLimitStatus(
                allowed=False,
                remaining=0,
                reset_time=now + wait_time,
                retry_after=wait_time,
                limit=self.config.requests_per_minute,
            )

    async def release(self, tokens: int = 1) -> None:
        async with self._lock:
            now = time.monotonic()
            self._clean_old_requests(now)
            # Remove the most recent tokens (LIFO for fairness)
            for _ in range(min(tokens, len(self._requests))):
                self._requests.pop()

    def get_status(self) -> RateLimitStatus:
        now = time.monotonic()
        self._clean_old_requests(now)
        return RateLimitStatus(
            allowed=len(self._requests) < self.config.requests_per_minute,
            remaining=self.config.requests_per_minute - len(self._requests),
            reset_time=now + 60.0,
            limit=self.config.requests_per_minute,
        )


class MultiTierRateLimiter(RateLimiter):
    """Multi-tier rate limiter combining multiple strategies."""

    def __init__(self, config: RateLimitConfig):
        self.config = config
        self._second_limiter = TokenBucketRateLimiter(
            RateLimitConfig(
                requests_per_second=config.requests_per_second,
                burst_allowance=config.burst_allowance,
            )
        )
        self._minute_limiter = SlidingWindowRateLimiter(config)
        self._hour_limiter = SlidingWindowRateLimiter(
            RateLimitConfig(requests_per_minute=config.requests_per_hour)
        )

    async def acquire(self, tokens: int = 1) -> RateLimitStatus:
        # Check all tiers
        second_status = await self._second_limiter.acquire(tokens)
        if not second_status.allowed:
            return second_status

        minute_status = await self._minute_limiter.acquire(tokens)
        if not minute_status.allowed:
            # Release second tier token
            await self._second_limiter.release(tokens)
            return minute_status

        hour_status = await self._hour_limiter.acquire(tokens)
        if not hour_status.allowed:
            await self._second_limiter.release(tokens)
            await self._minute_limiter.release(tokens)
            return hour_status

        return RateLimitStatus(
            allowed=True,
            remaining=min(second_status.remaining, minute_status.remaining, hour_status.remaining),
            reset_time=min(second_status.reset_time, minute_status.reset_time, hour_status.reset_time),
            limit=min(second_status.limit, minute_status.limit, hour_status.limit),
        )

    async def release(self, tokens: int = 1) -> None:
        await self._second_limiter.release(tokens)
        await self._minute_limiter.release(tokens)
        await self._hour_limiter.release(tokens)

    def get_status(self) -> RateLimitStatus:
        second = self._second_limiter.get_status()
        minute = self._minute_limiter.get_status()
        hour = self._hour_limiter.get_status()
        return RateLimitStatus(
            allowed=second.allowed and minute.allowed and hour.allowed,
            remaining=min(second.remaining, minute.remaining, hour.remaining),
            reset_time=min(second.reset_time, minute.reset_time, hour.reset_time),
            limit=min(second.limit, minute.limit, hour.limit),
        )


class ProviderRateLimitManager:
    """Manages rate limiters for multiple providers."""

    def __init__(self):
        self._limiters: dict[str, RateLimiter] = {}
        self._configs: dict[str, RateLimitConfig] = {}
        self._lock = asyncio.Lock()

    def configure_provider(self, provider_name: str, config: RateLimitConfig) -> None:
        """Configure rate limiting for a provider."""
        self._configs[provider_name] = config

        # Create appropriate limiter based on config
        if config.requests_per_second < 1:
            # Use sliding window for low rates
            self._limiters[provider_name] = SlidingWindowRateLimiter(config)
        else:
            # Use multi-tier for higher rates
            self._limiters[provider_name] = MultiTierRateLimiter(config)

    def get_limiter(self, provider_name: str) -> Optional[RateLimiter]:
        """Get rate limiter for a provider."""
        return self._limiters.get(provider_name)

    async def acquire(self, provider_name: str, tokens: int = 1) -> RateLimitStatus:
        """Acquire rate limit token for a provider."""
        limiter = self._limiters.get(provider_name)
        if limiter is None:
            # No limiter configured, allow
            return RateLimitStatus(allowed=True, remaining=999, reset_time=0, limit=999)
        return await limiter.acquire(tokens)

    async def release(self, provider_name: str, tokens: int = 1) -> None:
        """Release rate limit token for a provider."""
        limiter = self._limiters.get(provider_name)
        if limiter:
            await limiter.release(tokens)

    def get_all_status(self) -> dict[str, RateLimitStatus]:
        """Get status of all rate limiters."""
        return {
            name: limiter.get_status()
            for name, limiter in self._limiters.items()
        }


# Default provider rate limit configurations
DEFAULT_PROVIDER_LIMITS = {
    "yahoo_finance": RateLimitConfig(
        requests_per_second=5.0,
        requests_per_minute=100,
        requests_per_hour=1000,
        burst_allowance=10,
        provider_name="yahoo_finance",
    ),
    "alpha_vantage": RateLimitConfig(
        requests_per_second=5.0,  # 5 requests per second for premium, 5 per minute for free
        requests_per_minute=5,  # Free tier: 5/min
        requests_per_hour=500,
        burst_allowance=5,
        provider_name="alpha_vantage",
    ),
    "twelve_data": RateLimitConfig(
        requests_per_second=8.0,
        requests_per_minute=60,  # Free tier
        requests_per_hour=600,
        burst_allowance=8,
        provider_name="twelve_data",
    ),
    "finnhub": RateLimitConfig(
        requests_per_second=10.0,
        requests_per_minute=60,  # Free tier
        requests_per_hour=1000,
        burst_allowance=10,
        provider_name="finnhub",
    ),
    "polygon": RateLimitConfig(
        requests_per_second=5.0,
        requests_per_minute=100,
        requests_per_hour=1000,
        burst_allowance=5,
        provider_name="polygon",
    ),
    "frankfurter": RateLimitConfig(
        requests_per_second=10.0,
        requests_per_minute=60,
        requests_per_hour=1000,
        burst_allowance=10,
        provider_name="frankfurter",
    ),
    "exchangerate_api": RateLimitConfig(
        requests_per_second=5.0,
        requests_per_minute=30,
        requests_per_hour=500,
        burst_allowance=5,
        provider_name="exchangerate_api",
    ),
    "currencylayer": RateLimitConfig(
        requests_per_second=5.0,
        requests_per_minute=30,
        requests_per_hour=500,
        burst_allowance=5,
        provider_name="currencylayer",
    ),
}


# Global rate limit manager
_global_rate_manager: Optional[ProviderRateLimitManager] = None


def get_rate_manager() -> ProviderRateLimitManager:
    """Get global rate limit manager."""
    global _global_rate_manager
    if _global_rate_manager is None:
        _global_rate_manager = ProviderRateLimitManager()
        for name, config in DEFAULT_PROVIDER_LIMITS.items():
            _global_rate_manager.configure_provider(name, config)
    return _global_rate_manager


async def close_rate_manager() -> None:
    """Close global rate limit manager."""
    global _global_rate_manager
    _global_rate_manager = None