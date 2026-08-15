"""Normalized provider-domain contracts independent of vendor transports."""

from datetime import datetime
from enum import StrEnum
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

PROVIDER_REQUEST_ID_PATTERN = r"^[A-Za-z0-9][A-Za-z0-9._:-]{0,127}$"
PROVIDER_ID_PATTERN = r"^[a-z0-9][a-z0-9_-]{0,63}$"


class ProviderName(StrEnum):
    """Built-in identifiers retained as a compatibility convenience.

    Runtime routing accepts any validated identifier; this enum is not the
    provider registry and therefore does not limit installed plugins.
    """

    CEREBRAS = "cerebras"
    NVIDIA = "nvidia"
    OPENROUTER = "openrouter"


class ProviderCapability(StrEnum):
    """Capabilities used for model discovery and request routing."""

    CHAT = "chat"
    REASONING = "reasoning"
    STREAMING = "streaming"
    EMBEDDINGS = "embeddings"
    IMAGE_GENERATION = "image_generation"
    AUDIO_GENERATION = "audio_generation"
    TOOL_USE = "tool_use"
    FUNCTION_CALLING = "function_calling"
    VISION = "vision"
    LONG_CONTEXT = "long_context"
    JSON_MODE = "json_mode"
    WEB_SEARCH = "web_search"
    CODE_GENERATION = "code_generation"


class RoutingTask(StrEnum):
    """Provider-neutral task hints accepted by the ranking engine."""

    CHAT = "chat"
    REASONING = "reasoning"
    SUMMARIZATION = "summarization"
    CODE = "code"
    VISION = "vision"
    EMBEDDING = "embedding"
    IMAGE = "image"
    AUDIO = "audio"
    WEB_SEARCH = "web_search"


class ProviderCapabilities(BaseModel):
    """Normalized capability flags supplied by each provider plugin."""

    model_config = ConfigDict(extra="forbid", frozen=True, strict=True)

    chat: bool = False
    reasoning: bool = False
    streaming: bool = False
    embeddings: bool = False
    image_generation: bool = False
    audio_generation: bool = False
    tool_use: bool = False
    function_calling: bool = False
    vision: bool = False
    long_context: bool = False
    json_mode: bool = False
    web_search: bool = False
    code_generation: bool = False

    def supports(self, required: frozenset[ProviderCapability]) -> bool:
        """Return whether every requested capability is available."""

        return all(bool(getattr(self, item.value)) for item in required)

    def enabled(self) -> tuple[str, ...]:
        """Return stable names for dashboard and API projection."""

        return tuple(item.value for item in ProviderCapability if bool(getattr(self, item.value)))


class ProviderStatus(StrEnum):
    """Observable lifecycle and availability states."""

    UNINITIALIZED = "uninitialized"
    HEALTHY = "healthy"
    DEGRADED = "degraded"
    UNAVAILABLE = "unavailable"
    CLOSED = "closed"


class ProviderErrorCategory(StrEnum):
    """Stable provider failure categories exposed by the application layer."""

    TIMEOUT = "timeout"
    AUTHENTICATION = "authentication"
    RATE_LIMIT = "rate_limit"
    UNAVAILABLE = "unavailable"
    INVALID_REQUEST = "invalid_request"
    INVALID_RESPONSE = "invalid_response"
    BUDGET_EXCEEDED = "budget_exceeded"
    CAPABILITY_UNAVAILABLE = "capability_unavailable"
    INTERNAL = "internal"


class ProviderModel(BaseModel):
    """Normalized metadata returned by provider model discovery."""

    model_config = ConfigDict(extra="forbid", frozen=True, strict=True)

    id: str = Field(min_length=1, max_length=256)
    provider: ProviderName | str
    capabilities: ProviderCapabilities = Field(default_factory=ProviderCapabilities)
    is_free: bool = False
    input_cost_per_million_tokens_usd: float = Field(default=0.0, ge=0)
    output_cost_per_million_tokens_usd: float = Field(default=0.0, ge=0)
    context_window: int | None = Field(default=None, ge=1)
    latency_ms: float | None = Field(default=None, ge=0)
    health_score: float = Field(default=1.0, ge=0, le=1)
    available: bool = True
    reasoning_quality: float = Field(default=0.5, ge=0, le=1)
    discovered_at: datetime | None = None


class ChatMessage(BaseModel):
    """Text-only chat message accepted by every provider adapter."""

    model_config = ConfigDict(extra="forbid", frozen=True, strict=True)

    role: Literal["system", "user", "assistant"]
    content: str = Field(min_length=1)


class GenerationRequest(BaseModel):
    """Provider-neutral generation request with optional smart-routing hints."""

    model_config = ConfigDict(extra="forbid", frozen=True, strict=True)

    messages: tuple[ChatMessage, ...] = Field(min_length=1)
    model: str | None = Field(default=None, min_length=1, max_length=256)
    max_tokens: int | None = Field(default=None, ge=1)
    temperature: float | None = Field(default=None, ge=0, le=2)
    request_id: str | None = Field(default=None, pattern=PROVIDER_REQUEST_ID_PATTERN)
    task: RoutingTask = RoutingTask.CHAT
    required_capabilities: frozenset[ProviderCapability] = Field(default_factory=frozenset)
    estimated_input_tokens: int = Field(default=0, ge=0)
    max_cost_usd: float | None = Field(default=None, ge=0)


class TokenUsage(BaseModel):
    """Normalized token accounting when supplied by a provider."""

    model_config = ConfigDict(extra="forbid", frozen=True, strict=True)

    input_tokens: int = Field(default=0, ge=0)
    output_tokens: int = Field(default=0, ge=0)
    total_tokens: int = Field(default=0, ge=0)

    @model_validator(mode="after")
    def validate_total(self) -> "TokenUsage":
        """Reject totals smaller than the reported input and output counts."""

        if self.total_tokens < self.input_tokens + self.output_tokens:
            raise ValueError("total_tokens cannot be smaller than component counts")
        return self


class GenerationResponse(BaseModel):
    """Normalized non-streaming provider response."""

    model_config = ConfigDict(extra="forbid", frozen=True, strict=True)

    provider: ProviderName | str
    request_id: str = Field(pattern=PROVIDER_REQUEST_ID_PATTERN)
    model: str = Field(min_length=1, max_length=256)
    content: str
    finish_reason: str | None = Field(default=None, max_length=64)
    usage: TokenUsage = Field(default_factory=TokenUsage)


class GenerationChunk(BaseModel):
    """Normalized streaming response fragment."""

    model_config = ConfigDict(extra="forbid", frozen=True, strict=True)

    provider: ProviderName | str
    request_id: str = Field(pattern=PROVIDER_REQUEST_ID_PATTERN)
    model: str = Field(min_length=1, max_length=256)
    delta: str
    finish_reason: str | None = Field(default=None, max_length=64)


class ProviderHealthCheck(BaseModel):
    """Successful health probe returned by a provider adapter."""

    model_config = ConfigDict(extra="forbid", frozen=True, strict=True)

    provider: ProviderName | str
    latency_ms: float = Field(ge=0)


class ProviderStatusSnapshot(BaseModel):
    """Read-only provider health and request-history snapshot."""

    model_config = ConfigDict(extra="forbid", frozen=True, strict=True)

    provider: ProviderName | str
    status: ProviderStatus
    latency_ms: float | None = Field(default=None, ge=0)
    last_successful_request: datetime | None = None
    last_failed_request: datetime | None = None
    last_error_category: ProviderErrorCategory | None = None
    requests: int = Field(default=0, ge=0)
    successes: int = Field(default=0, ge=0)
    errors: int = Field(default=0, ge=0)
    retries: int = Field(default=0, ge=0)
    success_rate: float = Field(default=1.0, ge=0, le=1)
    average_latency_ms: float = Field(default=0.0, ge=0)
    health_score: float = Field(default=1.0, ge=0, le=1)


class ModelSelection(BaseModel):
    """Observable result of capability-aware model ranking."""

    model_config = ConfigDict(extra="forbid", frozen=True, strict=True)

    provider: str
    model: str
    score: float
    reason: str


class ProviderBudgetSnapshot(BaseModel):
    """Safe process-local budget state for one provider."""

    model_config = ConfigDict(extra="forbid", frozen=True, strict=True)

    provider: str
    daily_spend_usd: float = Field(ge=0)
    monthly_spend_usd: float = Field(ge=0)
    daily_limit_usd: float | None = Field(default=None, ge=0)
    monthly_limit_usd: float | None = Field(default=None, ge=0)
    per_request_limit_usd: float | None = Field(default=None, ge=0)
    soft_limit_reached: bool = False
    hard_limit_reached: bool = False
