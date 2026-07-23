"""Currency Exchange Tool - Convert currencies and get exchange rates using Currency Service."""

from __future__ import annotations

import logging
from typing import Any

from mcp_server.tools.base import BaseTool
from mcp_server.tools.finance.schemas import (
    CURRENCY_EXCHANGE_INPUT_SCHEMA,
    CURRENCY_EXCHANGE_OUTPUT_SCHEMA,
    SUPPORTED_CURRENCIES_INPUT_SCHEMA,
    SUPPORTED_CURRENCIES_OUTPUT_SCHEMA,
)
from mcp_server.services.finance import CurrencyService, InvalidCurrencyError, CurrencyError

logger = logging.getLogger(__name__)


class CurrencyExchangeTool(BaseTool):
    """Tool for currency conversion and exchange rate lookup.

    Supports 160+ currencies via multiple providers:
    - Frankfurter (ECB) - Primary
    - ExchangeRate-API - Fallback
    - CurrencyLayer - Optional (requires API key)

    Features:
    - Real-time exchange rates
    - Historical rates (optional)
    - Currency conversion
    - Supported currencies listing
    - Automatic provider failover
    """

    name = "currency_exchange"
    description = "Convert currencies and get latest/historical exchange rates"
    tags = ["finance", "currency", "forex", "conversion"]
    version = "1.0.0"
    author = "ToolBridge"

    def __init__(self, currency_service: CurrencyService | None = None, config: dict[str, Any] | None = None):
        super().__init__(config)
        self._currency_service = currency_service
        self._service_initialized = currency_service is not None

    def set_currency_service(self, service: CurrencyService) -> None:
        """Set the currency service (for dependency injection)."""
        self._currency_service = service
        self._service_initialized = True

    def get_input_schema(self) -> dict[str, Any]:
        return CURRENCY_EXCHANGE_INPUT_SCHEMA

    def get_output_schema(self) -> dict[str, Any] | None:
        return CURRENCY_EXCHANGE_OUTPUT_SCHEMA

    async def execute(self, arguments: dict[str, Any]) -> Any:
        """Execute currency conversion."""
        if not self._service_initialized or self._currency_service is None:
            raise CurrencyError("Currency service not initialized. Set currency_service before executing.")

        from_currency = arguments["from_currency"].upper()
        to_currency = arguments["to_currency"].upper()
        amount = float(arguments.get("amount", 1.0))
        date = arguments.get("date", "latest")
        include_supported = arguments.get("include_supported", False)

        logger.info(f"Converting {amount} {from_currency} to {to_currency} (date: {date})")

        try:
            result = await self._currency_service.convert_currency(
                from_currency=from_currency,
                to_currency=to_currency,
                amount=amount,
                date=date,
            )

            if include_supported:
                currencies = await self._currency_service.get_supported_currencies()
                result["supported_currencies"] = [c["code"] for c in currencies]

            return result

        except InvalidCurrencyError as e:
            logger.warning(f"Invalid currency: {e}")
            raise
        except CurrencyError as e:
            logger.error(f"Currency service error: {e}")
            raise
        except Exception as e:
            logger.error(f"Unexpected error converting currency: {e}")
            raise CurrencyError(f"Failed to convert currency: {e}") from e

    async def execute_async(self, arguments: dict[str, Any]) -> Any:
        return await self.execute(arguments)


class SupportedCurrenciesTool(BaseTool):
    """Tool to list all supported currencies."""

    name = "supported_currencies"
    description = "Get list of all supported currency codes with names and symbols"
    tags = ["finance", "currency", "reference"]
    version = "1.0.0"
    author = "ToolBridge"

    def __init__(self, currency_service: CurrencyService | None = None, config: dict[str, Any] | None = None):
        super().__init__(config)
        self._currency_service = currency_service
        self._service_initialized = currency_service is not None

    def set_currency_service(self, service: CurrencyService) -> None:
        self._currency_service = service
        self._service_initialized = True

    def get_input_schema(self) -> dict[str, Any]:
        return SUPPORTED_CURRENCIES_INPUT_SCHEMA

    def get_output_schema(self) -> dict[str, Any] | None:
        return SUPPORTED_CURRENCIES_OUTPUT_SCHEMA

    async def execute(self, arguments: dict[str, Any]) -> Any:
        """Execute currency listing."""
        if not self._service_initialized or self._currency_service is None:
            raise CurrencyError("Currency service not initialized.")

        logger.info("Fetching supported currencies")

        try:
            currencies = await self._currency_service.get_supported_currencies()
            return {"currencies": currencies, "count": len(currencies)}
        except Exception as e:
            logger.error(f"Error getting supported currencies: {e}")
            raise CurrencyError(f"Failed to get supported currencies: {e}") from e

    async def execute_async(self, arguments: dict[str, Any]) -> Any:
        return await self.execute(arguments)