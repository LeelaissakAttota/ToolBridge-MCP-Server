"""Normalized provider-domain contracts independent of vendor transports."""

from datetime import datetime
from enum import StrEnum
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

PROVIDER_REQUEST_ID_PATTERN = r"^[A-Za-z0-9][A-Za-z0-9._:-]{0,127}$"


class ProviderName(StrEnum):
    """Supported provider identifiers."""

    CEREBRAS = "cerebras"
    NVIDIA = "nvidia"
    OPENROUTER = "openrouter"


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
    INTERNAL = "internal"


class ProviderModel(BaseModel):
    """Normalized model metadata returned by provider discovery."""

    model_config = ConfigDict(extra="forbid", frozen=True, strict=True)

    id: str = Field(min_length=1, max_length=256)
    provider: ProviderName


class ChatMessage(BaseModel):
    """Text-only chat message accepted by every provider adapter."""

    model_config = ConfigDict(extra="forbid", frozen=True, strict=True)

    role: Literal["system", "user", "assistant"]
    content: str = Field(min_length=1)


class GenerationRequest(BaseModel):
    """Provider-neutral generation request."""

    model_config = ConfigDict(extra="forbid", frozen=True, strict=True)

    messages: tuple[ChatMessage, ...] = Field(min_length=1)
    model: str | None = Field(default=None, min_length=1, max_length=256)
    max_tokens: int | None = Field(default=None, ge=1)
    temperature: float | None = Field(default=None, ge=0, le=2)
    request_id: str | None = Field(default=None, pattern=PROVIDER_REQUEST_ID_PATTERN)


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

    provider: ProviderName
    request_id: str = Field(pattern=PROVIDER_REQUEST_ID_PATTERN)
    model: str = Field(min_length=1, max_length=256)
    content: str
    finish_reason: str | None = Field(default=None, max_length=64)
    usage: TokenUsage = Field(default_factory=TokenUsage)


class GenerationChunk(BaseModel):
    """Normalized streaming response fragment."""

    model_config = ConfigDict(extra="forbid", frozen=True, strict=True)

    provider: ProviderName
    request_id: str = Field(pattern=PROVIDER_REQUEST_ID_PATTERN)
    model: str = Field(min_length=1, max_length=256)
    delta: str
    finish_reason: str | None = Field(default=None, max_length=64)


class ProviderHealthCheck(BaseModel):
    """Successful health probe returned by a provider adapter."""

    model_config = ConfigDict(extra="forbid", frozen=True, strict=True)

    provider: ProviderName
    latency_ms: float = Field(ge=0)


class ProviderStatusSnapshot(BaseModel):
    """Read-only provider health and request-history snapshot."""

    model_config = ConfigDict(extra="forbid", frozen=True, strict=True)

    provider: ProviderName
    status: ProviderStatus
    latency_ms: float | None = Field(default=None, ge=0)
    last_successful_request: datetime | None = None
    last_failed_request: datetime | None = None
    last_error_category: ProviderErrorCategory | None = None
