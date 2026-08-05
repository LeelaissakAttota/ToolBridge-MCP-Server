"""Composition helpers for the MCP core and provider router runtime."""

from dataclasses import dataclass

from toolbridge.config import Settings
from toolbridge.core.executor import ToolExecutor
from toolbridge.core.ports import ExecutionEventLogger
from toolbridge.core.registry import ToolRegistry
from toolbridge.core.validation import RequestValidator, ResponseValidator
from toolbridge.providers.application.ports import ProviderEventLogger
from toolbridge.providers.application.router import ProviderRouter
from toolbridge.providers.infrastructure.factory import build_provider_router
from toolbridge.tools.definitions import system_status_definition


@dataclass(frozen=True, slots=True)
class CoreRuntime:
    """Application services composed for one server process."""

    registry: ToolRegistry
    executor: ToolExecutor
    provider_router: ProviderRouter


def build_core_runtime(
    settings: Settings,
    event_logger: ExecutionEventLogger,
    provider_event_logger: ProviderEventLogger | None = None,
) -> CoreRuntime:
    """Build the approved MCP Core and Phase 3 provider router."""

    registry = ToolRegistry()
    registry.register(system_status_definition(settings.tool_timeout_seconds))
    executor = ToolExecutor(
        registry=registry,
        request_validator=RequestValidator(settings.max_request_bytes),
        response_validator=ResponseValidator(settings.max_response_bytes),
        event_logger=event_logger,
    )
    provider_router = build_provider_router(settings, provider_event_logger)
    return CoreRuntime(
        registry=registry,
        executor=executor,
        provider_router=provider_router,
    )
