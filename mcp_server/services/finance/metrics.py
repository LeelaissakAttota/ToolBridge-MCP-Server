"""Metrics collection for finance services."""

from __future__ import annotations

import time
import asyncio
import logging
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any
from collections import defaultdict

logger = logging.getLogger(__name__)


@dataclass
class ServiceMetrics:
    """Metrics for a service."""
    total_requests: int = 0
    successful_requests: int = 0
    failed_requests: int = 0
    total_latency_ms: float = 0.0
    min_latency_ms: float = float('inf')
    max_latency_ms: float = 0.0
    errors_by_type: dict[str, int] = field(default_factory=lambda: defaultdict(int))
    last_request_time: datetime | None = None
    last_error_time: datetime | None = None

    def record_request(self, success: bool, latency_ms: float, error_type: str | None = None) -> None:
        """Record a request."""
        self.total_requests += 1
        self.total_latency_ms += latency_ms
        self.min_latency_ms = min(self.min_latency_ms, latency_ms)
        self.max_latency_ms = max(self.max_latency_ms, latency_ms)
        self.last_request_time = datetime.now(timezone.utc)

        if success:
            self.successful_requests += 1
        else:
            self.failed_requests += 1
            if error_type:
                self.errors_by_type[error_type] += 1
            self.last_error_time = datetime.now(timezone.utc)

    @property
    def success_rate(self) -> float:
        if self.total_requests == 0:
            return 0.0
        return self.successful_requests / self.total_requests

    @property
    def average_latency_ms(self) -> float:
        if self.total_requests == 0:
            return 0.0
        return self.total_latency_ms / self.total_requests

    def to_dict(self) -> dict[str, Any]:
        return {
            "total_requests": self.total_requests,
            "successful_requests": self.successful_requests,
            "failed_requests": self.failed_requests,
            "success_rate": self.success_rate,
            "average_latency_ms": self.average_latency_ms,
            "min_latency_ms": self.min_latency_ms if self.min_latency_ms != float('inf') else 0,
            "max_latency_ms": self.max_latency_ms,
            "errors_by_type": dict(self.errors_by_type),
            "last_request_time": self.last_request_time.isoformat() if self.last_request_time else None,
            "last_error_time": self.last_error_time.isoformat() if self.last_error_time else None,
        }


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

    def record_success(self, latency_ms: float) -> None:
        self.total_requests += 1
        self.successful_requests += 1
        self.total_latency_ms += latency_ms

    def record_failure(self) -> None:
        self.total_requests += 1
        self.failed_requests += 1

    def record_retry(self) -> None:
        self.retry_count += 1

    def record_failover(self) -> None:
        self.failover_count += 1

    def record_cache_hit(self) -> None:
        self.cache_hits += 1

    def record_cache_miss(self) -> None:
        self.cache_misses += 1

    @property
    def cache_hit_rate(self) -> float:
        total = self.cache_hits + self.cache_misses
        if total == 0:
            return 0.0
        return self.cache_hits / total

    @property
    def average_latency_ms(self) -> float:
        if self.total_requests == 0:
            return 0.0
        return self.total_latency_ms / self.total_requests

    def to_dict(self) -> dict[str, Any]:
        return {
            "total_requests": self.total_requests,
            "successful_requests": self.successful_requests,
            "failed_requests": self.failed_requests,
            "retry_count": self.retry_count,
            "failover_count": self.failover_count,
            "cache_hits": self.cache_hits,
            "cache_misses": self.cache_misses,
            "cache_hit_rate": self.cache_hit_rate,
            "average_latency_ms": self.average_latency_ms,
        }


class MetricsCollector:
    """Centralized metrics collection."""

    def __init__(self):
        self._service_metrics: dict[str, ServiceMetrics] = {}
        self._provider_metrics: dict[str, ProviderMetrics] = {}
        self._lock = asyncio.Lock()

    def get_service_metrics(self, service_name: str) -> ServiceMetrics:
        """Get or create service metrics."""
        if service_name not in self._service_metrics:
            self._service_metrics[service_name] = ServiceMetrics()
        return self._service_metrics[service_name]

    def get_provider_metrics(self, provider_name: str) -> ProviderMetrics:
        """Get or create provider metrics."""
        if provider_name not in self._provider_metrics:
            self._provider_metrics[provider_name] = ProviderMetrics()
        return self._provider_metrics[provider_name]

    async def record_service_request(
        self,
        service_name: str,
        success: bool,
        latency_ms: float,
        error_type: str | None = None,
    ) -> None:
        """Record a service request."""
        async with self._lock:
            metrics = self.get_service_metrics(service_name)
            metrics.record_request(success, latency_ms, error_type)

    async def record_provider_request(
        self,
        provider_name: str,
        success: bool,
        latency_ms: float,
    ) -> None:
        """Record a provider request."""
        async with self._lock:
            metrics = self.get_provider_metrics(provider_name)
            if success:
                metrics.record_success(latency_ms)
            else:
                metrics.record_failure()

    async def record_provider_retry(self, provider_name: str) -> None:
        """Record a provider retry."""
        async with self._lock:
            metrics = self.get_provider_metrics(provider_name)
            metrics.record_retry()

    async def record_provider_failover(self, provider_name: str) -> None:
        """Record a provider failover."""
        async with self._lock:
            metrics = self.get_provider_metrics(provider_name)
            metrics.record_failover()

    async def record_cache_hit(self, provider_name: str) -> None:
        """Record a cache hit."""
        async with self._lock:
            metrics = self.get_provider_metrics(provider_name)
            metrics.record_cache_hit()

    async def record_cache_miss(self, provider_name: str) -> None:
        """Record a cache miss."""
        async with self._lock:
            metrics = self.get_provider_metrics(provider_name)
            metrics.record_cache_miss()

    async def get_all_metrics(self) -> dict[str, Any]:
        """Get all metrics."""
        async with self._lock:
            return {
                "services": {
                    name: metrics.to_dict()
                    for name, metrics in self._service_metrics.items()
                },
                "providers": {
                    name: metrics.to_dict()
                    for name, metrics in self._provider_metrics.items()
                },
            }

    async def reset(self) -> None:
        """Reset all metrics."""
        async with self._lock:
            self._service_metrics.clear()
            self._provider_metrics.clear()


# Global metrics collector
metrics_collector = MetricsCollector()