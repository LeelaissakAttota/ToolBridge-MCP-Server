"""Replaceable ports used by the tool framework and stock application service."""

from abc import ABC, abstractmethod
from typing import Protocol

from toolbridge.core.contracts import ToolDefinition
from toolbridge.tools.domain.models import (
    ProviderHealthStatus,
    StockPriceOutput,
    StockProviderName,
    ToolHealthStatus,
)


class BaseTool(ABC):
    """Common lifecycle and definition interface implemented by every tool."""

    @property
    @abstractmethod
    def definition(self) -> ToolDefinition:
        """Return the immutable registration and validation contract."""

    @abstractmethod
    async def initialize(self) -> None:
        """Initialize resources without performing implicit health probes."""

    @abstractmethod
    async def health_check(self) -> ToolHealthStatus:
        """Return the current typed health status."""

    @abstractmethod
    async def close(self) -> None:
        """Release resources and make later execution fail safely."""


class StockQuoteProvider(ABC):
    """Provider-neutral interface for retrieving one normalized stock quote."""

    @property
    @abstractmethod
    def name(self) -> StockProviderName:
        """Return the stable provider identifier."""

    @abstractmethod
    async def initialize(self) -> None:
        """Initialize provider resources."""

    @abstractmethod
    async def get_quote(self, symbol: str) -> StockPriceOutput:
        """Return a normalized quote or raise a normalized stock data error."""

    @abstractmethod
    async def health_check(self, symbol: str) -> ProviderHealthStatus:
        """Probe the provider with the configured health symbol."""

    @abstractmethod
    async def close(self) -> None:
        """Release provider resources."""


class StockProviderEventLogger(Protocol):
    """Allowlisted logging boundary for stock provider attempts."""

    def completed(
        self,
        *,
        provider: StockProviderName,
        operation_id: str,
        latency_ms: float,
        status: str,
        error_category: str | None = None,
    ) -> None:
        """Record one attempt without symbols, credentials, URLs, or payloads."""


class NullStockProviderEventLogger:
    """No-op stock provider logger used by isolated application tests."""

    def completed(
        self,
        *,
        provider: StockProviderName,
        operation_id: str,
        latency_ms: float,
        status: str,
        error_category: str | None = None,
    ) -> None:
        """Discard an attempt event."""


class CompositeStockProviderEventLogger:
    """Forward stock provider events to ordered safe observers."""

    def __init__(self, observers: tuple[StockProviderEventLogger, ...]) -> None:
        self._observers = observers

    def completed(
        self,
        *,
        provider: StockProviderName,
        operation_id: str,
        latency_ms: float,
        status: str,
        error_category: str | None = None,
    ) -> None:
        """Forward one stock attempt without adding request data."""

        for observer in self._observers:
            observer.completed(
                provider=provider,
                operation_id=operation_id,
                latency_ms=latency_ms,
                status=status,
                error_category=error_category,
            )
