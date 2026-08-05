"""Deterministic registry and discovery for MCP tools."""

from toolbridge.core.contracts import ToolDefinition, ToolMetadata
from toolbridge.core.errors import DuplicateToolError, ToolNotFoundError


class ToolRegistry:
    """Store validated tool definitions by unique name."""

    def __init__(self) -> None:
        self._tools: dict[str, ToolDefinition] = {}

    def register(self, definition: ToolDefinition) -> None:
        """Register a definition or reject a duplicate name."""

        if definition.name in self._tools:
            raise DuplicateToolError(definition.name)
        self._tools[definition.name] = definition

    def get(self, tool_name: str) -> ToolDefinition:
        """Return a registered definition or raise a normalized error."""

        try:
            return self._tools[tool_name]
        except KeyError as error:
            raise ToolNotFoundError(tool_name) from error

    def definitions(self) -> tuple[ToolDefinition, ...]:
        """Return definitions in deterministic name order."""

        return tuple(self._tools[name] for name in sorted(self._tools))

    def discover(self) -> tuple[ToolMetadata, ...]:
        """Return validated discovery metadata in deterministic order."""

        return tuple(definition.metadata() for definition in self.definitions())

    def __len__(self) -> int:
        """Return the number of registered tools."""

        return len(self._tools)

