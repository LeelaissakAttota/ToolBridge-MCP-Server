"""Bounded process-local metrics and safe operational event storage."""

from collections import Counter, deque
from dataclasses import dataclass
from datetime import UTC, datetime
from threading import Lock

from toolbridge.core.contracts import ErrorCode
from toolbridge.operations.domain.models import SafeLogEntry, SafeLogLevel
from toolbridge.providers.domain.models import (
    ProviderErrorCategory,
    ProviderStatus,
)
from toolbridge.tools.domain.models import StockProviderName


@dataclass(frozen=True, slots=True)
class ProviderUsageValue:
    """Immutable provider generation and timing totals."""

    requests: int
    input_tokens: int
    output_tokens: int
    total_tokens: int
    estimated_cost_usd: float
    average_latency_ms: float


@dataclass(slots=True)
class _ProviderUsage:
    requests: int = 0
    input_tokens: int = 0
    output_tokens: int = 0
    total_tokens: int = 0
    estimated_cost_usd: float = 0.0
    timed_events: int = 0
    total_latency_ms: float = 0.0


class InMemoryOperationalMetrics:
    """Collect bounded operational data without retaining inputs or outputs."""

    def __init__(
        self,
        *,
        log_capacity: int,
        provider_costs: dict[str, tuple[float, float]],
    ) -> None:
        if log_capacity <= 0:
            raise ValueError("log capacity must be greater than zero")
        self._logs: deque[SafeLogEntry] = deque(maxlen=log_capacity)
        self._provider_costs = dict(provider_costs)
        self._provider_usage: dict[str, _ProviderUsage] = {}
        self._error_categories: Counter[str] = Counter()
        self._lock = Lock()

    def started(self, *, tool_name: str, correlation_id: str) -> None:
        """Retain only safe tool execution metadata."""

        self._append(
            level=SafeLogLevel.INFO,
            source="tool",
            event="tool_execution_started",
            component=tool_name,
            status="started",
            request_id=correlation_id,
        )

    def succeeded(
        self,
        *,
        tool_name: str,
        correlation_id: str,
        duration_ms: float,
    ) -> None:
        """Record one safe successful tool event."""

        self._append(
            level=SafeLogLevel.INFO,
            source="tool",
            event="tool_execution_succeeded",
            component=tool_name,
            status="succeeded",
            latency_ms=duration_ms,
            request_id=correlation_id,
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
        """Record one categorized failure without retaining exception details."""

        del exception_type
        with self._lock:
            self._error_categories[error_code.value] += 1
        self._append(
            level=SafeLogLevel.WARNING,
            source="tool",
            event="tool_execution_failed",
            component=tool_name,
            status="failed",
            latency_ms=duration_ms,
            request_id=correlation_id,
            error_category=error_code.value,
        )

    def record(
        self,
        *,
        provider: str,
        latency_ms: float,
        status: ProviderStatus,
        request_id: str,
        error_category: ProviderErrorCategory | None = None,
    ) -> None:
        """Record safe provider timing and status metadata."""

        with self._lock:
            usage = self._provider_entry(provider)
            usage.timed_events += 1
            usage.total_latency_ms += latency_ms
        self._append(
            level=(SafeLogLevel.INFO if error_category is None else SafeLogLevel.WARNING),
            source="provider",
            event="provider_request_completed",
            component=str(provider),
            status=status.value,
            latency_ms=latency_ms,
            request_id=request_id,
            error_category=(error_category.value if error_category is not None else None),
        )

    def completed(
        self,
        *,
        provider: StockProviderName,
        operation_id: str,
        latency_ms: float,
        status: str,
        error_category: str | None = None,
    ) -> None:
        """Record a safe stock-provider attempt for the log viewer."""

        self._append(
            level=(SafeLogLevel.INFO if error_category is None else SafeLogLevel.WARNING),
            source="stock_provider",
            event="stock_provider_attempt_completed",
            component=str(provider),
            status=status,
            latency_ms=latency_ms,
            request_id=operation_id,
            error_category=error_category,
        )

    def record_generation(
        self,
        *,
        provider: str,
        input_tokens: int,
        output_tokens: int,
        total_tokens: int,
    ) -> None:
        """Aggregate normalized usage and configured cost estimates."""

        input_price, output_price = self._provider_costs.get(provider, (0.0, 0.0))
        estimated_cost = (input_tokens * input_price + output_tokens * output_price) / 1_000_000
        with self._lock:
            usage = self._provider_entry(provider)
            usage.requests += 1
            usage.input_tokens += input_tokens
            usage.output_tokens += output_tokens
            usage.total_tokens += total_tokens
            usage.estimated_cost_usd += estimated_cost

    def record_system(
        self,
        *,
        event: str,
        status: str,
        error_category: str | None = None,
    ) -> None:
        """Record one allowlisted lifecycle or validation event."""

        self._append(
            level=(SafeLogLevel.INFO if error_category is None else SafeLogLevel.ERROR),
            source="system",
            event=event,
            component="toolbridge-mcp",
            status=status,
            error_category=error_category,
        )

    def provider_usage(self, provider: str) -> ProviderUsageValue:
        """Return immutable provider usage and average timing."""

        with self._lock:
            usage = self._provider_entry(provider)
            average = usage.total_latency_ms / usage.timed_events if usage.timed_events else 0.0
            return ProviderUsageValue(
                requests=usage.requests,
                input_tokens=usage.input_tokens,
                output_tokens=usage.output_tokens,
                total_tokens=usage.total_tokens,
                estimated_cost_usd=round(usage.estimated_cost_usd, 8),
                average_latency_ms=round(average, 3),
            )

    def error_categories(self) -> dict[str, int]:
        """Return stable tool-error counts without unbounded labels."""

        with self._lock:
            return dict(sorted(self._error_categories.items()))

    def recent_logs(self, limit: int) -> tuple[SafeLogEntry, ...]:
        """Return newest-first bounded log entries."""

        if limit <= 0:
            return ()
        with self._lock:
            return tuple(reversed(tuple(self._logs)[-limit:]))

    def _provider_entry(self, provider: str) -> _ProviderUsage:
        return self._provider_usage.setdefault(provider, _ProviderUsage())

    def _append(
        self,
        *,
        level: SafeLogLevel,
        source: str,
        event: str,
        component: str | None = None,
        status: str | None = None,
        latency_ms: float | None = None,
        request_id: str | None = None,
        error_category: str | None = None,
    ) -> None:
        entry = SafeLogEntry(
            timestamp=datetime.now(UTC),
            level=level,
            source=source,
            event=event,
            component=component,
            status=status,
            latency_ms=latency_ms,
            request_id=request_id,
            error_category=error_category,
        )
        with self._lock:
            self._logs.append(entry)
