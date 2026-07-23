"""Exceptions for finance tools."""

from mcp_server.mcp_core.errors import ToolExecutionError


class FinanceToolError(ToolExecutionError):
    """Base exception for finance tools."""

    def __init__(self, tool_name: str, message: str, data: dict | None = None):
        super().__init__(tool_name, message, data)


class StockPriceError(FinanceToolError):
    """Error fetching stock price."""

    def __init__(self, symbol: str, message: str, data: dict | None = None):
        super().__init__(
            "stock_price",
            f"Failed to get price for {symbol}: {message}",
            data={**data, "symbol": symbol} if data else {"symbol": symbol},
        )
        self.symbol = symbol


class StockNotFoundError(StockPriceError):
    """Stock symbol not found."""

    def __init__(self, symbol: str):
        super().__init__(symbol, "Stock symbol not found or invalid")


class StockDataProviderError(StockPriceError):
    """Error from stock data provider."""

    def __init__(self, symbol: str, provider: str, message: str):
        super().__init__(symbol, f"Provider {provider} error: {message}", data={"provider": provider})


class CurrencyExchangeError(FinanceToolError):
    """Error during currency exchange."""

    def __init__(self, from_currency: str, to_currency: str, message: str, data: dict | None = None):
        super().__init__(
            "currency_exchange",
            f"Failed to convert {from_currency} to {to_currency}: {message}",
            data={**data, "from_currency": from_currency, "to_currency": to_currency} if data else {
                "from_currency": from_currency,
                "to_currency": to_currency,
            },
        )
        self.from_currency = from_currency
        self.to_currency = to_currency


class InvalidCurrencyError(CurrencyExchangeError):
    """Invalid currency code."""

    def __init__(self, currency: str):
        super().__init__(
            currency,
            "N/A",
            f"Invalid currency code: {currency}. Must be 3-letter ISO 4217 code.",
        )
        self.currency = currency


class CurrencyProviderError(CurrencyExchangeError):
    """Error from currency data provider."""

    def __init__(self, from_currency: str, to_currency: str, provider: str, message: str):
        super().__init__(
            from_currency,
            to_currency,
            f"Provider {provider} error: {message}",
            data={"provider": provider},
        )


class MarketClosedError(StockPriceError):
    """Market is closed, no real-time data available."""

    def __init__(self, symbol: str, market: str):
        super().__init__(
            symbol,
            f"Market {market} is closed, no real-time data available",
            data={"market": market, "market_closed": True},
        )


class RateLimitError(FinanceToolError):
    """Rate limit exceeded."""

    def __init__(self, tool_name: str, retry_after: int | None = None):
        data = {"rate_limited": True}
        if retry_after:
            data["retry_after_seconds"] = retry_after
        super().__init__(
            tool_name,
            "Rate limit exceeded, please try again later",
            data=data,
        )