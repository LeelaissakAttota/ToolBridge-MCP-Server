"""Company Information Tool - Get comprehensive company profiles."""

from __future__ import annotations

import logging
from typing import Any, Optional

from mcp_server.tools.base import BaseTool
from mcp_server.tools.finance.advanced_schemas import (
    COMPANY_INFO_INPUT_SCHEMA,
    COMPANY_INFO_OUTPUT_SCHEMA,
)
from mcp_server.tools.finance.advanced_exceptions import CompanyInfoError
from mcp_server.services.finance import FinanceService, SymbolNotFoundError, FinanceServiceError

logger = logging.getLogger(__name__)


class CompanyInfoTool(BaseTool):
    """Tool for retrieving comprehensive company information.

    Provides detailed company profiles including:
    - Company profile (name, description, sector, industry)
    - Leadership (CEO, executives)
    - Financial metrics (market cap, P/E, EPS, beta)
    - Dividend information
    - Key statistics
    - Corporate actions

    Uses Finance Service with automatic provider failover.
    """

    name = "company_info"
    description = "Get comprehensive company information including profile, financials, leadership, and key metrics"
    tags = ["finance", "stocks", "company-profile", "fundamentals"]
    version = "1.0.0"
    author = "ToolBridge"

    def __init__(self, finance_service: Optional[Any] = None, config: dict[str, Any] | None = None):
        super().__init__(config)
        self._finance_service: Optional[FinanceService] = finance_service
        self._service_initialized = finance_service is not None

    def set_finance_service(self, service: FinanceService) -> None:
        """Set the finance service (for dependency injection)."""
        self._finance_service = finance_service
        self._service_initialized = True

    def get_input_schema(self) -> dict[str, Any]:
        return COMPANY_INFO_INPUT_SCHEMA

    def get_output_schema(self) -> dict[str, Any] | None:
        return COMPANY_INFO_OUTPUT_SCHEMA

    async def execute(self, arguments: dict[str, Any]) -> Any:
        """Execute company info lookup."""
        if not self._service_initialized or self._finance_service is None:
            raise FinanceServiceError("Finance service not initialized. Set finance_service before executing.")

        symbol = arguments["symbol"].upper()
        include_financials = arguments.get("include_financials", True)
        include_leadership = arguments.get("include_leadership", True)
        include_statistics = arguments.get("include_statistics", True)

        logger.info(f"Fetching company info for {symbol}")

        try:
            # Call finance service to get company info
            result = await self._finance_service.get_company_info(
                symbol=symbol,
                include_financials=include_financials,
                include_leadership=include_leadership,
                include_statistics=include_statistics,
            )
            return result

        except SymbolNotFoundError:
            logger.warning(f"Symbol not found: {symbol}")
            raise
        except FinanceServiceError as e:
            logger.error(f"Finance service error for {symbol}: {e}")
            raise
        except Exception as e:
            logger.error(f"Unexpected error getting company info for {symbol}: {e}")
            raise CompanyInfoError(symbol, f"Unexpected error: {e}") from e

    async def execute_async(self, arguments: dict[str, Any]) -> Any:
        return await self.execute(arguments)