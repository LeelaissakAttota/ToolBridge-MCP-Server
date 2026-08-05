"""Composition helpers for the MCP core runtime."""

from dataclasses import dataclass

from toolbridge.config import Settings
from toolbridge.core.executor import ToolExecutor
from toolbridge.core.ports import ExecutionEventLogger
from toolbridge.core.registry import ToolRegistry
from toolbridge.core.validation import RequestValidator, ResponseValidator
from toolbridge.tools.definitions import system_status_definition


@dataclass(frozen=True, slots=True)
class CoreRuntime:
    """Application services composed for one server process."""

    registry: ToolRegistry
    executor: ToolExecutor


def build_core_runtime(
    settings: Settings,
    event_logger: ExecutionEventLogger,
) -> CoreRuntime:
    """Build the approved Phase 2 core with no provider dependencies."""

    registry = ToolRegistry()
    registry.register(system_status_definition(settings.tool_timeout_seconds))
    executor = ToolExecutor(
        registry=registry,
        request_validator=RequestValidator(settings.max_request_bytes),
        response_validator=ResponseValidator(settings.max_response_bytes),
        event_logger=event_logger,
    )
    return CoreRuntime(registry=registry, executor=executor)

