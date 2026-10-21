"""Thread-safe in-process metrics observer for tool executions."""

from dataclasses import dataclass
from datetime import UTC, datetime
from threading import Lock

from toolbridge.core.contracts import ErrorCode
from toolbridge.tools.domain.models import ToolMetricsSnapshot


@dataclass(slots=True)
class _MutableMetrics:
    total: int = 0
    succeeded: int = 0
    failed: int = 0
    total_duration_ms: float = 0.0
    last_duration_ms: float | None = None
    last_error_code: str | None = None
    last_execution_at: datetime | None = None


class InMemoryToolMetrics:
    """Aggregate bounded label-free metrics without retaining request data."""

    def __init__(self) -> None:
        self._values: dict[str, _MutableMetrics] = {}
        self._lock = Lock()

    def started(self, *, tool_name: str, correlation_id: str) -> None:
        """Count an execution without retaining its correlation identifier."""

        del correlation_id
        with self._lock:
            self._entry(tool_name).total += 1

    def succeeded(
        self,
        *,
        tool_name: str,
        correlation_id: str,
        duration_ms: float,
    ) -> None:
        """Record one successful duration."""

        del correlation_id
        with self._lock:
            value = self._entry(tool_name)
            value.succeeded += 1
            value.total_duration_ms += duration_ms
            value.last_duration_ms = duration_ms
            value.last_error_code = None
            value.last_execution_at = datetime.now(UTC)

    def failed(
        self,
        *,
        tool_name: str | None,
        correlation_id: str,
        duration_ms: float,
        error_code: ErrorCode,
        exception_type: str | None = None,
    ) -> None:
        """Record one failed duration without retaining exception details."""

        del correlation_id, exception_type
        if tool_name is None:
            return
        with self._lock:
            value = self._entry(tool_name)
            value.failed += 1
            value.total_duration_ms += duration_ms
            value.last_duration_ms = duration_ms
            value.last_error_code = error_code.value
            value.last_execution_at = datetime.now(UTC)

    def snapshot(self, tool_name: str) -> ToolMetricsSnapshot:
        """Return an immutable metrics snapshot for one tool."""

        with self._lock:
            value = self._entry(tool_name)
            completed = value.succeeded + value.failed
            average = value.total_duration_ms / completed if completed else 0.0
            return ToolMetricsSnapshot(
                tool_name=tool_name,
                total_executions=value.total,
                successful_executions=value.succeeded,
                failed_executions=value.failed,
                average_duration_ms=round(average, 3),
                last_duration_ms=value.last_duration_ms,
                last_error_code=value.last_error_code,
                last_execution_at=value.last_execution_at,
            )

    def _entry(self, tool_name: str) -> _MutableMetrics:
        return self._values.setdefault(tool_name, _MutableMetrics())
