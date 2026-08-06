"""Managed wrapper for deterministic definition-backed tools."""

from datetime import UTC, datetime

from toolbridge.core.contracts import ToolDefinition
from toolbridge.tools.application.ports import BaseTool
from toolbridge.tools.domain.models import ToolHealthState, ToolHealthStatus


class DefinitionTool(BaseTool):
    """Apply the common lifecycle to a tool with no external resources."""

    def __init__(self, definition: ToolDefinition) -> None:
        self._definition = definition
        self._state = ToolHealthState.UNINITIALIZED
        self._last_success_at: datetime | None = None

    @property
    def definition(self) -> ToolDefinition:
        """Return the wrapped immutable definition."""

        return self._definition

    async def initialize(self) -> None:
        """Mark the deterministic tool ready."""

        self._state = ToolHealthState.HEALTHY
        self._last_success_at = datetime.now(UTC)

    async def health_check(self) -> ToolHealthStatus:
        """Return local lifecycle health without external I/O."""

        return ToolHealthStatus(
            tool_name=self._definition.name,
            status=self._state,
            checked_at=datetime.now(UTC),
            last_success_at=self._last_success_at,
        )

    async def close(self) -> None:
        """Mark the deterministic tool closed."""

        self._state = ToolHealthState.CLOSED
