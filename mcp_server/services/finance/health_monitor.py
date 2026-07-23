"""Health monitor for finance providers."""

from __future__ import annotations

import asyncio
import logging
import time
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Callable, Awaitable

from mcp_server.services.finance.finance_provider import BaseFinanceProvider

logger = logging.getLogger(__name__)


@dataclass
class HealthCheckResult:
    """Result of a health check."""
    provider_name: str
    healthy: bool
    latency_ms: float
    timestamp: datetime
    error: str | None = None
    details: dict[str, Any] = field(default_factory=dict)


class HealthMonitor:
    """Monitors health of finance providers."""

    def __init__(
        self,
        providers: dict[str, BaseFinanceProvider],
        check_interval: int = 30,
        failure_threshold: int = 3,
        recovery_threshold: int = 2,
    ):
        self._providers = providers
        self._check_interval = check_interval
        self._failure_threshold = failure_threshold
        self._recovery_threshold = recovery_threshold
        self._running = False
        self._monitor_task: asyncio.Task | None = None
        self._health_history: dict[str, list[HealthCheckResult]] = {}
        self._max_history = 100
        self._callbacks: list[Callable[[HealthCheckResult], Awaitable[None]]] = []

    def add_callback(self, callback: Callable[[HealthCheckResult], Awaitable[None]]) -> None:
        """Add callback to be called on health check results."""
        self._callbacks.append(callback)

    async def start(self) -> None:
        """Start health monitoring."""
        self._running = True
        self._monitor_task = asyncio.create_task(self._monitor_loop())
        logger.info("Health monitor started")

    async def stop(self) -> None:
        """Stop health monitoring."""
        self._running = False
        if self._monitor_task:
            self._monitor_task.cancel()
            try:
                await self._monitor_task
            except asyncio.CancelledError:
                pass
        logger.info("Health monitor stopped")

    async def _monitor_loop(self) -> None:
        """Main monitoring loop."""
        while self._running:
            try:
                await self._check_all_providers()
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Health monitor error: {e}")

            await asyncio.sleep(self._check_interval)

    async def _check_all_providers(self) -> None:
        """Check health of all providers."""
        for name, provider in self._providers.items():
            try:
                result = await self._check_provider(name, provider)
                self._record_result(result)
                await self._notify_callbacks(result)
            except Exception as e:
                logger.error(f"Health check failed for {name}: {e}")

    async def _check_provider(self, name: str, provider: BaseFinanceProvider) -> HealthCheckResult:
        """Check health of a single provider."""
        start = time.perf_counter()
        try:
            health = await provider.health_check()
            latency_ms = (time.perf_counter() - start) * 1000

            return HealthCheckResult(
                provider_name=name,
                healthy=health.healthy,
                latency_ms=latency_ms,
                timestamp=datetime.now(timezone.utc),
                error=health.error,
                details={
                    "consecutive_failures": health.consecutive_failures,
                    "consecutive_successes": health.consecutive_successes,
                },
            )
        except Exception as e:
            latency_ms = (time.perf_counter() - start) * 1000
            return HealthCheckResult(
                provider_name=name,
                healthy=False,
                latency_ms=latency_ms,
                timestamp=datetime.now(timezone.utc),
                error=str(e),
            )

    def _record_result(self, result: HealthCheckResult) -> None:
        """Record health check result."""
        if result.provider_name not in self._health_history:
            self._health_history[result.provider_name] = []

        history = self._health_history[result.provider_name]
        history.append(result)

        # Trim history
        if len(history) > self._max_history:
            history.pop(0)

    async def _notify_callbacks(self, result: HealthCheckResult) -> None:
        """Notify all callbacks of health check result."""
        for callback in self._callbacks:
            try:
                await callback(result)
            except Exception as e:
                logger.error(f"Health monitor callback error: {e}")

    async def check_now(self, provider_name: str | None = None) -> list[HealthCheckResult]:
        """Manually trigger health check."""
        results = []
        providers = self._providers

        if provider_name:
            if provider_name not in providers:
                raise ValueError(f"Provider not found: {provider_name}")
            providers = {provider_name: providers[provider_name]}

        for name, provider in providers.items():
            result = await self._check_provider(name, provider)
            self._record_result(result)
            await self._notify_callbacks(result)
            results.append(result)

        return results

    def get_status(self) -> dict[str, Any]:
        """Get current health status of all providers."""
        return {
            name: {
                "healthy": p.health.healthy,
                "latency_ms": p.health.latency_ms,
                "last_check": p.health.last_check.isoformat() if p.health.last_check else None,
                "error": p.health.error,
                "consecutive_failures": p.health.consecutive_failures,
                "consecutive_successes": p.health.consecutive_successes,
                "recent_results": [
                    {
                        "healthy": r.healthy,
                        "latency_ms": r.latency_ms,
                        "timestamp": r.timestamp.isoformat(),
                        "error": r.error,
                    }
                    for r in self._health_history.get(name, [])[-10:]
                ],
            }
            for name, p in self._providers.items()
        }

    def get_uptime(self, provider_name: str, window_minutes: int = 60) -> float:
        """Get uptime percentage for a provider over the last window."""
        if provider_name not in self._health_history:
            return 100.0

        history = self._health_history[provider_name]
        if not history:
            return 100.0

        cutoff = datetime.now(timezone.utc).timestamp() - (window_minutes * 60)
        recent = [r for r in history if r.timestamp.timestamp() > cutoff]

        if not recent:
            return 100.0

        healthy_count = sum(1 for r in recent if r.healthy)
        return (healthy_count / len(recent)) * 100.0

    def get_average_latency(self, provider_name: str, window_minutes: int = 60) -> float | None:
        """Get average latency for a provider over the last window."""
        if provider_name not in self._health_history:
            return None

        history = self._health_history[provider_name]
        if not history:
            return None

        cutoff = datetime.now(timezone.utc).timestamp() - (window_minutes * 60)
        recent = [r for r in history if r.timestamp.timestamp() > cutoff and r.healthy]

        if not recent:
            return None

        return sum(r.latency_ms for r in recent) / len(recent)