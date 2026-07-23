"""Finance tools package for ToolBridge MCP Server.

Provides stock price and currency exchange tools with automatic provider failover.
"""

from mcp_server.tools.finance.stock_tool import StockPriceTool
from mcp_server.tools.finance.currency_tool import CurrencyExchangeTool, SupportedCurrenciesTool
from mcp_server.tools.finance.schemas import (
    STOCK_PRICE_INPUT_SCHEMA,
    STOCK_PRICE_OUTPUT_SCHEMA,
    CURRENCY_EXCHANGE_INPUT_SCHEMA,
    CURRENCY_EXCHANGE_OUTPUT_SCHEMA,
    SUPPORTED_CURRENCIES_INPUT_SCHEMA,
    SUPPORTED_CURRENCIES_OUTPUT_SCHEMA,
)
from mcp_server.tools.finance.exceptions import (
    FinanceToolError,
    StockPriceError,
    StockNotFoundError,
    StockDataProviderError,
    MarketClosedError,
    CurrencyExchangeError,
    InvalidCurrencyError,
    CurrencyProviderError,
    RateLimitError,
)

__all__ = [
    "StockPriceTool",
    "CurrencyExchangeTool",
    "SupportedCurrenciesTool",
    "STOCK_PRICE_INPUT_SCHEMA",
    "STOCK_PRICE_OUTPUT_SCHEMA",
    "CURRENCY_EXCHANGE_INPUT_SCHEMA",
    "CURRENCY_EXCHANGE_OUTPUT_SCHEMA",
    "SUPPORTED_CURRENCIES_INPUT_SCHEMA",
    "SUPPORTED_CURRENCIES_OUTPUT_SCHEMA",
    "FinanceToolError",
    "StockPriceError",
    "StockNotFoundError",
    "StockDataProviderError",
    "MarketClosedError",
    "CurrencyExchangeError",
    "InvalidCurrencyError",
    "CurrencyProviderError",
    "RateLimitError",
]