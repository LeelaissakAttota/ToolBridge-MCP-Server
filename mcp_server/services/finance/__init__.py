"""Finance services package for ToolBridge MCP Server.

Provides production-ready financial market data services with:
- Multiple stock price providers with automatic failover
- Multiple currency exchange providers with automatic failover
- Health monitoring, caching, and metrics
"""

from mcp_server.services.finance.exceptions import (
    FinanceServiceError,
    ProviderError,
    ProviderUnavailableError,
    RateLimitError,
    SymbolNotFoundError,
    InvalidSymbolError,
    CurrencyError,
    InvalidCurrencyError,
    MarketClosedError,
    CacheError,
    ConfigurationError,
)
from mcp_server.services.finance.finance_provider import (
    BaseFinanceProvider,
    ProviderMetrics,
    ProviderHealth,
)
from mcp_server.services.finance.provider_router import (
    ProviderRouter,
    ProviderConfig,
    FailoverConfig,
)
from mcp_server.services.finance.finance_service import FinanceService
from mcp_server.services.finance.currency_service import CurrencyService
from mcp_server.services.finance.health_monitor import HealthMonitor, HealthCheckResult
from mcp_server.services.finance.metrics import MetricsCollector, ServiceMetrics, ProviderMetrics, metrics_collector
from mcp_server.services.finance.cache import FinanceCache, CacheEntry, StockPriceCache, ExchangeRateCache, CurrencyListCache

__all__ = [
    # Exceptions
    "FinanceServiceError",
    "ProviderError",
    "ProviderUnavailableError",
    "RateLimitError",
    "SymbolNotFoundError",
    "InvalidSymbolError",
    "CurrencyError",
    "InvalidCurrencyError",
    "MarketClosedError",
    "CacheError",
    "ConfigurationError",
    # Base classes
    "BaseFinanceProvider",
    "ProviderMetrics",
    "ProviderHealth",
    # Router
    "ProviderRouter",
    "ProviderConfig",
    "FailoverConfig",
    # Services
    "FinanceService",
    "CurrencyService",
    # Monitoring
    "HealthMonitor",
    "HealthCheckResult",
    # Metrics
    "MetricsCollector",
    "ServiceMetrics",
    "ProviderMetrics",
    "metrics_collector",
    # Cache
    "FinanceCache",
    "CacheEntry",
    "StockPriceCache",
    "ExchangeRateCache",
    "CurrencyListCache",
]