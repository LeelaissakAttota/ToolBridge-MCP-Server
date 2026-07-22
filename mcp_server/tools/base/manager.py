"""Tool manager for discovery, loading, validation, and execution."""

import importlib
import logging
import pkgutil
from typing import Any

from mcp_server.mcp_core.errors import ToolExecutionError, ToolNotFoundError, ToolValidationError
from mcp_server.tools.base.registry import ToolRegistry
from mcp_server.tools.base.tool import BaseTool

logger = logging.getLogger(__name__)


class ToolManager:
    """Manages tool lifecycle: discovery, loading, validation, execution.

    Handles:
    - Automatic tool discovery from Python packages
    - Tool registration and validation
    - Tool execution with error handling
    - Integration with ToolRegistry
    """

    def __init__(self, registry: ToolRegistry | None = None):
        """Initialize tool manager.

        Args:
            registry: Optional ToolRegistry instance. Creates new if not provided.
        """
        self.registry = registry or ToolRegistry()
        self._loaded_modules: set[str] = set()
        logger.info("ToolManager initialized")

    def discover_tools(self, package: str) -> list[str]:
        """Discover tool classes in a package.

        Scans the package for modules containing BaseTool subclasses
        and returns their fully qualified names.

        Args:
            package: Package name to scan (e.g., 'mcp_server.tools').

        Returns:
            List of fully qualified tool class names.
        """
        discovered = []
        try:
            pkg = importlib.import_module(package)
        except ImportError as e:
            logger.warning(f"Cannot import package {package}: {e}")
            return discovered

        # Walk package modules
        for importer, modname, ispkg in pkgutil.walk_packages(
            pkg.__path__, pkg.__name__ + "."
        ):
            if ispkg:
                continue  # Skip subpackages for now

            try:
                module = importlib.import_module(modname)
                self._loaded_modules.add(modname)
                # Find BaseTool subclasses
                for attr_name in dir(module):
                    attr = getattr(module, attr_name)
                    if (
                        isinstance(attr, type)
                        and issubclass(attr, BaseTool)
                        and attr is not BaseTool
                    ):
                        fqn = f"{modname}.{attr_name}"
                        discovered.append(fqn)
                        logger.debug(f"Discovered tool: {fqn}")
            except Exception as e:
                logger.warning(f"Failed to scan module {modname}: {e}")

        logger.info(f"Discovered {len(discovered)} tools in {package}")
        return discovered

    def load_tool(self, tool_class_path: str) -> BaseTool:
        """Load and instantiate a tool class from its fully qualified name.

        Args:
            tool_class_path: Fully qualified class name (e.g., 'mcp_server.tools.my_tool.MyTool').

        Returns:
            Instantiated tool object.

        Raises:
            ToolValidationError: If class not found or instantiation fails.
        """
        try:
            module_path, class_name = tool_class_path.rsplit(".", 1)
            module = importlib.import_module(module_path)
            tool_class = getattr(module, class_name)
        except (ImportError, AttributeError, ValueError) as e:
            raise ToolValidationError(
                tool_class_path,
                f"Cannot load tool class: {e}",
                data={"tool_class_path": tool_class_path},
            ) from e

        try:
            tool_instance = tool_class()
        except Exception as e:
            raise ToolValidationError(
                tool_class_path,
                f"Failed to instantiate tool: {e}",
                data={"tool_class_path": tool_class_path},
            ) from e

        logger.info(f"Loaded tool: {tool_class_path}")
        return tool_instance

    def load_and_register(self, tool_class_path: str) -> BaseTool:
        """Load, instantiate, and register a tool.

        Args:
            tool_class_path: Fully qualified class name.

        Returns:
            Registered tool instance.

        Raises:
            ToolValidationError: If loading or registration fails.
        """
        tool = self.load_tool(tool_class_path)
        self.registry.register_tool(tool)
        return tool

    def load_tools_from_package(self, package: str) -> list[BaseTool]:
        """Discover, load, and register all tools from a package.

        Args:
            package: Package name to scan.

        Returns:
            List of loaded tool instances.
        """
        discovered = self.discover_tools(package)
        loaded = []
        for tool_path in discovered:
            try:
                tool = self.load_and_register(tool_path)
                loaded.append(tool)
            except Exception as e:
                logger.error(f"Failed to load tool {tool_path}: {e}")
        return loaded

    def execute_tool(self, name: str, arguments: dict[str, Any]) -> Any:
        """Execute a tool by name with arguments.

        Args:
            name: Tool name.
            arguments: Tool input arguments.

        Returns:
            Tool execution result.

        Raises:
            ToolNotFoundError: If tool not found.
            ToolExecutionError: If execution fails.
            ToolValidationError: If validation fails.
        """
        tool = self.registry.get_tool(name)
        if not tool:
            raise ToolNotFoundError(name)

        logger.info(f"Executing tool: {name}")
        return tool.validate_and_execute(arguments)

    async def execute_tool_async(self, name: str, arguments: dict[str, Any]) -> Any:
        """Execute a tool asynchronously.

        Args:
            name: Tool name.
            arguments: Tool input arguments.

        Returns:
            Tool execution result.

        Raises:
            ToolNotFoundError: If tool not found.
            ToolExecutionError: If execution fails.
            ToolValidationError: If validation fails.
        """
        tool = self.registry.get_tool(name)
        if not tool:
            raise ToolNotFoundError(name)

        logger.info(f"Executing tool async: {name}")
        return await tool.validate_and_execute_async(arguments)

    def list_available_tools(self) -> list[dict[str, Any]]:
        """Get list of available tools in MCP format.

        Returns:
            List of tool dictionaries for tools/list endpoint.
        """
        return [meta.to_mcp_tool() for meta in self.registry.list_tools()]

    def get_tool_info(self, name: str) -> dict[str, Any]:
        """Get detailed tool information.

        Args:
            name: Tool name.

        Returns:
            Tool metadata dictionary.

        Raises:
            ToolNotFoundError: If tool not found.
        """
        metadata = self.registry.get_metadata(name)
        if not metadata:
            raise ToolNotFoundError(name)
        return {
            "name": metadata.name,
            "description": metadata.description,
            "input_schema": metadata.input_schema,
            "output_schema": metadata.output_schema,
            "annotations": metadata.annotations,
            "tags": metadata.tags,
            "version": metadata.version,
            "author": metadata.author,
        }

    def validate_tool_schema(self, name: str) -> bool:
        """Validate a tool's schema is well-formed.

        Args:
            name: Tool name.

        Returns:
            True if valid.

        Raises:
            ToolNotFoundError: If tool not found.
            ToolValidationError: If schema invalid.
        """
        tool = self.registry.get_tool(name)
        if not tool:
            raise ToolNotFoundError(name)

        try:
            import json
            json.dumps(tool.get_input_schema())
            if tool.get_output_schema():
                json.dumps(tool.get_output_schema())
            return True
        except Exception as e:
            raise ToolValidationError(
                name,
                f"Schema validation failed: {e}",
            ) from e

    def unload_tool(self, name: str) -> None:
        """Unregister and unload a tool.

        Args:
            name: Tool name to unload.

        Raises:
            ToolNotFoundError: If tool not found.
        """
        self.registry.unregister_tool(name)
        logger.info(f"Unloaded tool: {name}")

    def get_registry(self) -> ToolRegistry:
        """Get the underlying tool registry.

        Returns:
            ToolRegistry instance.
        """
        return self.registry