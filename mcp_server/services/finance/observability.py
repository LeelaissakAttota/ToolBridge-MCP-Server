"""Observability and metrics for finance services."""

from __future__ import annotations

import asyncio
import time
from collections import defaultdict
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Optional
from enum import Enum
import threading


class MetricType(Enum):
    """Types of metrics."""
    COUNTER = "counter"
    GAUGE = "gauge"
    HISTOGRAM = "histogram"
    SUMMARY = "summary"


@dataclass
class MetricPoint:
    """Single metric data point."""
    name: str
    value: float
    timestamp: datetime
    labels: dict[str, str]
    metric_type: MetricType


@dataclass
class MetricSummary:
    """Summary statistics for a metric."""
    count: int = 0
    sum: float = 0.0
    min: float = float('inf')
    max: float = float('-inf')
    avg: float = 0.0

    def update(self, value: float) -> None:
        self.count += 1
        self.sum += value
        self.min = min(self.min, value)
        self.max = max(self.max, value)
        self.avg = self.sum / self.count


class MetricsCollector:
    """
    Centralized metrics collector for finance services.

    Collects:
    - Request latency (histogram)
    - Provider usage (counter)
    - Failures (counter)
    - Retries (counter)
    - Cache hit ratio (gauge)
    - Token usage (counter)
    - Cost tracking (counter)
    """

    def __init__(self):
        self._metrics: dict[str, MetricSummary] = {}
        self._metric_points: list[MetricPoint] = []
        self._lock = threading.Lock()
        self._max_points = 10000

    def increment(self, name: str, value: float = 1.0, labels: Optional[dict[str, str]] = None) -> None:
        """Increment a counter metric."""
        key = self._make_key(name, labels)
        with self._lock:
            if key not in self._metrics:
                self._metrics[key] = MetricSummary()
            self._metrics[key].update(value)
            self._add_point(name, value, labels, MetricType.COUNTER)

    def gauge(self, name: str, value: float, labels: Optional[dict[str, str]] = None) -> None:
        """Set a gauge metric."""
        key = self._make_key(name, labels)
        with self._lock:
            if key not in self._metrics:
                self._metrics[key] = MetricSummary()
            self._metrics[key].update(value)
            self._add_point(name, value, labels, MetricType.GAUGE)

    def histogram(self, name: str, value: float, labels: Optional[dict[str, str]] = None) -> None:
        """Record a histogram value (e.g., latency)."""
        key = self._make_key(name, labels)
        with self._lock:
            if key not in self._metrics:
                self._metrics[key] = MetricSummary()
            self._metrics[key].update(value)
            self._add_point(name, value, labels, MetricType.HISTOGRAM)

    def _make_key(self, name: str, labels: Optional[dict[str, str]] = None) -> str:
        if not labels:
            return name
        label_str = ",".join(f"{k}={v}" for k, v in sorted(labels.items()))
        return f"{name}{{{label_str}}}"

    def _add_point(self, name: str, value: float, labels: Optional[dict[str, str]], mtype: MetricType) -> None:
        point = MetricPoint(
            name=name,
            value=value,
            timestamp=datetime.now(timezone.utc),
            labels=labels or {},
            metric_type=mtype,
        )
        self._metric_points.append(point)
        if len(self._metric_points) > self._max_points:
            self._metric_points = self._metric_points[-self._max_points:]

    def get_metric(self, name: str, labels: Optional[dict[str, str]] = None) -> Optional[MetricSummary]:
        """Get metric summary."""
        key = self._make_key(name, labels)
        with self._lock:
            return self._metrics.get(key)

    def get_all_metrics(self) -> dict[str, MetricSummary]:
        """Get all metrics."""
        with self._lock:
            return self._metrics.copy()

    def get_points(self, name: Optional[str] = None, since: Optional[datetime] = None) -> list[MetricPoint]:
        """Get metric points with optional filtering."""
        with self._lock:
            points = self._metric_points
            if name:
                points = [p for p in points if p.name == name]
            if since:
                points = [p for p in points if p.timestamp >= since]
            return points

    def get_provider_metric(self, name: str) -> None:
        """Reset a specific metric."""
        with self._lock:
            keys_to_remove = [k for k in self._metrics if k.startswith(name)]
            for k in keys_to_remove:
                del self._metrics[k]

    def reset_all(self) -> None:
        """Reset all metrics."""
        with self._lock:
            self._metrics.clear()
            self._metric_points.clear()


# Health check types
class HealthStatus(Enum):
    """Health check status."""
    HEALTHY = "healthy"
    DEGRADED = "degraded"
    UNHEALTHY = "unhealthy"
    UNKNOWN = "unknown"


@dataclass
class HealthCheckResult:
    """Result of a health check."""
    name: str
    status: HealthStatus
    message: str = ""
    latency_ms: float = 0.0
    details: dict[str, Any] = field(default_factory=dict)
    timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))


class HealthMonitor:
    """
    Health monitoring for finance services and providers.

    Features:
    - Periodic health checks
    - Status aggregation
    - Alerting on degradation
    - Health dashboard data
    """

    def __init__(self, check_interval: int = 30):
        self._checks: dict[str, Callable[[], HealthCheckResult]] = {}
        self._results: dict[str, HealthCheckResult] = {}
        self._check_interval = check_interval
        self._running = False
        self._task: Optional[asyncio.Task] = None
        self._lock = asyncio.Lock()

    def register_check(self, name: str, check_func: Callable[[], HealthCheckResult]) -> None:
        """Register a health check function."""
        self._checks[name] = check_func

    async def run_check(self, name: str) -> HealthCheckResult:
        """Run a single health check."""
        check_func = self._checks.get(name)
        if not check_func:
            return HealthCheckResult(
                name=name,
                status=HealthStatus.UNKNOWN,
                message="Check not found",
            )

        start = time.perf_counter()
        try:
            result = check_func()
            result.latency_ms = (time.perf_counter() - start) * 1000
        except Exception as e:
            result = HealthCheckResult(
                name=name,
                status=HealthStatus.UNHEALTHY,
                message=str(e),
                latency_ms=(time.perf_counter() - start) * 1000,
            )

        self._results[name] = result
        return result

    async def run_all_checks(self) -> dict[str, HealthCheckResult]:
        """Run all registered health checks."""
        results = {}
        for name in self._checks:
            results[name] = await self.run_check(name)
        return results

    async def start(self) -> None:
        """Start periodic health checks."""
        if self._running:
            return
        self._running = True
        self._task = asyncio.create_task(self._check_loop())

    async def stop(self) -> None:
        """Stop periodic health checks."""
        self._running = False
        if self._task:
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass

    async def _check_loop(self) -> None:
        """Background health check loop."""
        while self._running:
            try:
                await self.run_all_checks()
            except Exception as e:
                print(f"Health check error: {e}")
            await asyncio.sleep(self._check_interval)

    def get_status(self, name: Optional[str] = None) -> dict[str, Any]:
        """Get health status."""
        if name:
            result = self._results.get(name)
            if not result:
                return {"name": name, "status": "unknown", "message": "Not checked yet"}
            return {
                "name": result.name,
                "status": result.status.value,
                "message": result.message,
                "latency_ms": result.latency_ms,
                "details": result.details,
                "timestamp": result.timestamp.isoformat(),
            }

        # Aggregate status
        statuses = [r.status for r in self._results.values()]
        if not statuses:
            overall = HealthStatus.UNKNOWN
        elif HealthStatus.UNHEALTHY in statuses:
            overall = HealthStatus.UNHEALTHY
        elif HealthStatus.DEGRADED in statuses:
            overall = HealthStatus.DEGRADED
        else:
            overall = HealthStatus.HEALTHY

        return {
            "overall": overall.value,
            "checks": {
                name: {
                    "status": result.status.value,
                    "message": result.message,
                    "latency_ms": result.latency_ms,
                }
                for name, result in self._results.items()
            },
        }


# Global instances
_global_metrics: Optional[MetricsCollector] = None
_global_health: Optional[HealthMonitor] = None


def get_metrics() -> MetricsCollector:
    """Get global metrics collector."""
    global _global_metrics
    if _global_metrics is None:
        _global_metrics = MetricsCollector()
    return _global_metrics


def get_health() -> HealthMonitor:
    """Get global health monitor."""
    global _global_health
    if _global_health is None:
        _global_health = HealthMonitor()
    return _global_health


async def init_observability(check_interval: int = 30) -> tuple[MetricsCollector, HealthMonitor]:
    """Initialize global observability."""
    global _global_metrics, _global_health
    _global_metrics = MetricsCollector()
    _global_health = HealthMonitor(check_interval=check_interval)
    await _global_health.start()
    return _global_metrics, _global_health


async def close_observability() -> None:
    """Close global observability."""
    global _global_metrics, _global_health
    if _global_health:
        await _global_health.stop()
        _global_health = None
    _global_metrics = None


# Convenience functions for common metrics
def record_request_latency(provider: str, operation: str, latency_ms: float) -> None:
    """Record request latency."""
    get_metrics().histogram(
        "finance_request_latency_ms",
        latency_ms,
        labels={"provider": provider, "operation": operation}
    )


def record_provider_request(provider: str, success: bool) -> None:
    """Record provider request."""
    get_metrics().increment(
        "finance_provider_requests_total",
        1.0,
        labels={"provider": provider, "result": "success" if success else "failure"}
    )


def record_retry(provider: str) -> None:
    """Record retry attempt."""
    get_metrics().increment(
        "finance_retries_total",
        1.0,
        labels={"provider": provider}
    )


def record_cache_hit(provider: str) -> None:
    """Record cache hit."""
    get_metrics().increment(
        "finance_cache_hits_total",
        1.0,
        labels={"provider": provider}
    )


def record_cache_miss(provider: str) -> None:
    """Record cache miss."""
    get_metrics().increment(
        "finance_cache_misses_total",
        1.0,
        labels={"provider": provider}
    )


def record_token_usage(provider: str, prompt_tokens: int, completion_tokens: int) -> None:
    """Record LLM token usage."""
    metrics = get_metrics()
    metrics.increment("finance_llm_prompt_tokens_total", float(prompt_tokens), labels={"provider": provider})
    metrics.increment("finance_llm_completion_tokens_total", float(completion_tokens), labels={"provider": provider})


def record_cost(provider: str, cost: float) -> None:
    """Record API cost."""
    get_metrics().increment(
        "finance_cost_usd_total",
        cost,
        labels={"provider": provider}
    )