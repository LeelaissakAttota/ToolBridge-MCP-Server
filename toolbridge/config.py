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

from toolbridge.providers.domain.models import ProviderName
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
        """Require every supported stock provider once in configured order."""

        names = tuple(part.strip().lower() for part in value.split(",") if part.strip())
        try:
            providers = tuple(StockProviderName(name) for name in names)
        except ValueError as error:
            raise ValueError("stock provider priority contains an unsupported provider") from error
        if len(providers) != len(set(providers)):
            raise ValueError("stock provider priority cannot contain duplicates")
        if set(providers) != set(StockProviderName):
            raise ValueError("stock provider priority must contain every supported provider")
        return ",".join(provider.value for provider in providers)

    @field_validator("health_check_symbol", mode="before")
    @classmethod
    def normalize_health_symbol(cls, value: object) -> object:
        """Normalize the configured non-secret health probe symbol."""

        return value.strip().upper() if isinstance(value, str) else value

    @model_validator(mode="after")
    def validate_tool_configuration(self) -> "StockPriceToolSettings":
        """Keep retries bounded and require one source for an enabled tool."""

        if self.max_retry_backoff_seconds < self.retry_backoff_seconds:
            raise ValueError("stock max retry backoff cannot be smaller than initial")
        if self.enabled and not (
            self.yahoo_finance.enabled or self.alpha_vantage.enabled
        ):
            raise ValueError("enabled Stock Price Tool requires a provider")
        return self

    @property
    def provider_priority_order(self) -> tuple[StockProviderName, ...]:
        """Return stable configured provider identifiers."""

        return tuple(
            StockProviderName(name) for name in self.provider_priority.split(",")
        )


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
    provider_priority: str = "cerebras,nvidia,openrouter"
    provider_retry_backoff_seconds: float = Field(default=0.25, ge=0, le=60)
    provider_max_retry_backoff_seconds: float = Field(default=2.0, ge=0, le=300)
    provider_max_request_bytes: int = Field(
        default=262_144,
        ge=1_024,
        le=10_485_760,
    )
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

    @field_validator("provider_priority")
    @classmethod
    def validate_provider_priority(cls, value: str) -> str:
        """Require every supported provider exactly once in configured order."""

        names = tuple(part.strip().lower() for part in value.split(",") if part.strip())
        try:
            providers = tuple(ProviderName(name) for name in names)
        except ValueError as error:
            raise ValueError("provider_priority contains an unsupported provider") from error
        if len(providers) != len(set(providers)):
            raise ValueError("provider_priority cannot contain duplicates")
        if set(providers) != set(ProviderName):
            raise ValueError("provider_priority must contain every supported provider")
        return ",".join(provider.value for provider in providers)

    @model_validator(mode="after")
    def validate_retry_backoff(self) -> "Settings":
        """Keep the retry cap at or above the initial delay."""

        if self.provider_max_retry_backoff_seconds < self.provider_retry_backoff_seconds:
            raise ValueError("provider max retry backoff cannot be smaller than initial backoff")
        return self

    @property
    def provider_priority_order(self) -> tuple[ProviderName, ...]:
        """Return the validated provider priority as stable identifiers."""

        return tuple(ProviderName(name) for name in self.provider_priority.split(","))


@lru_cache
def get_settings() -> Settings:
    """Return a cached settings object for the current process."""

    return Settings()
