"""Provider router with automatic failover."""

from __future__ import annotations

import asyncio
import logging
import time
from dataclasses import dataclass
from typing import Any, Optional, Callable, Awaitable

from mcp_server.services.finance.exceptions import (
    ProviderError,
    ProviderUnavailableError,
    RateLimitError,
)
from mcp_server.services.finance.finance_provider import BaseFinanceProvider
from mcp_server.services.finance.metrics import metrics_collector

logger = logging.getLogger(__name__)


@dataclass
class ProviderConfig:
    """Configuration for a provider in the router."""
    name: str
    enabled: bool = True
    priority: int = 0  # Lower = higher priority
    health_check_interval: int = 60  # seconds
    max_consecutive_failures: int = 3
    timeout: int = 30


@dataclass
class FailoverConfig:
    """Configuration for failover behavior."""
    enabled: bool = True
    max_retries: int = 3
    retry_delay_base: float = 1.0  # seconds
    retry_delay_max: float = 30.0  # seconds
    health_check_interval: int = 60  # seconds
    enable_background_health_checks: bool = True


class ProviderRouter:
    """Routes requests to providers with automatic failover."""

    def __init__(
        self,
        providers: list[BaseFinanceProvider],
        config: dict[str, ProviderConfig] | None = None,
        enable_failover: bool = True,
        enable_health_monitoring: bool = True,
    ):
        self._providers = {p.name: p for p in providers}
        self._config = config or {}
        self._enable_failover = enable_failover
        self._enable_health_monitoring = enable_health_monitoring
        self._health_monitor_task: Optional[asyncio.Task] = None
        self._running = False

        # Initialize provider configs
        for provider in providers:
            if provider.name not in self._config:
                self._config[provider.name] = ProviderConfig(
                    name=provider.name,
                    priority=len(self._config),
                )

    async def start(self) -> None:
        """Start the router and health monitoring."""
        self._running = True
        if self._enable_health_monitoring:
            self._health_monitor_task = asyncio.create_task(self._health_monitor_loop())
        logger.info(f"Provider router started with {len(self._providers)} providers")

    async def stop(self) -> None:
        """Stop the router."""
        self._running = False
        if self._health_monitor_task:
            self._health_monitor_task.cancel()
            try:
                await self._health_monitor_task
            except asyncio.CancelledError:
                pass
        logger.info("Provider router stopped")

    def get_available_providers(self) -> list[BaseFinanceProvider]:
        """Get list of available (enabled and healthy) providers sorted by priority."""
        providers = [
            p for p in self._providers.values()
            if self._config.get(p.name, ProviderConfig(name=p.name)).enabled
            and p.health.healthy
        ]
        return sorted(providers, key=lambda p: self._config.get(p.name, ProviderConfig(name=p.name)).priority)

    def get_all_providers(self) -> list[BaseFinanceProvider]:
        """Get all providers sorted by priority."""
        return sorted(
            self._providers.values(),
            key=lambda p: self._config.get(p.name, ProviderConfig(name=p.name)).priority
        )

    async def execute_with_failover(
        self,
        operation: Callable[[BaseFinanceProvider], Awaitable[Any]],
        service_name: str,
    ) -> Any:
        """Execute operation with automatic failover.

        Args:
            operation: Async function that takes a provider and returns a result
            service_name: Name of service for metrics

        Returns:
            Result from successful provider

        Raises:
            ProviderError: If all providers fail
        """
        available = self.get_available_providers()

        if not available:
            raise ProviderUnavailableError("No available providers")

        last_error = None

        for i, provider in enumerate(available):
            start_time = time.perf_counter()
            try:
                result = await operation(provider)
                latency_ms = (time.perf_counter() - start_time) * 1000

                # Record metrics
                metrics_collector.record_provider_request(provider.name, True, latency_ms)
                metrics_collector.record_service_request(service_name, True, latency_ms)

                if i > 0:
                    metrics_collector.record_failover(service_name)
                    logger.info(f"Failover successful for {service_name}: used {provider.name} (attempt {i + 1})")

                return result

            except RateLimitError:
                latency_ms = (time.perf_counter() - start_time) * 1000
                metrics_collector.record_provider_request(provider.name, False, latency_ms, "rate_limit")
                metrics_collector.record_service_request(service_name, False, latency_ms, "rate_limit")
                metrics_collector.record_rate_limit(service_name, provider.name)

                if not self._enable_failover or i == len(available) - 1:
                    raise
                logger.warning(f"Rate limit on {provider.name}, trying next provider")
                continue

            except ProviderError as e:
                latency_ms = (time.perf_counter() - start_time) * 1000
                metrics_collector.record_provider_request(provider.name, False, latency_ms, type(e).__name__)
                metrics_collector.record_service_request(service_name, False, latency_ms, type(e).__name__)

                last_error = e
                logger.warning(f"Provider {provider.name} failed: {e}")

                if not self._enable_failover or i == len(available) - 1:
                    break
                continue

            except Exception as e:
                latency_ms = (time.perf_counter() - start_time) * 1000
                metrics_collector.record_provider_request(provider.name, False, latency_ms, "unexpected")
                metrics_collector.record_service_request(service_name, False, latency_ms, "unexpected")

                last_error = ProviderError(f"Unexpected error: {e}", provider.name)
                logger.error(f"Unexpected error from {provider.name}: {e}")

                if not self._enable_failover or i == len(available) - 1:
                    break
                continue

        raise last_error or ProviderError("All providers failed", "unknown")

    async def _health_monitor_loop(self) -> None:
        """Background task to monitor provider health."""
        while self._running:
            try:
                await self._check_all_providers()
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Health monitor error: {e}")

            await asyncio.sleep(30)  # Check every 30 seconds

    async def _check_all_providers(self) -> None:
        """Check health of all providers."""
        for provider in self._providers.values():
            config = self._config.get(provider.name, ProviderConfig(name=provider.name))

            if not config.enabled:
                continue

            try:
                health = await provider.health_check()

                if not health.healthy:
                    provider.health.consecutive_failures += 1

                    if provider.health.consecutive_failures >= config.max_consecutive_failures:
                        logger.warning(
                            f"Provider {provider.name} marked unhealthy after "
                            f"{provider.health.consecutive_failures} consecutive failures"
                        )
                        provider.health.healthy = False
                else:
                    provider.health.consecutive_failures = 0
                    provider.health.healthy = True

            except Exception as e:
                logger.warning(f"Health check failed for {provider.name}: {e}")
                provider.health.consecutive_failures += 1
                if provider.health.consecutive_failures >= config.max_consecutive_failures:
                    provider.health.healthy = False

    async def get_provider_status(self) -> dict[str, Any]:
        """Get status of all providers."""
        return {
            name: {
                "healthy": p.health.healthy,
                "enabled": self._config.get(name, ProviderConfig(name=name)).enabled,
                "priority": self._config.get(name, ProviderConfig(name=name)).priority,
                "latency_ms": p.health.latency_ms,
                "last_check": p.health.last_check.isoformat() if p.health.last_check else None,
                "error": p.health.error,
                "consecutive_failures": p.health.consecutive_failures,
                "metrics": p.metrics.to_dict(),
            }
            for name, p in self._providers.items()
        }

    def enable_provider(self, name: str) -> bool:
        """Enable a provider."""
        if name in self._config:
            self._config[name].enabled = True
            if name in self._providers:
                self._providers[name].health.healthy = True
                self._providers[name].health.consecutive_failures = 0
            return True
        return False

    def disable_provider(self, name: str) -> bool:
        """Disable a provider."""
        if name in self._config:
            self._config[name].enabled = False
            if name in self._providers:
                self._providers[name].health.healthy = False
            return True
        return False

    def set_priority(self, name: str, priority: int) -> bool:
        """Set provider priority (lower = higher priority)."""
        if name in self._config:
            self._config[name].priority = priority
            return True
        return False


class FinanceProviderRouter(ProviderRouter):
    """Specialized router for stock price providers."""

    def __init__(
        self,
        providers: list[BaseFinanceProvider],
        **kwargs,
    ):
        super().__init__(providers, **kwargs)

    async def get_stock_quote(self, symbol: str, service_name: str = "stock_price") -> dict[str, Any]:
        """Get stock quote with failover."""
        return await self.execute_with_failover(
            lambda p: p.get_stock_quote(symbol),
            service_name,
        )

    async def get_exchange_rate(
        self,
        from_currency: str,
        to_currency: str,
        date: str = "latest",
        service_name: str = "currency_exchange",
    ) -> dict[str, Any]:
        """Get exchange rate with failover."""
        return await self.execute_with_failover(
            lambda p: p.get_exchange_rate(from_currency, to_currency, date),
            service_name,
        )

    async def get_supported_currencies(self, service_name: str = "currency_list") -> list[dict[str, Any]]:
        """Get supported currencies with failover."""
        return await self.execute_with_failover(
            lambda p: p.get_supported_currencies(),
            service_name,
        )