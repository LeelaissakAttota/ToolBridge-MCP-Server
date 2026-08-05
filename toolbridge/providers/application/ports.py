"""Application ports for replaceable providers and safe event logging."""

from abc import ABC, abstractmethod
from collections.abc import AsyncIterator
from typing import Protocol

from toolbridge.providers.domain.models import (
    GenerationChunk,
    GenerationRequest,
    GenerationResponse,
    ProviderErrorCategory,
    ProviderHealthCheck,
    ProviderModel,
    ProviderName,
    ProviderStatus,
)


class BaseProvider(ABC):
    """Provider-neutral lifecycle and generation interface."""

    @property
    @abstractmethod
    def name(self) -> ProviderName:
        """Return the stable provider identifier."""

    @abstractmethod
    async def initialize(self) -> None:
        """Allocate provider resources without performing a generation request."""

    @abstractmethod
    async def health_check(self) -> ProviderHealthCheck:
        """Probe provider availability and return normalized latency."""

    @abstractmethod
    async def list_models(self) -> tuple[ProviderModel, ...]:
        """Return normalized available model identifiers."""

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
        provider: ProviderName,
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
        provider: ProviderName,
        latency_ms: float,
        status: ProviderStatus,
        request_id: str,
        error_category: ProviderErrorCategory | None = None,
    ) -> None:
        """Discard an event."""
