"""Bounded in-process store of sanitized model-routing records."""

from collections import deque
from threading import Lock

from toolbridge.providers.domain.routing import ModelRoutingRecord

DEFAULT_ROUTING_HISTORY_LIMIT = 200


class ModelRoutingHistory:
    """Thread-safe ring buffer; holds routing metadata only, never content."""

    def __init__(self, limit: int = DEFAULT_ROUTING_HISTORY_LIMIT) -> None:
        if limit <= 0:
            raise ValueError("limit must be greater than zero")
        self._records: deque[ModelRoutingRecord] = deque(maxlen=limit)
        self._lock = Lock()

    def record(self, record: ModelRoutingRecord) -> None:
        with self._lock:
            self._records.append(record)

    def recent(self, limit: int | None = None) -> tuple[ModelRoutingRecord, ...]:
        """Return newest-first records."""

        with self._lock:
            items = tuple(reversed(self._records))
        return items if limit is None else items[: max(limit, 0)]

    def __len__(self) -> int:
        with self._lock:
            return len(self._records)
