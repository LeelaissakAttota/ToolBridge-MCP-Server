"""Structured allowlisted logging for stock provider attempts."""

import json
import logging
from datetime import UTC, datetime
from typing import Any

from toolbridge.tools.domain.models import StockProviderName

SAFE_STOCK_EVENT_FIELDS = (
    "event",
    "tool_name",
    "provider",
    "operation_id",
    "latency_ms",
    "status",
    "error_category",
)


class StructuredStockFormatter(logging.Formatter):
    """Serialize only approved stock operation metadata."""

    def format(self, record: logging.LogRecord) -> str:
        """Return one compact JSON event without the source message."""

        payload: dict[str, Any] = {
            "timestamp": datetime.fromtimestamp(record.created, UTC).isoformat(),
            "level": record.levelname,
        }
        for field in SAFE_STOCK_EVENT_FIELDS:
            value = getattr(record, field, None)
            if value is not None:
                payload[field] = value
        return json.dumps(payload, ensure_ascii=False, separators=(",", ":"))


class StructuredStockProviderEventLogger:
    """Log stock provider outcomes without symbols, URLs, keys, or payloads."""

    def __init__(self, logger: logging.Logger) -> None:
        self._logger = logger

    def completed(
        self,
        *,
        provider: StockProviderName,
        operation_id: str,
        latency_ms: float,
        status: str,
        error_category: str | None = None,
    ) -> None:
        """Emit one allowlisted provider attempt event."""

        level = logging.INFO if status == "succeeded" else logging.WARNING
        self._logger.log(
            level,
            "stock_provider_attempt_completed",
            extra={
                "event": "stock_provider_attempt_completed",
                "tool_name": "stock_price",
                "provider": provider.value,
                "operation_id": operation_id,
                "latency_ms": latency_ms,
                "status": status,
                "error_category": error_category,
            },
        )


def configure_stock_logging(log_level: str) -> StructuredStockProviderEventLogger:
    """Configure the dedicated stock provider logger once."""

    logger = logging.getLogger("toolbridge.stock")
    level = getattr(logging, log_level.upper(), logging.INFO)
    logger.setLevel(level)
    logger.propagate = False
    if not any(getattr(handler, "toolbridge_handler", False) for handler in logger.handlers):
        handler = logging.StreamHandler()
        handler.setFormatter(StructuredStockFormatter())
        handler.toolbridge_handler = True  # type: ignore[attr-defined]
        logger.addHandler(handler)
    return StructuredStockProviderEventLogger(logger)
