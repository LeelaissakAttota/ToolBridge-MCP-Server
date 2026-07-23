"""Advanced Exceptions for Finance Tools.

Provides specific exception classes for each advanced finance tool.
"""

from __future__ import annotations

from mcp_server.mcp_core.errors import ToolExecutionError


class FinanceToolError(ToolExecutionError):
    """Base exception for finance tools."""

    def __init__(self, tool_name: str, message: str, data: dict | None = None):
        super().__init__(tool_name, message, data)


class HistoricalPriceError(FinanceToolError):
    """Error fetching historical prices."""

    def __init__(self, symbol: str, message: str, data: dict | None = None):
        super().__init__(
            "historical_price",
            f"Failed to get historical prices for {symbol}: {message}",
            data={**data, "symbol": symbol} if data else {"symbol": symbol},
        )
        self.symbol = symbol


class InsufficientDataError(FinanceToolError):
    """Insufficient data for calculation."""

    def __init__(self, symbol: str, indicator: str, required: int, available: int):
        super().__init__(
            "technical_indicators",
            f"Insufficient data for {indicator} on {symbol}: need {required}, have {available}",
            data={"symbol": symbol, "indicator": indicator, "required": required, "available": available},
        )
        self.symbol = symbol
        self.indicator = indicator
        self.required = required
        self.available = available


class TechnicalIndicatorsError(FinanceToolError):
    """Error calculating technical indicators."""

    def __init__(self, symbol: str, indicator: str, message: str, data: dict | None = None):
        super().__init__(
            "technical_indicators",
            f"Failed to calculate {indicator} for {symbol}: {message}",
            data={**data, "symbol": symbol, "indicator": indicator} if data else {"symbol": symbol, "indicator": indicator},
        )
        self.symbol = symbol
        self.indicator = indicator


class CompanyInfoError(FinanceToolError):
    """Error fetching company information."""

    def __init__(self, symbol: str, message: str, data: dict | None = None):
        super().__init__(
            "company_info",
            f"Failed to get company info for {symbol}: {message}",
            data={**data, "symbol": symbol} if data else {"symbol": symbol},
        )
        self.symbol = symbol


class MarketMoversError(FinanceToolError):
    """Error fetching market movers."""

    def __init__(self, market: str, movers_type: str, message: str, data: dict | None = None):
        super().__init__(
            "market_movers",
            f"Failed to get {movers_type} for {market}: {message}",
            data={**data, "market": market, "type": movers_type} if data else {"market": market, "type": movers_type},
        )
        self.market = market
        self.movers_type = movers_type


class FinancialNewsError(FinanceToolError):
    """Error fetching financial news."""

    def __init__(self, message: str, data: dict | None = None):
        super().__init__(
            "financial_news",
            f"Failed to get financial news: {message}",
            data=data,
        )


class NewsSentimentError(FinanceToolError):
    """Error analyzing news sentiment."""

    def __init__(self, symbols: list[str], message: str, data: dict | None = None):
        super().__init__(
            "news_sentiment",
            f"Failed to analyze sentiment for {symbols}: {message}",
            data={**data, "symbols": symbols} if data else {"symbols": symbols},
        )
        self.symbols = symbols


class FinancialAnalysisError(FinanceToolError):
    """Error generating financial analysis."""

    def __init__(self, symbol: str, message: str, data: dict | None = None):
        super().__init__(
            "financial_analysis",
            f"Failed to generate analysis for {symbol}: {message}",
            data={**data, "symbol": symbol} if data else {"symbol": symbol},
        )
        self.symbol = symbol


class LLMProviderError(FinanceToolError):
    """Error from LLM provider."""

    def __init__(self, provider: str, message: str, data: dict | None = None):
        super().__init__(
            "llm_provider",
            f"LLM provider {provider} error: {message}",
            data={**data, "provider": provider} if data else {"provider": provider},
        )
        self.provider = provider


class RateLimitError(FinanceToolError):
    """Rate limit exceeded."""

    def __init__(self, provider: str, retry_after: int | None = None):
        data = {"provider": provider}
        if retry_after:
            data["retry_after_seconds"] = retry_after
        super().__init__(
            "rate_limit",
            f"Rate limit exceeded for {provider}",
            data=data,
        )
        self.provider = provider
        self.retry_after = retry_after