"""Market Movers Tool - Get top gainers, losers, most active stocks."""

from __future__ import annotations

import logging
from typing import Any, Optional

from mcp_server.tools.base import BaseTool
from mcp_server.tools.finance.advanced_schemas import (
    MARKET_MOVERS_INPUT_SCHEMA,
    MARKET_MOVERS_OUTPUT_SCHEMA,
)
from mcp_server.tools.finance.advanced_exceptions import MarketMoversError
from mcp_server.services.finance import FinanceService, FinanceServiceError

logger = logging.getLogger(__name__)


class MarketMoversTool(BaseTool):
    """Tool for retrieving market movers.

    Provides:
    - Top Gainers
    - Top Losers
    - Most Active (by volume)
    - Trending Stocks
    - Market Summary

    Uses Finance Service with automatic provider failover.
    """

    name = "market_movers"
    description = "Get market movers: top gainers, losers, most active stocks, and market summary"
    tags = ["finance", "stocks", "market-movers", "gainers", "losers", "active"]
    version = "1.0.0"
    author = "ToolBridge"

    def __init__(self, finance_service: Optional[Any] = None, config: dict[str, Any] | None = None):
        super().__init__(config)
        self._finance_service: Optional[FinanceService] = finance_service
        self._service_initialized = finance_service is not None

    def set_finance_service(self, service: FinanceService) -> None:
        """Set the finance service (for dependency injection)."""
        self._finance_service = service
        self._service_initialized = True

    def get_input_schema(self) -> dict[str, Any]:
        return MARKET_MOVERS_INPUT_SCHEMA

    def get_output_schema(self) -> dict[str, Any] | None:
        return MARKET_MOVERS_OUTPUT_SCHEMA

    async def execute(self, arguments: dict[str, Any]) -> Any:
        """Execute market movers lookup."""
        if not self._service_initialized or self._finance_service is None:
            raise FinanceServiceError("Finance service not initialized. Set finance_service before executing.")

        movers_type = arguments.get("type", "gainers")
        market = arguments.get("market", "US")
        limit = arguments.get("limit", 10)
        sector = arguments.get("sector")

        logger.info(f"Fetching {movers_type} for {market} market (limit: {limit})")

        try:
            # Call finance service to get market movers
            result = await self._finance_service.get_market_movers(
                movers_type=movers_type,
                market=market,
                limit=limit,
                sector=sector,
            )
            return result

        except FinanceServiceError as e:
            logger.error(f"Finance service error getting market movers: {e}")
            raise
        except Exception as e:
            logger.error(f"Unexpected error getting market movers: {e}")
            raise MarketMoversError(market, movers_type, f"Unexpected error: {e}") from e

    async def execute_async(self, arguments: dict[str, Any]) -> Any:
        return await self.execute(arguments)