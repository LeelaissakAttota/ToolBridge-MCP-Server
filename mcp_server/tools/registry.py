"""Tool registry for MCP server.

Thread-safe registry for tool registration, lookup, and metadata management.
"""

import logging
import threading
from typing import Any

from mcp_server.tools.base import BaseTool

logger = logging.getLogger(__name__)


class ToolRegistry:
    """Thread-safe tool registry.

    Provides register, unregister, get, list operations with
    built-in validation and metadata tracking.
    """

    def __init__(self) -> None:
        """Initialize empty registry."""
        self._tools: dict[str, BaseTool] = {}
        self._metadata: dict[str, dict[str, Any]] = {}
        self._lock = threading.RLock()
        logger.debug("ToolRegistry initialized")

    def register_tool(self, tool: BaseTool) -> None:
        """Register a tool instance.

        Args:
            tool: Tool instance to register.

        Raises:
            ValueError: If tool name already registered.
            TypeError: If not a BaseTool instance.
        """
        if not isinstance(tool, BaseTool):
            raise TypeError(f"Expected BaseTool, got {type(tool).__name__}")

        with self._lock:
            if tool.name in self._tools:
                raise ValueError(f"Tool '{tool.name}' already registered")

            self._tools[tool.name] = tool
            self._metadata[tool.name] = {
                "description": tool.description,
                "input_schema": tool.get_input_schema(),
                "output_schema": tool.get_output_schema(),
                "registered_at": None,  # Could add timestamp
            }
            logger.debug(f"Registered tool: {tool.name}")

    def unregister_tool(self, name: str) -> None:
        """Unregister a tool by name.

        Args:
            name: Tool name to unregister.

        Raises:
            KeyError: If tool not found.
        """
        with self._lock:
            if name not in self._tools:
                raise KeyError(f"Tool '{name}' not found")

            del self._tools[name]
            del self._metadata[name]
            logger.debug(f"Unregistered tool: {name}")

    def get_tool(self, name: str) -> BaseTool | None:
        """Get a tool by name.

        Args:
            name: Tool name.

        Returns:
            Tool instance or None if not found.
        """
        with self._lock:
            return self._tools.get(name)

    def get_tool_metadata(self, name: str) -> dict[str, Any] | None:
        """Get tool metadata by name.

        Args:
            name: Tool name.

        Returns:
            Metadata dict or None.
        """
        with self._lock:
            return self._metadata.get(name)

    def list_tools(self) -> list[dict[str, Any]]:
        """List all registered tools with metadata.

        Returns:
            List of tool metadata for MCP tools/list response.
        """
        with self._lock:
            return [
                {
                    "name": tool.name,
                    "description": tool.description,
                    "inputSchema": tool.get_input_schema(),
                    "outputSchema": tool.get_output_schema(),
                }
                for tool in self._tools.values()
            ]

    def list_tool_names(self) -> list[str]:
        """List all registered tool names.

        Returns:
            List of tool names.
        """
        with self._lock:
            return list(self._tools.keys())

    def has_tool(self, name: str) -> bool:
        """Check if a tool is registered.

        Args:
            name: Tool name.

        Returns:
            True if registered.
        """
        with self._lock:
            return name in self._tools

    def validate_tool(self, name: str) -> tuple[bool, list[str]]:
        """Validate a registered tool's schema.

        Args:
            name: Tool name.

        Returns:
            Tuple of (is_valid, error_messages).
        """
        with self._lock:
            tool = self._tools.get(name)
            if not tool:
                return False, [f"Tool '{name}' not found"]

        errors = []

        # Validate input schema
        try:
            input_schema = tool.get_input_schema()
            if not isinstance(input_schema, dict):
                errors.append("Input schema must be a dictionary")
            elif "type" not in input_schema:
                errors.append("Input schema missing 'type' field")
        except Exception as e:
            errors.append(f"Input schema error: {e}")

        # Validate output schema
        try:
            output_schema = tool.get_output_schema()
            if output_schema is not None and not isinstance(output_schema, dict):
                errors.append("Output schema must be a dictionary or None")
        except Exception as e:
            errors.append(f"Output schema error: {e}")

        return len(errors) == 0, errors

    def clear(self) -> None:
        """Clear all tools from registry."""
        with self._lock:
            self._tools.clear()
            self._metadata.clear()
            logger.debug("Registry cleared")

    def __len__(self) -> int:
        """Return number of registered tools."""
        with self._lock:
            return len(self._tools)

    def __contains__(self, name: str) -> bool:
        """Check if tool exists."""
        return self.has_tool(name)

    def __iter__(self):
        """Iterate over tool names."""
        with self._lock:
            return iter(self._tools.keys())