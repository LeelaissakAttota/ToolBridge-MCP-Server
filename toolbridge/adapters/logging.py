"""Structured, audit-safe execution logging adapter."""

import json
import logging
from datetime import UTC, datetime
from typing import Any

from toolbridge.core.contracts import ErrorCode

SAFE_EVENT_FIELDS = (
    "event",
    "tool_name",
    "correlation_id",
    "duration_ms",
    "error_code",
    "exception_type",
)


class StructuredJsonFormatter(logging.Formatter):
    """Serialize only approved execution metadata as one JSON object."""

    def format(self, record: logging.LogRecord) -> str:
        payload: dict[str, Any] = {
            "timestamp": datetime.fromtimestamp(record.created, UTC).isoformat(),
            "level": record.levelname,
        }
        for field in SAFE_EVENT_FIELDS:
            value = getattr(record, field, None)
            if value is not None:
                payload[field] = value
        return json.dumps(payload, ensure_ascii=False, separators=(",", ":"))


class StructuredExecutionEventLogger:
    """Emit tool lifecycle events without arguments, results, or error messages."""

    def __init__(self, logger: logging.Logger) -> None:
        self._logger = logger

    def started(self, *, tool_name: str, correlation_id: str) -> None:
        self._logger.info(
            "tool_execution_started",
            extra={
                "event": "tool_execution_started",
                "tool_name": tool_name,
                "correlation_id": correlation_id,
            },
        )

    def succeeded(
        self,
        *,
        tool_name: str,
        correlation_id: str,
        duration_ms: float,
    ) -> None:
        self._logger.info(
            "tool_execution_succeeded",
            extra={
                "event": "tool_execution_succeeded",
                "tool_name": tool_name,
                "correlation_id": correlation_id,
                "duration_ms": duration_ms,
            },
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
        self._logger.warning(
            "tool_execution_failed",
            extra={
                "event": "tool_execution_failed",
                "tool_name": tool_name,
                "correlation_id": correlation_id,
                "duration_ms": duration_ms,
                "error_code": error_code.value,
                "exception_type": exception_type,
            },
        )


def configure_execution_logging(log_level: str) -> StructuredExecutionEventLogger:
    """Configure the dedicated execution logger once and return its adapter."""

    logger = logging.getLogger("toolbridge.execution")
    level = getattr(logging, log_level.upper(), logging.INFO)
    logger.setLevel(level)
    logger.propagate = False
    if not any(getattr(handler, "toolbridge_handler", False) for handler in logger.handlers):
        handler = logging.StreamHandler()
        handler.setFormatter(StructuredJsonFormatter())
        handler.toolbridge_handler = True  # type: ignore[attr-defined]
        logger.addHandler(handler)
    return StructuredExecutionEventLogger(logger)
