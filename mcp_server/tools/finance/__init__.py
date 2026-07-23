"""Finance tools package for ToolBridge MCP Server.

Provides stock price and currency exchange tools with automatic provider failover.
"""

from mcp_server.tools.finance.stock_tool import StockPriceTool
from mcp_server.tools.finance.currency_tool import CurrencyExchangeTool, SupportedCurrenciesTool
from mcp_server.tools.finance.historical_price_tool import HistoricalPriceTool
from mcp_server.tools.finance.company_info_tool import CompanyInfoTool
from mcp_server.tools.finance.market_movers_tool import MarketMoversTool
from mcp_server.tools.finance.technical_indicators_tool import TechnicalIndicatorsTool
from mcp_server.tools.finance.financial_news_tool import FinancialNewsTool
from mcp_server.tools.finance.news_sentiment_tool import NewsSentimentTool
from mcp_server.tools.finance.financial_analysis_tool import FinancialAnalysisTool
from mcp_server.tools.finance.schemas import (
    STOCK_PRICE_INPUT_SCHEMA,
    STOCK_PRICE_OUTPUT_SCHEMA,
    CURRENCY_EXCHANGE_INPUT_SCHEMA,
    CURRENCY_EXCHANGE_OUTPUT_SCHEMA,
    SUPPORTED_CURRENCIES_INPUT_SCHEMA,
    SUPPORTED_CURRENCIES_OUTPUT_SCHEMA,
)
from mcp_server.tools.finance.advanced_schemas import (
    HISTORICAL_PRICE_INPUT_SCHEMA,
    HISTORICAL_PRICE_OUTPUT_SCHEMA,
    COMPANY_INFO_INPUT_SCHEMA,
    COMPANY_INFO_OUTPUT_SCHEMA,
    MARKET_MOVERS_INPUT_SCHEMA,
    MARKET_MOVERS_OUTPUT_SCHEMA,
    TECHNICAL_INDICATORS_INPUT_SCHEMA,
    TECHNICAL_INDICATORS_OUTPUT_SCHEMA,
    FINANCIAL_NEWS_INPUT_SCHEMA,
    FINANCIAL_NEWS_OUTPUT_SCHEMA,
    NEWS_SENTIMENT_INPUT_SCHEMA,
    NEWS_SENTIMENT_OUTPUT_SCHEMA,
    FINANCIAL_ANALYSIS_INPUT_SCHEMA,
    FINANCIAL_ANALYSIS_OUTPUT_SCHEMA,
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
from mcp_server.tools.finance.advanced_exceptions import (
    FinanceToolError,
    HistoricalPriceError,
    CompanyInfoError,
    MarketMoversError,
    TechnicalIndicatorsError,
    FinancialNewsError,
    NewsSentimentError,
    FinancialAnalysisError,
    InsufficientDataError,
    LLMProviderError,
    RateLimitError,
)

__all__ = [
    # Basic tools
    "StockPriceTool",
    "CurrencyExchangeTool",
    "SupportedCurrenciesTool",
    # Advanced tools
    "HistoricalPriceTool",
    "CompanyInfoTool",
    "MarketMoversTool",
    "TechnicalIndicatorsTool",
    "FinancialNewsTool",
    "NewsSentimentTool",
    "FinancialAnalysisTool",
    # Basic schemas
    "STOCK_PRICE_INPUT_SCHEMA",
    "STOCK_PRICE_OUTPUT_SCHEMA",
    "CURRENCY_EXCHANGE_INPUT_SCHEMA",
    "CURRENCY_EXCHANGE_OUTPUT_SCHEMA",
    "SUPPORTED_CURRENCIES_INPUT_SCHEMA",
    "SUPPORTED_CURRENCIES_OUTPUT_SCHEMA",
    # Advanced schemas
    "HISTORICAL_PRICE_INPUT_SCHEMA",
    "HISTORICAL_PRICE_OUTPUT_SCHEMA",
    "COMPANY_INFO_INPUT_SCHEMA",
    "COMPANY_INFO_OUTPUT_SCHEMA",
    "MARKET_MOVERS_INPUT_SCHEMA",
    "MARKET_MOVERS_OUTPUT_SCHEMA",
    "TECHNICAL_INDICATORS_INPUT_SCHEMA",
    "TECHNICAL_INDICATORS_OUTPUT_SCHEMA",
    "FINANCIAL_NEWS_INPUT_SCHEMA",
    "FINANCIAL_NEWS_OUTPUT_SCHEMA",
    "NEWS_SENTIMENT_INPUT_SCHEMA",
    "NEWS_SENTIMENT_OUTPUT_SCHEMA",
    "FINANCIAL_ANALYSIS_INPUT_SCHEMA",
    "FINANCIAL_ANALYSIS_OUTPUT_SCHEMA",
    # Basic exceptions
    "FinanceToolError",
    "StockPriceError",
    "StockNotFoundError",
    "StockDataProviderError",
    "MarketClosedError",
    "CurrencyExchangeError",
    "InvalidCurrencyError",
    "CurrencyProviderError",
    "RateLimitError",
    # Advanced exceptions
    "FinanceToolError",
    "HistoricalPriceError",
    "CompanyInfoError",
    "MarketMoversError",
    "TechnicalIndicatorsError",
    "FinancialNewsError",
    "NewsSentimentError",
    "FinancialAnalysisError",
    "InsufficientDataError",
    "LLMProviderError",
    "RateLimitError",
]