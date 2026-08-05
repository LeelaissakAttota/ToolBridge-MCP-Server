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

