"""Historical Price Tool - Get historical price data for stocks."""

from __future__ import annotations

import logging
from typing import Any, Optional

from mcp_server.tools.base import BaseTool
from mcp_server.tools.finance.advanced_schemas import (
    HISTORICAL_PRICE_INPUT_SCHEMA,
    HISTORICAL_PRICE_OUTPUT_SCHEMA,
)
from mcp_server.tools.finance.advanced_exceptions import HistoricalPriceError
from mcp_server.services.finance import FinanceService, SymbolNotFoundError, FinanceServiceError

logger = logging.getLogger(__name__)


class HistoricalPriceTool(BaseTool):
    """Tool for retrieving historical price data for stocks.

    Supports multiple timeframes and intervals:
    - Daily, weekly, monthly prices
    - Custom date ranges
    - OHLC data with adjusted close
    - Volume data
    - Dividends and splits (optional)

    Uses Finance Service with automatic provider failover.
    """

    name = "historical_price"
    description = "Get historical price data for any publicly traded stock with multiple timeframes and intervals"
    tags = ["finance", "stocks", "historical-data", "market-data"]
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
        return HISTORICAL_PRICE_INPUT_SCHEMA

    def get_output_schema(self) -> dict[str, Any] | None:
        return HISTORICAL_PRICE_OUTPUT_SCHEMA

    async def execute(self, arguments: dict[str, Any]) -> Any:
        """Execute historical price lookup."""
        if not self._service_initialized or self._finance_service is None:
            raise FinanceServiceError("Finance service not initialized. Set finance_service before executing.")

        symbol = arguments["symbol"].upper()
        period = arguments.get("period", "1mo")
        interval = arguments.get("interval", "1d")
        start_date = arguments.get("start_date")
        end_date = arguments.get("end_date")
        include_adjusted_close = arguments.get("include_adjusted_close", True)
        include_dividends = arguments.get("include_dividends", False)
        include_splits = arguments.get("include_splits", False)

        logger.info(f"Fetching historical data for {symbol} (period: {period}, interval: {interval})")

        try:
            # Call the finance service to get historical data
            result = await self._finance_service.get_historical_prices(
                symbol=symbol,
                period=period,
                interval=interval,
                start_date=start_date,
                end_date=end_date,
                include_adjusted_close=include_adjusted_close,
                include_dividends=include_dividends,
                include_splits=include_splits,
            )
            return result

        except SymbolNotFoundError:
            logger.warning(f"Symbol not found: {symbol}")
            raise
        except FinanceServiceError as e:
            logger.error(f"Finance service error for {symbol}: {e}")
            raise
        except Exception as e:
            logger.error(f"Unexpected error getting historical data for {symbol}: {e}")
            raise HistoricalPriceError(symbol, f"Unexpected error: {e}") from e

    async def execute_async(self, arguments: dict[str, Any]) -> Any:
        return await self.execute(arguments)