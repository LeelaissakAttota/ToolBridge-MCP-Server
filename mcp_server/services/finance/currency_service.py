"""Currency service for foreign exchange data."""

from __future__ import annotations

import logging
import time
from typing import Any, Optional

from mcp_server.services.finance.exceptions import (
    FinanceServiceError,
    ProviderError,
    InvalidCurrencyError,
    CurrencyError,
)
from mcp_server.services.finance.provider_router import ProviderRouter
from mcp_server.services.finance.metrics import metrics_collector

logger = logging.getLogger(__name__)


class CurrencyService:
    """High-level currency service for exchange rates and conversions."""

    def __init__(self, router: ProviderRouter):
        self.router = router
        self._running = False

    async def start(self) -> None:
        """Start the service."""
        await self.router.start()
        self._running = True
        logger.info("Currency service started")

    async def stop(self) -> None:
        """Stop the service."""
        await self.router.stop()
        self._running = False
        logger.info("Currency service stopped")

    async def get_exchange_rate(
        self,
        from_currency: str,
        to_currency: str,
        date: str = "latest",
    ) -> dict[str, Any]:
        """Get exchange rate between two currencies.

        Args:
            from_currency: Source currency code (ISO 4217)
            to_currency: Target currency code (ISO 4217)
            date: Date for historical rate or "latest"

        Returns:
            Dictionary with rate data

        Raises:
            InvalidCurrencyError: If currency not supported
            CurrencyError: For other errors
        """
        from_currency = from_currency.upper()
        to_currency = to_currency.upper()

        if from_currency == to_currency:
            return {
                "from_currency": from_currency,
                "to_currency": to_currency,
                "rate": 1.0,
                "amount": 1.0,
                "converted_amount": 1.0,
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "date": date if date != "latest" else datetime.now(timezone.utc).date().isoformat(),
                "source": "identity",
            }

        start = time.perf_counter()
        try:
            rate_data = await self.router.get_exchange_rate(from_currency, to_currency, date)
            latency_ms = (time.perf_counter() - start) * 1000
            metrics_collector.record_service_request("currency_service", True, latency_ms)
            return rate_data

        except InvalidCurrencyError:
            metrics_collector.record_service_request("currency_service", False, (time.perf_counter() - start) * 1000)
            raise
        except ProviderError as e:
            metrics_collector.record_service_request("currency_service", False, (time.perf_counter() - start) * 1000)
            raise CurrencyError(f"Failed to get rate for {from_currency}/{to_currency}: {e}") from e
        except Exception as e:
            metrics_collector.record_service_request("currency_service", False, (time.perf_counter() - start) * 1000)
            logger.error(f"Unexpected error getting rate for {from_currency}/{to_currency}: {e}")
            raise CurrencyError(f"Unexpected error: {e}") from e

    async def convert_currency(
        self,
        from_currency: str,
        to_currency: str,
        amount: float,
        date: str = "latest",
    ) -> dict[str, Any]:
        """Convert amount from one currency to another.

        Args:
            from_currency: Source currency code (ISO 4217)
            to_currency: Target currency code (ISO 4217)
            amount: Amount to convert
            date: Date for historical rate or "latest"

        Returns:
            Dictionary with conversion result

        Raises:
            InvalidCurrencyError: If currency not supported
            CurrencyError: For other errors
        """
        if amount <= 0:
            raise CurrencyError("Amount must be positive")

        rate_data = await self.get_exchange_rate(from_currency, to_currency, date)
        converted_amount = round(amount * rate_data["rate"], 6)

        return {
            **rate_data,
            "amount": amount,
            "converted_amount": converted_amount,
        }

    async def get_supported_currencies(self) -> list[dict[str, Any]]:
        """Get list of all supported currencies.

        Returns:
            List of currency dictionaries with code, name, symbol
        """
        start = time.perf_counter()
        try:
            currencies = await self.router.get_supported_currencies()
            latency_ms = (time.perf_counter() - start) * 1000
            metrics_collector.record_service_request("currency_service", True, latency_ms)
            return currencies
        except Exception as e:
            latency_ms = (time.perf_counter() - start) * 1000
            metrics_collector.record_service_request("currency_service", False, latency_ms)
            logger.error(f"Error getting supported currencies: {e}")
            raise CurrencyError(f"Failed to get currencies: {e}") from e

    async def health_check(self) -> dict[str, Any]:
        """Check health of all currency providers."""
        provider_health = await self.router.health_check_all()
        return {
            "service": "currency",
            "status": "healthy" if any(h.healthy for h in provider_health.values()) else "degraded",
            "providers": {
                name: {
                    "healthy": health.healthy,
                    "latency_ms": health.latency_ms,
                    "last_check": health.last_check.isoformat() if health.last_check else None,
                    "error": health.error,
                }
                for name, health in provider_health.items()
            },
        }