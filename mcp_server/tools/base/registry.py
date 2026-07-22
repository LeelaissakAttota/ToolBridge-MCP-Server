"""Tool Registry for dynamic tool management.

Provides thread-safe tool registration, lookup, and management.
"""

import logging
import threading
from typing import Any

from mcp_server.tools.base.metadata import ToolMetadata
from mcp_server.tools.base.tool import BaseTool

logger = logging.getLogger(__name__)


class ToolRegistry:
    """Thread-safe registry for MCP tools.

    Supports dynamic registration, unregistration, and lookup of tools.
    All operations are thread-safe.
    """

    def __init__(self):
        """Initialize empty tool registry."""
        self._tools: dict[str, BaseTool] = {}
        self._lock = threading.RLock()
        logger.debug("ToolRegistry initialized")

    def register_tool(self, tool: BaseTool) -> None:
        """Register a tool in the registry.

        Validates the tool and stores it with metadata.

        Args:
            tool: BaseTool instance to register.

        Raises:
            ValueError: If tool name already registered.
            TypeError: If tool is not a BaseTool instance.
        """
        if not isinstance(tool, BaseTool):
            raise TypeError(f"Tool must be BaseTool instance, got {type(tool).__name__}")

        name = tool.name
        with self._lock:
            if name in self._tools:
                raise ValueError(f"Tool '{name}' already registered")

            self._tools[name] = tool
            logger.info(f"Registered tool: {name} v{tool.version}")

    def unregister_tool(self, name: str) -> None:
        """Unregister a tool by name.

        Args:
            name: Name of tool to unregister.

        Raises:
            KeyError: If tool not found.
        """
        with self._lock:
            if name not in self._tools:
                raise KeyError(f"Tool '{name}' not found")

            del self._tools[name]
            logger.info(f"Unregistered tool: {name}")

    def get_tool(self, name: str) -> BaseTool | None:
        """Get a tool by name.

        Args:
            name: Tool name.

        Returns:
            Tool instance or None if not found.
        """
        with self._lock:
            return self._tools.get(name)

    def get_metadata(self, name: str) -> ToolMetadata | None:
        """Get tool metadata by name.

        Args:
            name: Tool name.

        Returns:
            ToolMetadata or None if not found.
        """
        tool = self.get_tool(name)
        if tool:
            return tool.get_metadata()
        return None

    def list_tools(self, enabled_only: bool = True) -> list[ToolMetadata]:
        """List all registered tools with metadata.

        Args:
            enabled_only: If True, only return enabled tools.

        Returns:
            List of ToolMetadata objects.
        """
        with self._lock:
            tools = []
            for tool in self._tools.values():
                if not enabled_only or True:  # All tools enabled by default
                    tools.append(tool.get_metadata())
            return tools

    def list_tool_names(self) -> list[str]:
        """Get list of all registered tool names.

        Returns:
            Sorted list of tool names.
        """
        with self._lock:
            return sorted(self._tools.keys())

    def validate_tool(self, name: str) -> tuple[bool, list[str]]:
        """Validate a registered tool's schema and structure.

        Args:
            name: Tool name.

        Returns:
            Tuple of (is_valid, error_messages).
        """
        tool = self.get_tool(name)
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

        # Validate execute method
        if not hasattr(tool, "execute") or not callable(tool.execute):
            errors.append("Tool missing callable execute method")

        return len(errors) == 0, errors

    def has_tool(self, name: str) -> bool:
        """Check if a tool is registered.

        Args:
            name: Tool name.

        Returns:
            True if registered.
        """
        with self._lock:
            return name in self._tools

    def is_enabled(self, name: str) -> bool:
        """Check if a tool is enabled (always True for now).

        Args:
            name: Tool name.

        Returns:
            True if tool exists (all tools enabled).
        """
        return self.has_tool(name)

    def enable_tool(self, name: str) -> None:
        """Enable a tool (no-op, kept for compatibility)."""
        if not self.has_tool(name):
            raise KeyError(f"Tool '{name}' not found")
        logger.debug(f"Tool {name} enabled")

    def disable_tool(self, name: str) -> None:
        """Disable a tool (no-op, kept for compatibility)."""
        if not self.has_tool(name):
            raise KeyError(f"Tool '{name}' not found")
        logger.debug(f"Tool {name} disabled")

    def clear(self) -> None:
        """Remove all tools from registry."""
        with self._lock:
            count = len(self._tools)
            self._tools.clear()
            logger.info(f"Cleared registry: removed {count} tools")

    def __len__(self) -> int:
        """Return number of registered tools."""
        with self._lock:
            return len(self._tools)

    def __contains__(self, name: str) -> bool:
        """Check if tool name exists in registry."""
        return self.has_tool(name)

    def __iter__(self):
        """Iterate over tool names."""
        with self._lock:
            return iter(self._tools.keys())

    def __repr__(self) -> str:
        return f"<ToolRegistry tools={len(self._tools)}>"