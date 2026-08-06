"""Outbound adapters for stock market data sources."""

from toolbridge.tools.adapters.alpha_vantage import AlphaVantageStockProvider
from toolbridge.tools.adapters.yahoo_finance import YahooFinanceStockProvider

__all__ = ["AlphaVantageStockProvider", "YahooFinanceStockProvider"]
