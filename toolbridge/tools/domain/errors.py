"""Safe errors used by stock data adapters and the MCP tool boundary."""

from toolbridge.core.contracts import ErrorCode
from toolbridge.core.errors import ToolBridgeError
from toolbridge.tools.domain.models import StockErrorCategory, StockProviderName


class StockDataError(Exception):
    """Normalized provider failure that never includes upstream payloads."""

    def __init__(
        self,
        category: StockErrorCategory,
        provider: StockProviderName,
        *,
        retryable: bool,
    ) -> None:
        super().__init__(f"{provider.value} stock data request failed: {category.value}")
        self.category = category
        self.provider = provider
        self.retryable = retryable


class InvalidStockSymbolError(ToolBridgeError):
    """Safe MCP error returned when no provider recognizes a symbol."""

    def __init__(self, symbol: str) -> None:
        super().__init__(
            ErrorCode.INVALID_SYMBOL,
            "The stock symbol is invalid or unavailable.",
            details={"symbol": symbol},
        )


class StockDataUnavailableError(ToolBridgeError):
    """Safe MCP error returned after bounded retries and failover."""

    def __init__(self, category: StockErrorCategory | None) -> None:
        details = {"error_category": category.value} if category is not None else {}
        super().__init__(
            ErrorCode.DATA_SOURCE_UNAVAILABLE,
            "Stock price data is temporarily unavailable.",
            retryable=True,
            details=details,
        )
