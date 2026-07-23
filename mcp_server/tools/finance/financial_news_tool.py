"""Financial News Tool - Get financial news for companies and markets."""

from __future__ import annotations

import logging
from typing import Any, Optional

from mcp_server.tools.base import BaseTool
from mcp_server.tools.finance.advanced_schemas import (
    FINANCIAL_NEWS_INPUT_SCHEMA,
    FINANCIAL_NEWS_OUTPUT_SCHEMA,
)
from mcp_server.tools.finance.advanced_exceptions import FinancialNewsError
from mcp_server.services.finance import FinanceService, FinanceServiceError

logger = logging.getLogger(__name__)


class FinancialNewsTool(BaseTool):
    """Tool for retrieving financial news.

    Provides:
    - Company-specific news
    - Market news
    - Sector news
    - Breaking news
    - Filter by symbol, category, country, date range

    Uses Finance Service with automatic provider failover.
    """

    name = "financial_news"
    description = "Get financial news for companies, sectors, or markets with filtering by category, country, and date range"
    tags = ["finance", "news", "market-news", "company-news"]
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
        return FINANCIAL_NEWS_INPUT_SCHEMA

    def get_output_schema(self) -> dict[str, Any] | None:
        return FINANCIAL_NEWS_OUTPUT_SCHEMA

    async def execute(self, arguments: dict[str, Any]) -> Any:
        """Execute financial news lookup."""
        if not self._service_initialized or self._finance_service is None:
            raise FinanceServiceError("Finance service not initialized. Set finance_service before executing.")

        symbols = arguments.get("symbols", [])
        category = arguments.get("category")
        country = arguments.get("country")
        limit = arguments.get("limit", 20)
        start_date = arguments.get("start_date")
        end_date = arguments.get("end_date")

        logger.info(f"Fetching financial news (symbols: {symbols}, category: {category}, country: {country})")

        try:
            # Call finance service to get financial news
            result = await self._finance_service.get_financial_news(
                symbols=symbols if symbols else None,
                category=category,
                country=country,
                limit=limit,
                start_date=start_date,
                end_date=end_date,
            )
            
            # Apply limit as fallback if service doesn't
            if "articles" in result and len(result["articles"]) > limit:
                result["articles"] = result["articles"][:limit]
            
            return result

        except FinanceServiceError as e:
            logger.error(f"Finance service error getting financial news: {e}")
            raise
        except Exception as e:
            logger.error(f"Unexpected error getting financial news: {e}")
            raise FinancialNewsError(f"Unexpected error: {e}") from e

    async def execute_async(self, arguments: dict[str, Any]) -> Any:
        return await self.execute(arguments)