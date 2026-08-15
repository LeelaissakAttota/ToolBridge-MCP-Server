"""Application ports for replaceable providers and safe event logging."""

from abc import ABC, abstractmethod
from collections.abc import AsyncIterator
from typing import Protocol

from toolbridge.providers.domain.models import (
    GenerationChunk,
    GenerationRequest,
    GenerationResponse,
    ProviderCapabilities,
    ProviderErrorCategory,
    ProviderHealthCheck,
    ProviderModel,
    ProviderStatus,
)


class BaseProvider(ABC):
    """Provider-neutral lifecycle, discovery, and generation interface."""

    @property
    @abstractmethod
    def name(self) -> str:
        """Return the stable provider identifier."""

    @property
    def capabilities(self) -> ProviderCapabilities:
        """Return capabilities; legacy adapters retain chat defaults."""

        return ProviderCapabilities(chat=True, streaming=True)

    @abstractmethod
    async def initialize(self) -> None:
        """Allocate provider resources without performing a generation request."""

    @abstractmethod
    async def health_check(self) -> ProviderHealthCheck:
        """Probe provider availability and return normalized latency."""

    @abstractmethod
    async def list_models(self) -> tuple[ProviderModel, ...]:
        """Return normalized available model identifiers."""

    async def discover_models(self) -> tuple[ProviderModel, ...]:
        """Discover rich metadata; legacy providers delegate to list_models."""

        return await self.list_models()

    @abstractmethod
    async def generate(self, request: GenerationRequest) -> GenerationResponse:
        """Generate one normalized response."""

    @abstractmethod
    def stream_generate(self, request: GenerationRequest) -> AsyncIterator[GenerationChunk]:
        """Generate normalized response chunks."""

    @abstractmethod
    async def close(self) -> None:
        """Release provider resources idempotently."""


class ProviderEventLogger(Protocol):
    """Allowlisted structured logging boundary for provider activity."""

    def record(
        self,
        *,
        provider: str,
        latency_ms: float,
        status: ProviderStatus,
        request_id: str,
        error_category: ProviderErrorCategory | None = None,
    ) -> None:
        """Record provider metadata without prompts, results, or secrets."""


class NullProviderEventLogger:
    """No-op provider logger for isolated application use and tests."""

    def record(
        self,
        *,
        provider: str,
        latency_ms: float,
        status: ProviderStatus,
        request_id: str,
        error_category: ProviderErrorCategory | None = None,
    ) -> None:
        """Discard an event."""


class CompositeProviderEventLogger:
    """Forward provider events to ordered safe observers."""

    def __init__(self, observers: tuple[ProviderEventLogger, ...]) -> None:
        self._observers = observers

    def record(
        self,
        *,
        provider: str,
        latency_ms: float,
        status: ProviderStatus,
        request_id: str,
        error_category: ProviderErrorCategory | None = None,
    ) -> None:
        """Forward one provider event without adding payload fields."""

        for observer in self._observers:
            observer.record(
                provider=provider,
                latency_ms=latency_ms,
                status=status,
                request_id=request_id,
                error_category=error_category,
            )


class ProviderUsageRecorder(Protocol):
    """Record normalized generation usage without content or prompts."""

    def record_generation(
        self,
        *,
        provider: str,
        input_tokens: int,
        output_tokens: int,
        total_tokens: int,
    ) -> None:
        """Record one completed generation and its normalized token counts."""


class NullProviderUsageRecorder:
    """No-op provider usage observer for isolated router tests."""

    def record_generation(
        self,
        *,
        provider: str,
        input_tokens: int,
        output_tokens: int,
        total_tokens: int,
    ) -> None:
        """Discard generation usage."""
