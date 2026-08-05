"""Allowlisted JSON logging for provider lifecycle and request outcomes."""

import json
import logging
from datetime import UTC, datetime
from typing import Any

from toolbridge.providers.domain.models import (
    ProviderErrorCategory,
    ProviderName,
    ProviderStatus,
)

SAFE_PROVIDER_EVENT_FIELDS = (
    "provider",
    "latency_ms",
    "status",
    "request_id",
    "error_category",
)


class ProviderJsonFormatter(logging.Formatter):
    """Serialize only approved provider metadata as one JSON object."""

    def format(self, record: logging.LogRecord) -> str:
        payload: dict[str, Any] = {
            "timestamp": datetime.fromtimestamp(record.created, UTC).isoformat(),
            "level": record.levelname,
        }
        for field in SAFE_PROVIDER_EVENT_FIELDS:
            value = getattr(record, field, None)
            if value is not None:
                payload[field] = value
        return json.dumps(payload, ensure_ascii=False, separators=(",", ":"))


class StructuredProviderEventLogger:
    """Emit provider metadata without credentials, prompts, or response content."""

    def __init__(self, logger: logging.Logger) -> None:
        self._logger = logger

    def record(
        self,
        *,
        provider: ProviderName,
        latency_ms: float,
        status: ProviderStatus,
        request_id: str,
        error_category: ProviderErrorCategory | None = None,
    ) -> None:
        """Record one allowlisted provider event."""

        level = logging.INFO if error_category is None else logging.WARNING
        self._logger.log(
            level,
            "provider_event",
            extra={
                "provider": provider.value,
                "latency_ms": latency_ms,
                "status": status.value,
                "request_id": request_id,
                "error_category": (
                    error_category.value if error_category is not None else None
                ),
            },
        )


def configure_provider_logging(log_level: str) -> StructuredProviderEventLogger:
    """Configure the dedicated provider logger once and return its adapter."""

    logger = logging.getLogger("toolbridge.providers")
    level = getattr(logging, log_level.upper(), logging.INFO)
    logger.setLevel(level)
    logger.propagate = False
    if not any(
        getattr(handler, "toolbridge_provider_handler", False)
        for handler in logger.handlers
    ):
        handler = logging.StreamHandler()
        handler.setFormatter(ProviderJsonFormatter())
        handler.toolbridge_provider_handler = True  # type: ignore[attr-defined]
        logger.addHandler(handler)
    return StructuredProviderEventLogger(logger)
