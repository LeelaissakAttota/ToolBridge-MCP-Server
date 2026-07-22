"""Base tool class for all MCP tools.

All tools must inherit from BaseTool and implement required methods.
Provides schema validation, execution wrapper, and metadata management.
"""

from __future__ import annotations

import logging
import time
from abc import ABC, abstractmethod
from typing import Any

from mcp_server.mcp_core.errors import ToolExecutionError, ToolValidationError
from mcp_server.tools.base.metadata import ToolMetadata

logger = logging.getLogger(__name__)


class BaseTool(ABC):
    """Abstract base class for all MCP tools.

    All tools must inherit from this class and implement:
    - name: Unique tool identifier
    - description: Human-readable description
    - get_input_schema(): JSON Schema for input validation
    - execute(): Core tool logic

    Optional:
    - get_output_schema(): JSON Schema for output (for structured output)
    - annotations: MCP tool annotations
    - tags: Categorization tags
    - version: Tool version
    - author: Tool author
    """

    # Class-level attributes (override in subclasses)
    name: str = ""
    description: str = ""
    tags: list[str] = []
    version: str = "1.0.0"
    author: str = "ToolBridge"
    annotations: dict[str, Any] | None = None

    def __init_subclass__(cls, **kwargs):
        """Validate subclass on creation."""
        super().__init_subclass__(**kwargs)
        if not cls.name:
            raise TypeError(f"Tool class {cls.__name__} must define 'name' attribute")
        if not cls.description:
            raise TypeError(f"Tool class {cls.__name__} must define 'description' attribute")

    def __init__(self, config: dict[str, Any] | None = None):
        """Initialize tool instance.

        Args:
            config: Optional tool-specific configuration.
        """
        self.config = config or {}
        self._input_schema: dict[str, Any] | None = None
        self._output_schema: dict[str, Any] | None = None
        logger.debug(f"Initialized tool: {self.name}")

    @abstractmethod
    def get_input_schema(self) -> dict[str, Any]:
        """Get JSON Schema for tool input parameters.

        Returns:
            Dictionary representing JSON Schema for input validation.

        Example:
            {
                "type": "object",
                "properties": {
                    "param1": {"type": "string", "description": "First parameter"},
                    "param2": {"type": "integer", "minimum": 0}
                },
                "required": ["param1"],
                "additionalProperties": False
            }
        """
        pass

    def get_output_schema(self) -> dict[str, Any] | None:
        """Get JSON Schema for tool output (optional).

        Returns:
            Dictionary representing JSON Schema for output validation,
            or None if output is unstructured.
        """
        return {"type": "object", "properties": {}, "additionalProperties": True}

    @abstractmethod
    async def execute(self, arguments: dict[str, Any]) -> Any:
        """Execute the tool with validated arguments.

        This method contains the core tool logic. Input arguments
        have already been validated against the input schema.

        Args:
            arguments: Validated input arguments.

        Returns:
            Tool execution result (any JSON-serializable value).

        Raises:
            ToolExecutionError: If execution fails.
        """
        pass

    async def execute_async(self, arguments: dict[str, Any]) -> Any:
        """Execute the tool asynchronously.

        Default implementation calls synchronous execute(). Override
        for true async execution.

        Args:
            arguments: Validated input arguments.

        Returns:
            Tool execution result.
        """
        return await self.execute(arguments)

    def validate_arguments(self, arguments: Any) -> tuple[bool, str | None]:
            """Validate input arguments against schema.

            Args:
                arguments: Raw input arguments.

            Returns:
                Tuple of (is_valid, error_message).
            """
            if not isinstance(arguments, dict):
                return False, "Arguments must be a dictionary"

            schema = self.get_input_schema()
            try:
                import jsonschema
                jsonschema.validate(arguments, schema)
            except ImportError:
                # jsonschema not available, skip validation
                logger.warning("jsonschema not installed, skipping input validation")
            except Exception as e:
                # Extract a clean error message
                error_msg = getattr(e, 'message', str(e))
                if 'is a required property' in str(e):
                    # Extract the property name from the error
                    import re
                    match = re.search(r"'([^']+)' is a required property", str(e))
                    if match:
                        return False, f"Missing required argument: {match.group(1)}"
                return False, f"Input validation failed: {error_msg}"
            return True, None

    def validate_output(self, result: Any) -> Any:
        """Validate output result against schema (if defined).

        Args:
            result: Tool execution result.

        Returns:
            Validated result.

        Raises:
            ToolValidationError: If validation fails.
        """
        schema = self.get_output_schema()
        if schema is None:
            return result

        try:
            import jsonschema
            jsonschema.validate(result, schema)
        except ImportError:
            logger.warning("jsonschema not installed, skipping output validation")
        except Exception as e:
            raise ToolValidationError(
                self.name,
                f"Output validation failed: {e.message}",
                data={"path": list(e.path), "schema_path": list(e.schema_path)},
            ) from e
        return result

    async def validate_and_execute(self, arguments: dict[str, Any]) -> Any:
        """Validate input, execute, and validate output.

        This is the main entry point for tool execution.

        Args:
            arguments: Raw input arguments.

        Returns:
            Validated execution result.

        Raises:
            ToolValidationError: If input/output validation fails.
            ToolExecutionError: If execution fails.
        """
        start_time = time.perf_counter()
        logger.info(f"Tool {self.name} execution started")

        # Validate input
        self.validate_arguments(arguments)

        try:
            # Execute (async)
            result = await self.execute_async(arguments)

            # Validate output
            result = self.validate_output(result)

            elapsed = time.perf_counter() - start_time
            logger.info(f"Tool {self.name} completed in {elapsed:.3f}s")
            return result

        except ToolValidationError:
            raise
        except ToolExecutionError:
            raise
        except Exception as e:
            elapsed = time.perf_counter() - start_time
            logger.error(f"Tool {self.name} failed after {elapsed:.3f}s: {e}")
            raise ToolExecutionError(
                self.name,
                f"Execution failed: {e}",
                data={"elapsed_seconds": elapsed},
            ) from e

    def get_metadata(self) -> ToolMetadata:
        """Get tool metadata for registry.

        Returns:
            ToolMetadata instance.
        """
        return ToolMetadata(
            name=self.name,
            description=self.description,
            input_schema=self.get_input_schema(),
            output_schema=self.get_output_schema(),
            annotations=self.annotations,
            tags=self.tags,
            version=self.version,
            author=self.author,
        )

    def to_mcp_tool(self) -> dict[str, Any]:
        """Convert to MCP tool format for tools/list endpoint.

        Returns:
            Dictionary matching MCP Tool schema.
        """
        return {
            "name": self.name,
            "description": self.description,
            "inputSchema": self.get_input_schema(),
            "outputSchema": self.get_output_schema(),
        }

    def __repr__(self) -> str:
        return f"<Tool {self.name} v{self.version}>"