"""Typed application and provider configuration."""

from functools import lru_cache
from re import fullmatch

from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
    HttpUrl,
    SecretStr,
    field_validator,
    model_validator,
)
from pydantic_settings import BaseSettings, SettingsConfigDict

from toolbridge.phase5_config import Phase5ToolSettings
from toolbridge.providers.domain.models import ProviderCapabilities
from toolbridge.tools.domain.models import StockProviderName


class LLMProviderSettings(BaseModel):
    """Configuration shared by one OpenAI-compatible provider adapter."""

    model_config = ConfigDict(extra="forbid")

    enabled: bool = False
    api_key: SecretStr | None = None
    base_url: HttpUrl
    default_model: str | None = Field(default=None, max_length=256)
    timeout_seconds: float = Field(default=30.0, gt=0, le=300)
    retry_count: int = Field(default=2, ge=0, le=5)
    max_tokens: int = Field(default=1_024, ge=1, le=131_072)
    temperature: float = Field(default=0.2, ge=0, le=2)
    input_cost_per_million_tokens_usd: float = Field(default=0.0, ge=0)
    output_cost_per_million_tokens_usd: float = Field(default=0.0, ge=0)
    capabilities: ProviderCapabilities | None = None
    is_free: bool = False
    context_window: int | None = Field(default=None, ge=1)
    reasoning_quality: float = Field(default=0.5, ge=0, le=1)
    daily_budget_usd: float | None = Field(default=None, ge=0)
    monthly_budget_usd: float | None = Field(default=None, ge=0)
    per_request_budget_usd: float | None = Field(default=None, ge=0)
    budget_soft_limit_ratio: float = Field(default=0.8, ge=0, le=1)
    max_prompt_bytes: int = Field(default=131_072, ge=1_024, le=10_485_760)
    models_path: str = Field(default="/models", pattern=r"^/[A-Za-z0-9_./-]+$")
    chat_completions_path: str = Field(
        default="/chat/completions",
        pattern=r"^/[A-Za-z0-9_./-]+$",
    )

    @field_validator("base_url")
    @classmethod
    def require_https(cls, value: HttpUrl) -> HttpUrl:
        """Require TLS for every configured external provider endpoint."""

        if value.scheme != "https":
            raise ValueError("provider base_url must use HTTPS")
        return value

    @field_validator("default_model")
    @classmethod
    def normalize_model(cls, value: str | None) -> str | None:
        """Trim a configured model identifier without inventing a default."""

        if value is None:
            return None
        normalized = value.strip()
        return normalized or None

    @model_validator(mode="after")
    def validate_enabled_provider(self) -> "LLMProviderSettings":
        """Require credentials and a model only when the provider is enabled."""

        secret = self.api_key.get_secret_value() if self.api_key is not None else ""
        if self.enabled and not secret:
            raise ValueError("enabled providers require an API key")
        if self.enabled and self.default_model is None:
            raise ValueError("enabled providers require a default model")
        return self


class OpenRouterSettings(LLMProviderSettings):
    """OpenRouter settings including optional application attribution."""

    http_referer: HttpUrl | None = None
    app_title: str | None = Field(default=None, max_length=128)

    @field_validator("http_referer", mode="before")
    @classmethod
    def normalize_http_referer(cls, value: object) -> object:
        """Treat an empty optional attribution URL as unset."""

        return None if value == "" else value

    @field_validator("app_title")
    @classmethod
    def normalize_app_title(cls, value: str | None) -> str | None:
        """Trim an optional OpenRouter title."""

        if value is None:
            return None
        normalized = value.strip()
        return normalized or None


class YahooFinanceSettings(BaseModel):
    """Configuration for the default Yahoo Finance stock data adapter."""

    model_config = ConfigDict(extra="forbid")

    enabled: bool = True
    base_url: HttpUrl = HttpUrl("https://query1.finance.yahoo.com")
    quote_path_template: str = "/v8/finance/chart/{symbol}"
    range_value: str = Field(default="1d", pattern=r"^[A-Za-z0-9]+$")
    interval: str = Field(default="1m", pattern=r"^[A-Za-z0-9]+$")
    user_agent: str = Field(default="ToolBridge-MCP", min_length=1, max_length=128)

    @field_validator("base_url")
    @classmethod
    def require_https(cls, value: HttpUrl) -> HttpUrl:
        """Require TLS for Yahoo Finance requests."""

        if value.scheme != "https" or any(
            (value.username, value.password, value.query, value.fragment)
        ):
            raise ValueError("stock provider base_url must be a safe HTTPS origin")
        if value.path not in {"", "/"}:
            raise ValueError("stock provider base_url must not include a path")
        return value

    @field_validator("quote_path_template")
    @classmethod
    def validate_quote_path(cls, value: str) -> str:
        """Require a relative path containing only the safe symbol placeholder."""

        safe_path = value.replace("{symbol}", "SYMBOL")
        if value.count("{symbol}") != 1 or not value.startswith("/"):
            raise ValueError("Yahoo quote path must contain one {symbol} placeholder")
        if (
            value.startswith("//")
            or fullmatch(r"/[A-Za-z0-9_./-]+", safe_path) is None
            or ".." in safe_path.split("/")
        ):
            raise ValueError("Yahoo quote path must be a safe relative path")
        return value


class AlphaVantageSettings(BaseModel):
    """Configuration for the optional Alpha Vantage stock adapter."""

    model_config = ConfigDict(extra="forbid")

    enabled: bool = False
    api_key: SecretStr | None = None
    base_url: HttpUrl = HttpUrl("https://www.alphavantage.co")
    query_path: str = Field(default="/query", pattern=r"^/[A-Za-z0-9_./-]+$")
    function_name: str = Field(
        default="GLOBAL_QUOTE",
        pattern=r"^[A-Z][A-Z0-9_]+$",
    )

    @field_validator("base_url")
    @classmethod
    def require_https(cls, value: HttpUrl) -> HttpUrl:
        """Require TLS for Alpha Vantage requests."""

        if value.scheme != "https" or any(
            (value.username, value.password, value.query, value.fragment)
        ):
            raise ValueError("stock provider base_url must be a safe HTTPS origin")
        if value.path not in {"", "/"}:
            raise ValueError("stock provider base_url must not include a path")
        return value

    @field_validator("query_path")
    @classmethod
    def validate_query_path(cls, value: str) -> str:
        """Prevent authority overrides and traversal in the configured path."""

        if value.startswith("//") or ".." in value.split("/"):
            raise ValueError("Alpha Vantage query path must be a safe relative path")
        return value

    @model_validator(mode="after")
    def require_key_when_enabled(self) -> "AlphaVantageSettings":
        """Require an API key only when the optional adapter is enabled."""

        secret = self.api_key.get_secret_value() if self.api_key is not None else ""
        if self.enabled and not secret:
            raise ValueError("enabled Alpha Vantage requires an API key")
        return self


class StockPriceToolSettings(BaseModel):
    """Bounded configuration for stock routing, caching, and provider priority."""

    model_config = ConfigDict(extra="forbid")

    enabled: bool = True
    timeout_seconds: float = Field(default=10.0, gt=0, le=60)
    retry_count: int = Field(default=2, ge=0, le=5)
    cache_duration_seconds: float = Field(default=60.0, ge=0, le=3_600)
    max_cache_entries: int = Field(default=256, ge=1, le=10_000)
    provider_priority: str = "yahoo_finance,alpha_vantage"
    retry_backoff_seconds: float = Field(default=0.1, ge=0, le=10)
    max_retry_backoff_seconds: float = Field(default=1.0, ge=0, le=60)
    max_provider_response_bytes: int = Field(
        default=1_048_576,
        ge=1_024,
        le=10_485_760,
    )
    health_check_symbol: str = Field(
        default="MSFT",
        min_length=1,
        max_length=20,
        pattern=r"^[A-Z0-9][A-Z0-9.\-]{0,19}$",
    )
    yahoo_finance: YahooFinanceSettings = YahooFinanceSettings()
    alpha_vantage: AlphaVantageSettings = AlphaVantageSettings()

    @field_validator("provider_priority")
    @classmethod
    def validate_provider_priority(cls, value: str) -> str:
        """Accept an optional unique ordered list of installed plugin IDs."""

        names = tuple(part.strip().lower() for part in value.split(",") if part.strip())
        if len(names) != len(set(names)):
            raise ValueError("provider_priority cannot contain duplicates")
        if any(fullmatch(r"[a-z0-9][a-z0-9_-]{0,63}", name) is None for name in names):
            raise ValueError("provider_priority contains an invalid provider identifier")
        return ",".join(names)

    @model_validator(mode="after")
    def validate_tool_configuration(self) -> "StockPriceToolSettings":
        """Keep retries bounded and require one source for an enabled tool."""

        if self.max_retry_backoff_seconds < self.retry_backoff_seconds:
            raise ValueError("stock max retry backoff cannot be smaller than initial")
        if self.enabled and not (self.yahoo_finance.enabled or self.alpha_vantage.enabled):
            raise ValueError("enabled Stock Price Tool requires a provider")
        return self

    @property
    def provider_priority_order(self) -> tuple[StockProviderName, ...]:
        """Return stable configured provider identifiers."""

        return tuple(StockProviderName(name) for name in self.provider_priority.split(","))


class OperationsSettings(BaseModel):
    """Configuration for bounded, read-only operational monitoring."""

    model_config = ConfigDict(extra="forbid")

    current_phase: str = Field(
        default="Provider Platform v1.1",
        min_length=1,
        max_length=128,
    )
    log_capacity: int = Field(default=500, ge=10, le=10_000)
    recent_log_limit: int = Field(default=100, ge=1, le=1_000)
    dashboard_api_url: HttpUrl = HttpUrl("http://127.0.0.1:8000")
    dashboard_timeout_seconds: float = Field(default=5.0, gt=0, le=30)
    readiness_require_provider: bool = False
    readiness_require_all_tools_healthy: bool = False

    @field_validator("current_phase")
    @classmethod
    def normalize_phase(cls, value: str) -> str:
        """Trim the display phase while rejecting an empty value."""

        normalized = value.strip()
        if not normalized:
            raise ValueError("current phase cannot be empty")
        return normalized

    @field_validator("dashboard_api_url")
    @classmethod
    def require_local_dashboard_api(cls, value: HttpUrl) -> HttpUrl:
        """Keep the unauthenticated dashboard connection on the local host."""

        if value.host not in {"127.0.0.1", "localhost", "::1"}:
            raise ValueError("dashboard API URL must use a loopback host")
        if any((value.username, value.password, value.query, value.fragment)):
            raise ValueError("dashboard API URL must not include credentials or query data")
        return value

    @model_validator(mode="after")
    def validate_log_limits(self) -> "OperationsSettings":
        """Keep dashboard log reads within the bounded in-memory buffer."""

        if self.recent_log_limit > self.log_capacity:
            raise ValueError("recent log limit cannot exceed log capacity")
        return self


class Settings(BaseSettings):
    """Runtime settings loaded from environment variables and `.env`."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_prefix="TOOLBRIDGE_",
        env_nested_delimiter="__",
        nested_model_default_partial_update=True,
        extra="ignore",
    )

    app_name: str = "ToolBridge MCP Server"
    environment: str = "development"
    host: str = "127.0.0.1"
    port: int = 8000
    log_level: str = "INFO"
    tool_timeout_seconds: float = Field(default=30.0, gt=0, le=300)
    max_request_bytes: int = Field(default=65_536, ge=1_024, le=10_485_760)
    max_response_bytes: int = Field(default=262_144, ge=1_024, le=10_485_760)
    provider_priority: str = ""
    provider_retry_backoff_seconds: float = Field(default=0.25, ge=0, le=60)
    provider_max_retry_backoff_seconds: float = Field(default=2.0, ge=0, le=300)
    provider_max_request_bytes: int = Field(
        default=262_144,
        ge=1_024,
        le=10_485_760,
    )
    providers: dict[str, LLMProviderSettings] = Field(default_factory=dict)
    cerebras: LLMProviderSettings = LLMProviderSettings(
        base_url="https://api.cerebras.ai/v1",
    )
    nvidia: LLMProviderSettings = LLMProviderSettings(
        base_url="https://integrate.api.nvidia.com/v1",
    )
    openrouter: OpenRouterSettings = OpenRouterSettings(
        base_url="https://openrouter.ai/api/v1",
    )
    stock_price: StockPriceToolSettings = StockPriceToolSettings()
    phase5: Phase5ToolSettings = Phase5ToolSettings()
    operations: OperationsSettings = OperationsSettings()

    @field_validator("provider_priority")
    @classmethod
    def validate_provider_priority(cls, value: str) -> str:
        """Accept an optional unique ordered list of installed plugin IDs."""

        names = tuple(part.strip().lower() for part in value.split(",") if part.strip())
        if len(names) != len(set(names)):
            raise ValueError("provider_priority cannot contain duplicates")
        if any(fullmatch(r"[a-z0-9][a-z0-9_-]{0,63}", name) is None for name in names):
            raise ValueError("provider_priority contains an invalid provider identifier")
        return ",".join(names)

    @model_validator(mode="after")
    def validate_retry_backoff(self) -> "Settings":
        """Keep the retry cap at or above the initial delay."""

        if self.provider_max_retry_backoff_seconds < self.provider_retry_backoff_seconds:
            raise ValueError("provider max retry backoff cannot be smaller than initial backoff")
        return self

    @property
    def provider_priority_order(self) -> tuple[str, ...]:
        """Return configured provider identifiers, or empty for dynamic ranking."""

        if not self.provider_priority:
            return ()
        return tuple(self.provider_priority.split(","))


@lru_cache
def get_settings() -> Settings:
    """Return a cached settings object for the current process."""

    return Settings()
