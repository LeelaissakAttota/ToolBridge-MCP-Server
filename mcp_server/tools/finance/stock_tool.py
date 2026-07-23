"""Stock Price Tool - Get current stock prices and company information using Finance Service."""

from __future__ import annotations

import logging
from typing import Any

from mcp_server.tools.base import BaseTool
from mcp_server.tools.finance.schemas import STOCK_PRICE_INPUT_SCHEMA, STOCK_PRICE_OUTPUT_SCHEMA
from mcp_server.services.finance import FinanceService, SymbolNotFoundError, MarketClosedError, FinanceServiceError

logger = logging.getLogger(__name__)


class StockPriceTool(BaseTool):
    """Tool for retrieving current stock prices and company information.

    Supports multiple markets:
    - US (NYSE, NASDAQ)
    - Indian (NSE, BSE)
    - European (XETRA, LSE, Euronext)
    - Other major global markets

    Uses Finance Service with automatic provider failover.
    """

    name = "stock_price"
    description = "Get current stock price, company information, and market data for any publicly traded stock"
    tags = ["finance", "stocks", "market-data"]
    version = "1.0.0"
    author = "ToolBridge"

    def __init__(self, finance_service: FinanceService | None = None, config: dict[str, Any] | None = None):
        super().__init__(config)
        self._finance_service = finance_service
        self._service_initialized = finance_service is not None

    def set_finance_service(self, service: FinanceService) -> None:
        """Set the finance service (for dependency injection)."""
        self._finance_service = service
        self._service_initialized = True

    def get_input_schema(self) -> dict[str, Any]:
        return STOCK_PRICE_INPUT_SCHEMA

    def get_output_schema(self) -> dict[str, Any] | None:
        return STOCK_PRICE_OUTPUT_SCHEMA

    async def execute(self, arguments: dict[str, Any]) -> Any:
        """Execute stock price lookup."""
        if not self._service_initialized or self._finance_service is None:
            raise FinanceServiceError("Finance service not initialized. Set finance_service before executing.")

        symbol = arguments["symbol"].upper()
        market = arguments.get("market", "AUTO")

        logger.info(f"Fetching stock quote for {symbol} (market: {market})")

        try:
            quote = await self._finance_service.get_stock_quote(symbol)

            # Add market info if available
            if market != "AUTO":
                quote["requested_market"] = market

            # Include provider info
            quote["provider"] = quote.get("source", "unknown")

            return quote

        except SymbolNotFoundError:
            logger.warning(f"Stock not found: {symbol}")
            raise
        except MarketClosedError as e:
            logger.warning(f"Market closed for {symbol}: {e}")
            raise
        except FinanceServiceError as e:
            logger.error(f"Finance service error for {symbol}: {e}")
            raise
        except Exception as e:
            logger.error(f"Unexpected error getting stock quote for {symbol}: {e}")
            raise FinanceServiceError(f"Failed to get stock quote: {e}") from e

    async def execute_async(self, arguments: dict[str, Any]) -> Any:
        return await self.execute(arguments)