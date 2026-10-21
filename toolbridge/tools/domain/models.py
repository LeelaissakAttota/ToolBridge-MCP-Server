"""Provider-neutral models for the tool framework and stock quotes."""

from datetime import datetime
from enum import StrEnum
from math import isfinite

from pydantic import BaseModel, ConfigDict, Field, field_validator

from toolbridge.core.contracts import ToolInput, ToolOutput


class ToolHealthState(StrEnum):
    """Lifecycle and availability states shared by all managed tools."""

    UNINITIALIZED = "uninitialized"
    HEALTHY = "healthy"
    DEGRADED = "degraded"
    UNAVAILABLE = "unavailable"
    CLOSED = "closed"


class StockProviderName(StrEnum):
    """Supported stock data source identifiers."""

    YAHOO_FINANCE = "yahoo_finance"
    ALPHA_VANTAGE = "alpha_vantage"


class MarketStatus(StrEnum):
    """Normalized market-session states."""

    PRE_MARKET = "pre_market"
    OPEN = "open"
    POST_MARKET = "post_market"
    CLOSED = "closed"
    UNKNOWN = "unknown"


class StockErrorCategory(StrEnum):
    """Normalized stock provider failure categories."""

    INVALID_SYMBOL = "invalid_symbol"
    TIMEOUT = "timeout"
    NETWORK = "network"
    AUTHENTICATION = "authentication"
    RATE_LIMIT = "rate_limit"
    UNAVAILABLE = "unavailable"
    INVALID_RESPONSE = "invalid_response"


class ToolMetricsSnapshot(BaseModel):
    """Immutable aggregate execution metrics for one tool."""

    model_config = ConfigDict(extra="forbid", strict=True, frozen=True)

    tool_name: str
    total_executions: int = Field(ge=0)
    successful_executions: int = Field(ge=0)
    failed_executions: int = Field(ge=0)
    average_duration_ms: float = Field(ge=0)
    last_duration_ms: float | None = Field(default=None, ge=0)
    last_error_code: str | None = None
    last_execution_at: datetime | None = None


class ToolHealthStatus(BaseModel):
    """Safe health snapshot returned by a managed tool."""

    model_config = ConfigDict(extra="forbid", strict=True, frozen=True)

    tool_name: str
    status: ToolHealthState
    checked_at: datetime
    latency_ms: float | None = Field(default=None, ge=0)
    last_success_at: datetime | None = None
    last_failure_at: datetime | None = None
    providers: dict[str, str] = Field(default_factory=dict)


class ProviderHealthStatus(BaseModel):
    """Internal normalized health snapshot for a stock data provider."""

    model_config = ConfigDict(extra="forbid", strict=True, frozen=True)

    provider: StockProviderName
    status: ToolHealthState
    checked_at: datetime
    latency_ms: float | None = Field(default=None, ge=0)
    error_category: StockErrorCategory | None = None


class StockPriceInput(ToolInput):
    """Validated stock symbol accepted by the Stock Price Tool."""

    symbol: str = Field(
        min_length=1,
        max_length=20,
        pattern=r"^[A-Z0-9][A-Z0-9.\-]{0,19}$",
        description="Exchange ticker symbol, for example NVDA or BRK.B.",
    )

    @field_validator("symbol", mode="before")
    @classmethod
    def normalize_symbol(cls, value: object) -> object:
        """Normalize safe textual symbols before pattern validation."""

        if isinstance(value, str):
            return value.strip().upper()
        return value


class StockPriceOutput(ToolOutput):
    """Normalized stock quote returned by every data provider."""

    symbol: str = Field(min_length=1, max_length=20)
    current_price: float = Field(ge=0)
    company_name: str | None = Field(default=None, max_length=256)
    currency: str | None = Field(default=None, max_length=16)
    exchange: str | None = Field(default=None, max_length=128)
    day_high: float | None = Field(default=None, ge=0)
    day_low: float | None = Field(default=None, ge=0)
    open: float | None = Field(default=None, ge=0)
    previous_close: float | None = Field(default=None, ge=0)
    market_status: MarketStatus
    timestamp: datetime
    provider: StockProviderName
    cached: bool = False

    @field_validator(
        "current_price",
        "day_high",
        "day_low",
        "open",
        "previous_close",
    )
    @classmethod
    def require_finite_price(cls, value: float | None) -> float | None:
        """Reject non-finite market values before they reach MCP clients."""

        if value is not None and not isfinite(value):
            raise ValueError("price values must be finite")
        return value

    @field_validator("timestamp")
    @classmethod
    def require_aware_timestamp(cls, value: datetime) -> datetime:
        """Require an offset-aware market-data timestamp."""

        if value.tzinfo is None or value.utcoffset() is None:
            raise ValueError("timestamp must include a timezone")
        return value


class ToolStatusSnapshot(BaseModel):
    """Combined health and metrics for internal runtime inspection."""

    model_config = ConfigDict(extra="forbid", strict=True, frozen=True)

    health: ToolHealthStatus
    metrics: ToolMetricsSnapshot
