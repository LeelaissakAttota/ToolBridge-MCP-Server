"""Ports implemented by infrastructure adapters."""

from typing import Protocol

from toolbridge.core.contracts import ErrorCode


class ExecutionEventLogger(Protocol):
    """Safe logging boundary used by the execution service."""

    def started(self, *, tool_name: str, correlation_id: str) -> None:
        """Record that execution started without logging request data."""

    def succeeded(
        self,
        *,
        tool_name: str,
        correlation_id: str,
        duration_ms: float,
    ) -> None:
        """Record a successful execution."""

    def failed(
        self,
        *,
        tool_name: str | None,
        correlation_id: str,
        duration_ms: float,
        error_code: ErrorCode,
        exception_type: str | None = None,
    ) -> None:
        """Record a safe failure event without payloads or exception messages."""


class NullExecutionEventLogger:
    """No-op logger for isolated core use and tests."""

    def started(self, *, tool_name: str, correlation_id: str) -> None:
        """Discard a start event."""

    def succeeded(
        self,
        *,
        tool_name: str,
        correlation_id: str,
        duration_ms: float,
    ) -> None:
        """Discard a success event."""

    def failed(
        self,
        *,
        tool_name: str | None,
        correlation_id: str,
        duration_ms: float,
        error_code: ErrorCode,
        exception_type: str | None = None,
    ) -> None:
        """Discard a failure event."""


class CompositeExecutionEventLogger:
    """Forward execution events to ordered logging and metrics observers."""

    def __init__(self, observers: tuple[ExecutionEventLogger, ...]) -> None:
        self._observers = observers

    def started(self, *, tool_name: str, correlation_id: str) -> None:
        """Forward a start event in configured observer order."""

        for observer in self._observers:
            observer.started(tool_name=tool_name, correlation_id=correlation_id)

    def succeeded(
        self,
        *,
        tool_name: str,
        correlation_id: str,
        duration_ms: float,
    ) -> None:
        """Forward a success event in configured observer order."""

        for observer in self._observers:
            observer.succeeded(
                tool_name=tool_name,
                correlation_id=correlation_id,
                duration_ms=duration_ms,
            )

    def failed(
        self,
        *,
        tool_name: str | None,
        correlation_id: str,
        duration_ms: float,
        error_code: ErrorCode,
        exception_type: str | None = None,
    ) -> None:
        """Forward a failure event in configured observer order."""

        for observer in self._observers:
            observer.failed(
                tool_name=tool_name,
                correlation_id=correlation_id,
                duration_ms=duration_ms,
                error_code=error_code,
                exception_type=exception_type,
            )
