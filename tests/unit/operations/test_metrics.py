"""Tests for bounded metrics, timing, costs, and safe logs."""

from toolbridge.core.contracts import ErrorCode
from toolbridge.operations.application.metrics import InMemoryOperationalMetrics
from toolbridge.providers.domain.models import ProviderName, ProviderStatus


def build_metrics(capacity: int = 10) -> InMemoryOperationalMetrics:
    """Build deterministic operational metrics with configured provider prices."""

    return InMemoryOperationalMetrics(
        log_capacity=capacity,
        provider_costs={ProviderName.CEREBRAS: (1.0, 2.0)},
    )


def test_metrics_aggregate_requests_errors_tokens_costs_and_timings() -> None:
    metrics = build_metrics()

    metrics.started(tool_name="system_status", correlation_id="request-1")
    metrics.succeeded(
        tool_name="system_status",
        correlation_id="request-1",
        duration_ms=4.0,
    )
    metrics.failed(
        tool_name="system_status",
        correlation_id="request-2",
        duration_ms=6.0,
        error_code=ErrorCode.EXECUTION_FAILED,
        exception_type="SensitiveFailure",
    )
    metrics.record(
        provider=ProviderName.CEREBRAS,
        latency_ms=10.0,
        status=ProviderStatus.HEALTHY,
        request_id="provider-request",
    )
    metrics.record_generation(
        provider=ProviderName.CEREBRAS,
        input_tokens=1_000,
        output_tokens=500,
        total_tokens=1_500,
    )

    usage = metrics.provider_usage(ProviderName.CEREBRAS)

    assert usage.requests == 1
    assert usage.total_tokens == 1_500
    assert usage.estimated_cost_usd == 0.002
    assert usage.average_latency_ms == 10.0
    assert metrics.error_categories() == {"execution_failed": 1}
    serialized = str([entry.model_dump(mode="json") for entry in metrics.recent_logs(10)])
    assert "SensitiveFailure" not in serialized


def test_log_buffer_is_bounded_and_newest_first() -> None:
    metrics = build_metrics(capacity=2)

    for index in range(3):
        metrics.record_system(event=f"event-{index}", status="ok")

    logs = metrics.recent_logs(10)

    assert [entry.event for entry in logs] == ["event-2", "event-1"]

