"""Finance service for stock market data."""

from __future__ import annotations

import logging
import time
from typing import Any, Optional

from mcp_server.services.finance.exceptions import (
    FinanceServiceError,
    ProviderError,
    SymbolNotFoundError,
    MarketClosedError,
)
from mcp_server.services.finance.provider_router import ProviderRouter
from mcp_server.services.finance.metrics import metrics_collector

logger = logging.getLogger(__name__)


class FinanceService:
    """High-level finance service for stock market data."""

    def __init__(self, router: ProviderRouter):
        self.router = router
        self._running = False

    async def start(self) -> None:
        """Start the service."""
        await self.router.start()
        self._running = True
        logger.info("Finance service started")

    async def stop(self) -> None:
        """Stop the service."""
        await self.router.stop()
        self._running = False
        logger.info("Finance service stopped")

    async def get_stock_quote(self, symbol: str) -> dict[str, Any]:
        """Get stock quote for a symbol.

        Args:
            symbol: Stock symbol (e.g., AAPL, RELIANCE.NS)

        Returns:
            Dictionary with quote data

        Raises:
            SymbolNotFoundError: If symbol not found
            MarketClosedError: If market is closed and no real-time data
            FinanceServiceError: For other errors
        """
        if not symbol:
            raise FinanceServiceError("Symbol is required")

        start = time.perf_counter()
        try:
            quote = await self.router.get_stock_quote(symbol.upper())
            latency_ms = (time.perf_counter() - start) * 1000
            metrics_collector.record_service_request("finance_service", True, latency_ms)

            # Check if market is closed
            if quote.get("market_state") == "CLOSED":
                logger.warning(f"Market closed for {symbol}, returning last available price")

            return quote

        except SymbolNotFoundError:
            metrics_collector.record_service_request("finance_service", False, (time.perf_counter() - start) * 1000)
            raise
        except MarketClosedError:
            metrics_collector.record_service_request("finance_service", False, (time.perf_counter() - start) * 1000)
            raise
        except ProviderError as e:
            metrics_collector.record_service_request("finance_service", False, (time.perf_counter() - start) * 1000)
            raise FinanceServiceError(f"Failed to get quote for {symbol}: {e}") from e
        except Exception as e:
            metrics_collector.record_service_request("finance_service", False, (time.perf_counter() - start) * 1000)
            logger.error(f"Unexpected error getting quote for {symbol}: {e}")
            raise FinanceServiceError(f"Unexpected error: {e}") from e

    async def get_multiple_quotes(self, symbols: list[str]) -> dict[str, dict[str, Any]]:
        """Get quotes for multiple symbols.

        Args:
            symbols: List of stock symbols

        Returns:
            Dictionary mapping symbols to quote data (or error)
        """
        results = {}
        for symbol in symbols:
            try:
                results[symbol] = await self.get_stock_quote(symbol)
            except Exception as e:
                results[symbol] = {"error": str(e), "symbol": symbol}
        return results

    async def health_check(self) -> dict[str, Any]:
        """Check health of all providers."""
        provider_health = await self.router.health_check_all()
        return {
            "service": "finance",
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