"""FastMCP adapter for framework-independent ToolBridge tools."""

import inspect
import json
from collections.abc import Callable
from typing import Any

from mcp.server.fastmcp import FastMCP
from mcp.server.fastmcp.exceptions import ToolError

from toolbridge.core.contracts import ToolDefinition
from toolbridge.core.executor import ToolExecutor
from toolbridge.core.registry import ToolRegistry


class MCPToolAdapter:
    """Project registered tools and normalized execution into FastMCP."""

    def __init__(
        self,
        mcp: FastMCP,
        registry: ToolRegistry,
        executor: ToolExecutor,
    ) -> None:
        self._mcp = mcp
        self._registry = registry
        self._executor = executor

    def register_tools(self) -> None:
        """Register every core definition with the MCP transport."""

        for definition in self._registry.definitions():
            self._mcp.add_tool(
                self._build_adapter(definition),
                name=definition.name,
                description=definition.description,
                structured_output=True,
            )
            self._enforce_strict_transport_validation(definition)

    def _enforce_strict_transport_validation(self, definition: ToolDefinition) -> None:
        """Align FastMCP's generated argument model with the strict core contract."""

        registered = self._mcp._tool_manager.get_tool(definition.name)  # type: ignore[attr-defined]
        if registered is None:
            raise RuntimeError(f"FastMCP did not register tool {definition.name!r}")
        argument_model = registered.fn_metadata.arg_model
        argument_model.model_config.update(
            extra="forbid",
            strict=True,
            hide_input_in_errors=True,
        )
        argument_model.model_rebuild(force=True)
        registered.parameters = argument_model.model_json_schema(by_alias=True)

    def _build_adapter(self, definition: ToolDefinition) -> Callable[..., Any]:
        """Create a schema-preserving async adapter for one tool definition."""

        async def execute_tool(**arguments: Any) -> Any:
            response = await self._executor.execute(definition.name, arguments)
            if not response.success:
                assert response.error is not None
                safe_error = response.error.model_dump(mode="json", exclude_none=True)
                raise ToolError(
                    json.dumps(
                        safe_error,
                        ensure_ascii=False,
                        separators=(",", ":"),
                        sort_keys=True,
                    )
                )
            assert response.result is not None
            return definition.output_model.model_validate(response.result, strict=False)

        execute_tool.__name__ = definition.name
        execute_tool.__doc__ = definition.description
        execute_tool.__signature__ = self._signature(definition)  # type: ignore[attr-defined]
        return execute_tool

    @staticmethod
    def _signature(definition: ToolDefinition) -> inspect.Signature:
        """Expose the Pydantic input model as the MCP callable signature."""

        parameters: list[inspect.Parameter] = []
        for name, field in definition.input_model.model_fields.items():
            default = inspect.Parameter.empty if field.is_required() else field.default
            parameters.append(
                inspect.Parameter(
                    name=name,
                    kind=inspect.Parameter.KEYWORD_ONLY,
                    default=default,
                    annotation=field.annotation or Any,
                )
            )
        return inspect.Signature(
            parameters=parameters,
            return_annotation=definition.output_model,
        )
