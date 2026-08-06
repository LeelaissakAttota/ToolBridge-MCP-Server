"""Composition helpers for the MCP core and managed runtime."""

from dataclasses import dataclass

from toolbridge import __version__
from toolbridge.config import Settings
from toolbridge.core.executor import ToolExecutor
from toolbridge.core.ports import (
    CompositeExecutionEventLogger,
    ExecutionEventLogger,
)
from toolbridge.core.registry import ToolRegistry
from toolbridge.core.validation import RequestValidator, ResponseValidator
from toolbridge.operations.application.metrics import InMemoryOperationalMetrics
from toolbridge.operations.application.service import OperationsService
from toolbridge.providers.application.ports import (
    CompositeProviderEventLogger,
    ProviderEventLogger,
)
from toolbridge.providers.application.router import ProviderRouter
from toolbridge.providers.infrastructure.factory import build_provider_router
from toolbridge.providers.domain.models import ProviderName
from toolbridge.tools.application.manager import ToolManager
from toolbridge.tools.application.metrics import InMemoryToolMetrics
from toolbridge.tools.application.ports import (
    CompositeStockProviderEventLogger,
    StockProviderEventLogger,
)
from toolbridge.tools.infrastructure.phase5_factory import build_phase5_managed_tools


@dataclass(frozen=True, slots=True)
class CoreRuntime:
    """Application services composed for one server process."""

    registry: ToolRegistry
    executor: ToolExecutor
    provider_router: ProviderRouter
    tool_manager: ToolManager
    tool_metrics: InMemoryToolMetrics
    operations: OperationsService


def build_core_runtime(
    settings: Settings,
    event_logger: ExecutionEventLogger,
    provider_event_logger: ProviderEventLogger | None = None,
    stock_event_logger: StockProviderEventLogger | None = None,
) -> CoreRuntime:
    """Build the MCP Core, provider router, and approved managed tools."""

    registry = ToolRegistry()
    metrics = InMemoryToolMetrics()
    provider_costs = {
        ProviderName.CEREBRAS: (
            settings.cerebras.input_cost_per_million_tokens_usd,
            settings.cerebras.output_cost_per_million_tokens_usd,
        ),
        ProviderName.NVIDIA: (
            settings.nvidia.input_cost_per_million_tokens_usd,
            settings.nvidia.output_cost_per_million_tokens_usd,
        ),
        ProviderName.OPENROUTER: (
            settings.openrouter.input_cost_per_million_tokens_usd,
            settings.openrouter.output_cost_per_million_tokens_usd,
        ),
    }
    operational_metrics = InMemoryOperationalMetrics(
        log_capacity=settings.operations.log_capacity,
        provider_costs=provider_costs,
    )
    provider_observers = (operational_metrics,)
    if provider_event_logger is not None:
        provider_observers = (provider_event_logger, operational_metrics)
    provider_router = build_provider_router(
        settings,
        CompositeProviderEventLogger(provider_observers),
        operational_metrics,
    )
    stock_observers = (operational_metrics,)
    if stock_event_logger is not None:
        stock_observers = (stock_event_logger, operational_metrics)
    tools = build_phase5_managed_tools(
        settings,
        provider_router,
        CompositeStockProviderEventLogger(stock_observers),
    )
    tool_manager = ToolManager(tools, metrics)
    tool_manager.register_all(registry)
    observers = CompositeExecutionEventLogger((event_logger, metrics, operational_metrics))
    executor = ToolExecutor(
        registry=registry,
        request_validator=RequestValidator(settings.max_request_bytes),
        response_validator=ResponseValidator(settings.max_response_bytes),
        event_logger=observers,
    )
    enabled_providers = frozenset(
        name
        for name, configured in {
            ProviderName.CEREBRAS: settings.cerebras,
            ProviderName.NVIDIA: settings.nvidia,
            ProviderName.OPENROUTER: settings.openrouter,
        }.items()
        if configured.enabled
    )
    operations = OperationsService(
        version=__version__,
        environment=settings.environment,
        current_phase=settings.operations.current_phase,
        registry=registry,
        provider_router=provider_router,
        tool_manager=tool_manager,
        metrics=operational_metrics,
        provider_priority=settings.provider_priority_order,
        enabled_providers=enabled_providers,
        recent_log_limit=settings.operations.recent_log_limit,
        readiness_require_provider=settings.operations.readiness_require_provider,
        readiness_require_all_tools_healthy=(
            settings.operations.readiness_require_all_tools_healthy
        ),
    )
    return CoreRuntime(
        registry=registry,
        executor=executor,
        provider_router=provider_router,
        tool_manager=tool_manager,
        tool_metrics=metrics,
        operations=operations,
    )
