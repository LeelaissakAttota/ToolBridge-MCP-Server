"""Composition helpers for the MCP core and managed runtime."""

from dataclasses import dataclass

from toolbridge.config import Settings
from toolbridge.core.executor import ToolExecutor
from toolbridge.core.ports import (
    CompositeExecutionEventLogger,
    ExecutionEventLogger,
)
from toolbridge.core.registry import ToolRegistry
from toolbridge.core.validation import RequestValidator, ResponseValidator
from toolbridge.providers.application.ports import ProviderEventLogger
from toolbridge.providers.application.router import ProviderRouter
from toolbridge.providers.infrastructure.factory import build_provider_router
from toolbridge.tools.application.manager import ToolManager
from toolbridge.tools.application.metrics import InMemoryToolMetrics
from toolbridge.tools.application.ports import StockProviderEventLogger
from toolbridge.tools.infrastructure.phase5_factory import build_phase5_managed_tools


@dataclass(frozen=True, slots=True)
class CoreRuntime:
    """Application services composed for one server process."""

    registry: ToolRegistry
    executor: ToolExecutor
    provider_router: ProviderRouter
    tool_manager: ToolManager
    tool_metrics: InMemoryToolMetrics


def build_core_runtime(
    settings: Settings,
    event_logger: ExecutionEventLogger,
    provider_event_logger: ProviderEventLogger | None = None,
    stock_event_logger: StockProviderEventLogger | None = None,
) -> CoreRuntime:
    """Build the MCP Core, provider router, and approved managed tools."""

    registry = ToolRegistry()
    metrics = InMemoryToolMetrics()
    provider_router = build_provider_router(settings, provider_event_logger)
    tools = build_phase5_managed_tools(
        settings,
        provider_router,
        stock_event_logger,
    )
    tool_manager = ToolManager(tools, metrics)
    tool_manager.register_all(registry)
    observers = CompositeExecutionEventLogger((event_logger, metrics))
    executor = ToolExecutor(
        registry=registry,
        request_validator=RequestValidator(settings.max_request_bytes),
        response_validator=ResponseValidator(settings.max_response_bytes),
        event_logger=observers,
    )
    return CoreRuntime(
        registry=registry,
        executor=executor,
        provider_router=provider_router,
        tool_manager=tool_manager,
        tool_metrics=metrics,
    )
