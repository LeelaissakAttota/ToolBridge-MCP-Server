"""Base provider interface for finance data providers."""

from __future__ import annotations

import logging
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Optional

logger = logging.getLogger(__name__)


@dataclass
class ProviderMetrics:
    """Metrics for a provider."""
    total_requests: int = 0
    successful_requests: int = 0
    failed_requests: int = 0
    retry_count: int = 0
    failover_count: int = 0
    cache_hits: int = 0
    cache_misses: int = 0
    total_latency_ms: float = 0.0
    last_success: Optional[datetime] = None
    last_failure: Optional[datetime] = None

    @property
    def success_rate(self) -> float:
        if self.total_requests == 0:
            return 0.0
        return self.successful_requests / self.total_requests

    @property
    def average_latency_ms(self) -> float:
        if self.successful_requests == 0:
            return 0.0
        return self.total_latency_ms / self.successful_requests

    def record_success(self, latency_ms: float) -> None:
        self.total_requests += 1
        self.successful_requests += 1
        self.total_latency_ms += latency_ms
        self.last_success = datetime.now(timezone.utc)

    def record_failure(self) -> None:
        self.total_requests += 1
        self.failed_requests += 1
        self.last_failure = datetime.now(timezone.utc)

    def record_retry(self) -> None:
        self.retry_count += 1

    def record_failover(self) -> None:
        self.failover_count += 1

    def record_cache_hit(self) -> None:
        self.cache_hits += 1

    def record_cache_miss(self) -> None:
        self.cache_misses += 1


@dataclass
class ProviderHealth:
    """Health status of a provider."""
    name: str
    healthy: bool = True
    latency_ms: float = 0.0
    last_check: Optional[datetime] = None
    error: Optional[str] = None
    consecutive_failures: int = 0
    consecutive_successes: int = 0

    def mark_healthy(self, latency_ms: float) -> None:
        self.healthy = True
        self.latency_ms = latency_ms
        self.last_check = datetime.now(timezone.utc)
        self.consecutive_failures = 0
        self.consecutive_successes += 1

    def mark_unhealthy(self, error: str) -> None:
        self.healthy = False
        self.error = error
        self.last_check = datetime.now(timezone.utc)
        self.consecutive_failures += 1
        self.consecutive_successes = 0


class BaseFinanceProvider(ABC):
    """Abstract base class for all finance data providers."""

    def __init__(self, name: str, config: dict[str, Any] | None = None):
        self.name = name
        self.config = config or {}
        self.enabled = self.config.get("enabled", True)
        self.timeout = self.config.get("timeout", 30)
        self.max_retries = self.config.get("max_retries", 3)
        self.metrics = ProviderMetrics()
        self.health = ProviderHealth(name=name)
        self._cache: dict[str, tuple[Any, datetime]] = {}
        self._cache_ttl = self.config.get("cache_ttl", 300)  # 5 minutes default

    @abstractmethod
    async def get_stock_quote(self, symbol: str) -> dict[str, Any]:
        """Get current stock quote.

        Args:
            symbol: Stock symbol (e.g., AAPL, RELIANCE.NS)

        Returns:
            Dictionary with quote data

        Raises:
            ProviderError: If provider fails
            SymbolNotFoundError: If symbol not found
        """
        pass

    @abstractmethod
    async def get_exchange_rate(self, from_currency: str, to_currency: str, date: str = "latest") -> dict[str, Any]:
        """Get exchange rate.

        Args:
            from_currency: Source currency (ISO 4217)
            to_currency: Target currency (ISO 4217)
            date: Date for historical rate or "latest"

        Returns:
            Dictionary with rate data

        Raises:
            ProviderError: If provider fails
            InvalidCurrencyError: If currency not supported
        """
        pass

    @abstractmethod
    async def get_supported_currencies(self) -> list[dict[str, Any]]:
        """Get list of supported currencies.

        Returns:
            List of currency dictionaries with code, name, symbol
        """
        pass

    @abstractmethod
    async def health_check(self) -> ProviderHealth:
        """Check provider health.

        Returns:
            ProviderHealth status
        """
        pass

    async def close(self) -> None:
        """Cleanup resources."""
        pass

    def _is_cache_valid(self, cached_time: datetime) -> bool:
        elapsed = (datetime.now(timezone.utc) - cached_time).total_seconds()
        return elapsed < self._cache_ttl

    def _get_from_cache(self, key: str) -> Optional[Any]:
        if key in self._cache:
            value, cached_time = self._cache[key]
            if self._is_cache_valid(cached_time):
                self.metrics.record_cache_hit()
                logger.debug(f"Cache hit for {self.name}: {key}")
                return value
            else:
                del self._cache[key]
        self.metrics.record_cache_miss()
        return None

    def _store_in_cache(self, key: str, value: Any) -> None:
        self._cache[key] = (value, datetime.now(timezone.utc))
        logger.debug(f"Cached {self.name}: {key}")

    def _record_success(self, latency_ms: float) -> None:
        self.metrics.record_success(latency_ms)
        self.health.mark_healthy(latency_ms)

    def _record_failure(self, error: str) -> None:
        self.metrics.record_failure()
        self.health.mark_unhealthy(error)

    def __repr__(self) -> str:
        return f"<{self.__class__.__name__}(name='{self.name}', healthy={self.health.healthy})>"