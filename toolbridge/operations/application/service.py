"""Read-only operational snapshots and lifecycle readiness decisions."""

from datetime import UTC, datetime
from threading import Lock
from time import perf_counter

from toolbridge.core.registry import ToolRegistry
from toolbridge.operations.application.metrics import InMemoryOperationalMetrics
from toolbridge.operations.domain.models import (
    CostSummary,
    LifecycleState,
    MetricsSummary,
    OperationsSnapshot,
    ProviderMonitor,
    ReadinessCheck,
    ReadinessSnapshot,
    SystemOverview,
    ToolMonitor,
)
from toolbridge.providers.application.router import ProviderRouter
from toolbridge.providers.domain.models import ProviderName
from toolbridge.tools.application.manager import ToolManager
from toolbridge.tools.domain.models import ToolHealthState, ToolStatusSnapshot

TOOL_DISPLAY_NAMES = {
    "system_status": "System Status",
    "stock_price": "Stock Price",
    "website_reader": "Website Reader",
    "sql_query": "SQL Query",
    "csv_analysis": "CSV Analysis",
    "currency_converter": "Currency Converter",
    "hcl_curie_analysis": "HCL Curie / LLM Analysis",
}


class OperationsService:
    """Coordinate safe monitoring views without owning business resources."""

    def __init__(
        self,
        *,
        version: str,
        environment: str,
        current_phase: str,
        registry: ToolRegistry,
        provider_router: ProviderRouter,
        tool_manager: ToolManager,
        metrics: InMemoryOperationalMetrics,
        provider_priority: tuple[ProviderName, ...],
        enabled_providers: frozenset[ProviderName],
        recent_log_limit: int,
        readiness_require_provider: bool,
        readiness_require_all_tools_healthy: bool,
    ) -> None:
        self._version = version
        self._environment = environment
        self._current_phase = current_phase
        self._registry = registry
        self._provider_router = provider_router
        self._tool_manager = tool_manager
        self._metrics = metrics
        self._provider_priority = provider_priority
        self._enabled_providers = enabled_providers
        self._recent_log_limit = recent_log_limit
        self._readiness_require_provider = readiness_require_provider
        self._readiness_require_all_tools_healthy = (
            readiness_require_all_tools_healthy
        )
        self._started_at = datetime.now(UTC)
        self._started_counter = perf_counter()
        self._lifecycle = LifecycleState.STARTING
        self._state_lock = Lock()

    @property
    def metrics(self) -> InMemoryOperationalMetrics:
        """Expose the shared safe observer to the composition root."""

        return self._metrics

    def validate_startup(self) -> None:
        """Reject an incomplete local composition before accepting traffic."""

        expected = len(self._tool_manager.tools)
        if expected <= 0 or len(self._registry) != expected:
            self.mark_failed("registry_validation")
            raise RuntimeError("startup validation failed")
        if not self._version.strip():
            self.mark_failed("version_validation")
            raise RuntimeError("startup validation failed")
        self._metrics.record_system(
            event="startup_validation_completed",
            status="succeeded",
        )

    def mark_ready(self) -> None:
        """Mark startup complete after every managed lifespan is active."""

        self._set_lifecycle(LifecycleState.READY)
        self._metrics.record_system(event="service_ready", status="ready")

    def mark_stopping(self) -> None:
        """Make readiness fail before managed resources begin closing."""

        self._set_lifecycle(LifecycleState.STOPPING)
        self._metrics.record_system(event="service_stopping", status="stopping")

    def mark_stopped(self) -> None:
        """Record successful completion of graceful shutdown."""

        self._set_lifecycle(LifecycleState.STOPPED)
        self._metrics.record_system(event="service_stopped", status="stopped")

    def mark_failed(self, error_category: str) -> None:
        """Record a safe categorized lifecycle failure."""

        self._set_lifecycle(LifecycleState.FAILED)
        self._metrics.record_system(
            event="service_lifecycle_failed",
            status="failed",
            error_category=error_category,
        )

    def readiness(self) -> ReadinessSnapshot:
        """Evaluate local readiness without network, database, or file probes."""

        tool_statuses = self._tool_manager.monitoring_statuses()
        lifecycle = self._lifecycle_value()
        checks = [
            ReadinessCheck(
                name="lifecycle",
                ready=lifecycle is LifecycleState.READY,
                status=lifecycle.value,
            ),
            ReadinessCheck(
                name="registry",
                ready=(
                    len(self._registry) > 0
                    and len(self._registry) == len(self._tool_manager.tools)
                ),
                status=f"{len(self._registry)} tools registered",
            ),
            ReadinessCheck(
                name="tool_lifecycle",
                ready=self._tool_manager.is_initialized,
                status=(
                    "initialized"
                    if self._tool_manager.is_initialized
                    else "not_initialized"
                ),
            ),
            ReadinessCheck(
                name="provider_router",
                ready=self._provider_router.is_initialized,
                status=(
                    "initialized"
                    if self._provider_router.is_initialized
                    else "not_initialized"
                ),
            ),
        ]
        if self._readiness_require_provider:
            checks.append(
                ReadinessCheck(
                    name="active_provider",
                    ready=self._provider_router.active_provider is not None,
                    status=(
                        self._provider_router.active_provider.value
                        if self._provider_router.active_provider is not None
                        else "unavailable"
                    ),
                )
            )
        if self._readiness_require_all_tools_healthy:
            all_healthy = all(
                item.health.status is ToolHealthState.HEALTHY
                for item in tool_statuses
            )
            checks.append(
                ReadinessCheck(
                    name="tool_health",
                    ready=all_healthy,
                    status="healthy" if all_healthy else "degraded",
                )
            )
        ready = all(check.ready for check in checks)
        return ReadinessSnapshot(
            status="ready" if ready else "not_ready",
            ready=ready,
            checked_at=datetime.now(UTC),
            checks=tuple(checks),
        )

    def snapshot(self) -> OperationsSnapshot:
        """Build the complete bounded dashboard payload."""

        readiness = self.readiness()
        providers = self._provider_monitors()
        tool_statuses = self._tool_manager.monitoring_statuses()
        tools = self._tool_monitors(tool_statuses)
        total_requests = sum(
            item.metrics.total_executions for item in tool_statuses
        )
        completed = sum(
            item.metrics.successful_executions + item.metrics.failed_executions
            for item in tool_statuses
        )
        total_duration = sum(
            item.metrics.average_duration_ms
            * (item.metrics.successful_executions + item.metrics.failed_executions)
            for item in tool_statuses
        )
        successful = sum(
            item.metrics.successful_executions for item in tool_statuses
        )
        failed = sum(item.metrics.failed_executions for item in tool_statuses)
        provider_usage = {item.provider: item.requests for item in providers}
        tool_usage = {item.tool_name: item.execution_count for item in tools}
        estimated_tokens = sum(item.total_tokens for item in providers)
        estimated_cost = round(sum(item.estimated_cost_usd for item in providers), 8)
        lifecycle = self._lifecycle_value()
        health_status = "healthy" if readiness.ready else "not_ready"
        if readiness.ready and any(
            item.health
            in {ToolHealthState.DEGRADED.value, ToolHealthState.UNAVAILABLE.value}
            for item in tools
        ):
            health_status = "degraded"
        return OperationsSnapshot(
            system=SystemOverview(
                version=self._version,
                uptime_seconds=round(perf_counter() - self._started_counter, 3),
                environment=self._environment,
                current_phase=self._current_phase,
                health_status=health_status,
                lifecycle=lifecycle,
                started_at=self._started_at,
            ),
            readiness=readiness,
            providers=providers,
            tools=tools,
            metrics=MetricsSummary(
                total_requests=total_requests,
                successful_requests=successful,
                failed_requests=failed,
                error_categories=self._metrics.error_categories(),
                average_response_time_ms=(
                    round(total_duration / completed, 3) if completed else 0.0
                ),
                provider_usage=provider_usage,
                tool_usage=tool_usage,
            ),
            costs=CostSummary(
                estimated_token_usage=estimated_tokens,
                estimated_api_cost_usd=estimated_cost,
                requests_per_provider=provider_usage,
                cost_per_provider={
                    item.provider: item.estimated_cost_usd for item in providers
                },
            ),
            logs=self._metrics.recent_logs(self._recent_log_limit),
        )

    def _provider_monitors(self) -> tuple[ProviderMonitor, ...]:
        statuses = {
            item.provider: item for item in self._provider_router.provider_status()
        }
        active = self._provider_router.active_provider
        enabled_order = tuple(
            name for name in self._provider_priority if name in self._enabled_providers
        )
        failover_active = active is not None and (
            not enabled_order or active is not enabled_order[0]
        )
        values: list[ProviderMonitor] = []
        for priority, provider in enumerate(self._provider_priority, start=1):
            status = statuses.get(provider)
            usage = self._metrics.provider_usage(provider)
            values.append(
                ProviderMonitor(
                    provider=provider.value,
                    configured=provider in self._enabled_providers,
                    priority=priority,
                    status=status.status.value if status is not None else "disabled",
                    active=provider is active,
                    failover_active=failover_active and provider is active,
                    response_latency_ms=(
                        usage.average_latency_ms
                        if usage.average_latency_ms > 0
                        else (status.latency_ms if status is not None else None)
                    ),
                    last_successful_request=(
                        status.last_successful_request if status is not None else None
                    ),
                    last_failed_request=(
                        status.last_failed_request if status is not None else None
                    ),
                    error_category=(
                        status.last_error_category.value
                        if status is not None
                        and status.last_error_category is not None
                        else None
                    ),
                    requests=usage.requests,
                    total_tokens=usage.total_tokens,
                    estimated_cost_usd=usage.estimated_cost_usd,
                )
            )
        return tuple(values)

    def _tool_monitors(
        self,
        statuses: tuple[ToolStatusSnapshot, ...],
    ) -> tuple[ToolMonitor, ...]:
        registered = {item.name for item in self._registry.discover()}
        return tuple(
            ToolMonitor(
                tool_name=item.health.tool_name,
                display_name=TOOL_DISPLAY_NAMES.get(
                    item.health.tool_name,
                    item.health.tool_name.replace("_", " ").title(),
                ),
                registered=item.health.tool_name in registered,
                health=item.health.status.value,
                execution_count=item.metrics.total_executions,
                average_response_time_ms=item.metrics.average_duration_ms,
                last_execution=item.metrics.last_execution_at,
            )
            for item in statuses
        )

    def _set_lifecycle(self, value: LifecycleState) -> None:
        with self._state_lock:
            self._lifecycle = value

    def _lifecycle_value(self) -> LifecycleState:
        with self._state_lock:
            return self._lifecycle
