"""Core definitions for the Phase 1 diagnostic tool."""

from datetime import datetime
from typing import Literal

from pydantic import field_validator

from toolbridge.core.contracts import EmptyToolInput, ToolDefinition, ToolOutput
from toolbridge.tools.system import system_status


class SystemStatusOutput(ToolOutput):
    """Validated output contract for `system_status`."""

    service: Literal["toolbridge-mcp"]
    status: Literal["ok"]
    timestamp: str

    @field_validator("timestamp")
    @classmethod
    def validate_timestamp(cls, value: str) -> str:
        """Require an ISO 8601 timestamp while preserving its wire format."""

        datetime.fromisoformat(value.replace("Z", "+00:00"))
        return value


def handle_system_status(_: EmptyToolInput) -> SystemStatusOutput:
    """Adapt the existing diagnostic function to the core contracts."""

    return SystemStatusOutput.model_validate(system_status(), strict=True)


def system_status_definition(timeout_seconds: float) -> ToolDefinition:
    """Build the stable definition for the diagnostic tool."""

    return ToolDefinition(
        name="system_status",
        description="Return the current ToolBridge service status.",
        input_model=EmptyToolInput,
        output_model=SystemStatusOutput,
        handler=handle_system_status,
        timeout_seconds=timeout_seconds,
    )
