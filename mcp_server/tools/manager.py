"""Tool manager for MCP server.

Handles tool discovery, loading, validation, and execution.
"""

import importlib
import importlib.util
import logging
from pathlib import Path
from typing import Any

from mcp_server.tools.base import BaseTool
from mcp_server.tools.registry import ToolRegistry
from mcp_server.validation import ToolSchemaValidator

logger = logging.getLogger(__name__)


class ToolManager:
    """Manages tool lifecycle: discovery, loading, validation, execution.

    Integrates with ToolRegistry for storage and provides
    high-level tool management operations.
    """

    def __init__(self, registry: ToolRegistry | None = None) -> None:
        """Initialize tool manager.

        Args:
            registry: Optional existing registry. Creates new if None.
        """
        self.registry = registry or ToolRegistry()
        self.validator = ToolSchemaValidator()
        self._loaded_modules: dict[str, Any] = {}
        logger.info("ToolManager initialized")

    def discover_tools(self, path: str | Path) -> list[str]:
        """Discover tool modules in a directory.

        Args:
            path: Directory path to scan for tool modules.

        Returns:
            List of discovered module names.
        """
        path = Path(path)
        if not path.exists():
            logger.warning(f"Tool discovery path does not exist: {path}")
            return []

        modules = []
        for py_file in path.rglob("*.py"):
            if py_file.name.startswith("_"):
                continue
            # Convert path to module name
            rel_path = py_file.relative_to(path.parent if path.parent.name == "tools" else path)
            module_name = str(rel_path.with_suffix("")).replace("/", ".")
            modules.append(module_name)

        logger.info(f"Discovered {len(modules)} potential tool modules in {path}")
        return modules

    def load_tool_module(self, module_name: str) -> list[BaseTool]:
        """Load tool classes from a module.

        Args:
            module_name: Fully qualified module name.

        Returns:
            List of instantiated BaseTool subclasses found.
        """
        if module_name in self._loaded_modules:
            logger.debug(f"Module already loaded: {module_name}")
            return []

        try:
            module = importlib.import_module(module_name)
            self._loaded_modules[module_name] = module
        except Exception as e:
            logger.error(f"Failed to load module {module_name}: {e}")
            return []

        tools = []
        for attr_name in dir(module):
            attr = getattr(module, attr_name)
            if (
                isinstance(attr, type)
                and issubclass(attr, BaseTool)
                and attr is not BaseTool
            ):
                try:
                    tool_instance = attr()
                    tools.append(tool_instance)
                    logger.debug(f"Found tool class: {attr_name} in {module_name}")
                except Exception as e:
                    logger.error(f"Failed to instantiate {attr_name}: {e}")

        logger.info(f"Loaded {len(tools)} tools from {module_name}")
        return tools

    def load_tools_from_path(self, path: str | Path) -> list[BaseTool]:
        """Discover and load all tools from a directory.

        Args:
            path: Directory containing tool modules.

        Returns:
            List of all loaded tool instances.
        """
        all_tools = []
        modules = self.discover_tools(path)

        for module_name in modules:
            tools = self.load_tool_module(module_name)
            all_tools.extend(tools)

        return all_tools

    def register_tool(self, tool: BaseTool) -> None:
        """Register a tool instance.

        Args:
            tool: Tool instance to register.

        Raises:
            ValueError: If tool name conflicts.
            TypeError: If not a BaseTool.
        """
        self.registry.register_tool(tool)
        logger.info(f"Tool registered: {tool.name}")

    def register_tools(self, tools: list[BaseTool]) -> None:
        """Register multiple tools.

        Args:
            tools: List of tool instances.
        """
        for tool in tools:
            self.register_tool(tool)

    def validate_tool(self, name: str) -> tuple[bool, list[str]]:
        """Validate a registered tool.

        Args:
            name: Tool name.

        Returns:
            Tuple of (is_valid, error_messages).
        """
        return self.registry.validate_tool(name)

    def validate_all_tools(self) -> dict[str, tuple[bool, list[str]]]:
        """Validate all registered tools.

        Returns:
            Dict mapping tool name to (is_valid, errors).
        """
        results = {}
        for name in self.registry.list_tool_names():
            results[name] = self.validate_tool(name)
        return results

    async def execute_tool(
        self,
        name: str,
        arguments: dict[str, Any],
    ) -> Any:
        """Execute a tool by name with arguments.

        Args:
            name: Tool name.
            arguments: Input arguments.

        Returns:
            Tool execution result.

        Raises:
            KeyError: If tool not found.
            ToolExecutionError: On execution failure.
        """
        tool = self.registry.get_tool(name)
        if not tool:
            raise KeyError(f"Tool '{name}' not found")

        # Validate arguments
        is_valid, error = tool.validate_arguments(arguments)
        if not is_valid:
            from mcp_server.exceptions import InvalidParams
            raise InvalidParams(f"Invalid arguments for {name}: {error}")

        # Execute
        logger.info(f"Executing tool: {name} with args: {arguments}")
        try:
            result = await tool.execute(arguments)
            logger.debug(f"Tool {name} completed successfully")
            return result
        except Exception as e:
            logger.error(f"Tool {name} execution failed: {e}")
            from mcp_server.exceptions import ToolExecutionError
            raise ToolExecutionError(f"Tool execution failed: {e}") from e

    def get_tool(self, name: str) -> BaseTool | None:
        """Get a tool by name.

        Args:
            name: Tool name.

        Returns:
            Tool instance or None.
        """
        return self.registry.get_tool(name)

    def get_tool_info(self, name: str) -> dict[str, Any] | None:
        """Get tool metadata by name.

        Args:
            name: Tool name.

        Returns:
            Tool metadata dict or None if not found.
        """
        tool = self.registry.get_tool(name)
        if not tool:
            return None
        return {
            "name": tool.name,
            "description": tool.description,
            "input_schema": tool.get_input_schema(),
            "output_schema": tool.get_output_schema(),
            "version": tool.version,
            "tags": tool.tags,
        }

    def list_tools(self) -> list[dict[str, Any]]:
        """List all registered tools with metadata.

        Returns:
            List of tool metadata for tools/list response.
        """
        return self.registry.list_tools()

    def unregister_tool(self, name: str) -> None:
        """Unregister a tool.

        Args:
            name: Tool name.

        Raises:
            KeyError: If tool not found.
        """
        self.registry.unregister_tool(name)

    def get_registry(self) -> ToolRegistry:
        """Get the underlying registry.

        Returns:
            ToolRegistry instance.
        """
        return self.registry

    async def initialize_all(self) -> None:
        """Initialize all registered tools."""
        for tool in self.registry._tools.values():
            if hasattr(tool, "initialize") and callable(tool.initialize):
                await tool.initialize()
        logger.info("All tools initialized")

    async def cleanup_all(self) -> None:
        """Cleanup all registered tools."""
        for tool in self.registry._tools.values():
            if hasattr(tool, "cleanup") and callable(tool.cleanup):
                await tool.cleanup()
        logger.info("All tools cleaned up")

    def __len__(self) -> int:
        """Return number of registered tools."""
        return len(self.registry)

    def __contains__(self, name: str) -> bool:
        """Check if tool is registered."""
        return name in self.registry

    def __repr__(self) -> str:
        return f"<ToolManager tools={len(self.registry)}>"