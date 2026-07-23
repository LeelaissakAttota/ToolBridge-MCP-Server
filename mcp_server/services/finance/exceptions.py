"""Exceptions for finance services."""

from __future__ import annotations


class FinanceServiceError(Exception):
    """Base exception for finance services."""

    def __init__(self, message: str, provider: str | None = None, data: dict | None = None):
        super().__init__(message)
        self.provider = provider
        self.data = data or {}


class ProviderError(FinanceServiceError):
    """Error from a data provider."""

    def __init__(self, message: str, provider: str, data: dict | None = None):
        super().__init__(message, provider, data)


class ProviderUnavailableError(ProviderError):
    """Provider is unavailable or unhealthy."""

    def __init__(self, provider: str, reason: str = "Provider unavailable"):
        super().__init__(reason, provider)


class RateLimitError(ProviderError):
    """Rate limit exceeded."""

    def __init__(self, provider: str, retry_after: int | None = None):
        data = {"retry_after": retry_after} if retry_after else {}
        super().__init__("Rate limit exceeded", provider, data)


class SymbolNotFoundError(FinanceServiceError):
    """Symbol not found."""

    def __init__(self, symbol: str, provider: str | None = None):
        super().__init__(f"Symbol not found: {symbol}", provider, {"symbol": symbol})


class InvalidSymbolError(FinanceServiceError):
    """Invalid symbol format."""

    def __init__(self, symbol: str):
        super().__init__(f"Invalid symbol format: {symbol}", data={"symbol": symbol})


class CurrencyError(FinanceServiceError):
    """Currency conversion error."""

    def __init__(self, message: str, from_currency: str | None = None, to_currency: str | None = None, provider: str | None = None):
        super().__init__(message, provider)
        self.from_currency = from_currency
        self.to_currency = to_currency


class InvalidCurrencyError(CurrencyError):
    """Invalid currency code."""

    def __init__(self, currency: str):
        super().__init__(f"Invalid currency code: {currency}", data={"currency": currency})


class MarketClosedError(FinanceServiceError):
    """Market is closed."""

    def __init__(self, symbol: str, market: str):
        super().__init__(f"Market {market} is closed for {symbol}", data={"symbol": symbol, "market": market})


class CacheError(FinanceServiceError):
    """Cache operation error."""

    def __init__(self, operation: str, message: str):
        super().__init__(f"Cache {operation} failed: {message}", data={"operation": operation})


class ConfigurationError(FinanceServiceError):
    """Configuration error."""

    def __init__(self, message: str):
        super().__init__(f"Configuration error: {message}")