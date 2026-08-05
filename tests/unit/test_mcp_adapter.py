"""Unit tests for MCP discovery and execution adapters."""

import asyncio

import pytest
from mcp.server.fastmcp import FastMCP
from mcp.server.fastmcp.exceptions import ToolError

from toolbridge.adapters.mcp import MCPToolAdapter
from toolbridge.core.contracts import ToolDefinition, ToolInput, ToolOutput
from toolbridge.core.executor import ToolExecutor
from toolbridge.core.registry import ToolRegistry
from toolbridge.core.validation import RequestValidator, ResponseValidator


class AddInput(ToolInput):
    """Input contract for the adapter test tool."""

    left: int
    right: int


class AddOutput(ToolOutput):
    """Output contract for the adapter test tool."""

    total: int


def build_mcp() -> FastMCP:
    """Build an isolated MCP transport with one core tool."""

    registry = ToolRegistry()
    registry.register(
        ToolDefinition(
            name="add",
            description="Add two integers.",
            input_model=AddInput,
            output_model=AddOutput,
            handler=lambda data: AddOutput(total=data.left + data.right),
            timeout_seconds=1.0,
        )
    )
    executor = ToolExecutor(
        registry,
        RequestValidator(max_request_bytes=1_024),
        ResponseValidator(max_response_bytes=1_024),
    )
    mcp = FastMCP("adapter-test", stateless_http=True, json_response=True)
    MCPToolAdapter(mcp, registry, executor).register_tools()
    return mcp


def test_mcp_discovery_uses_core_contract_schema() -> None:
    tools = asyncio.run(build_mcp().list_tools())

    assert [tool.name for tool in tools] == ["add"]
    assert tools[0].description == "Add two integers."
    assert set(tools[0].inputSchema["required"]) == {"left", "right"}
    assert tools[0].inputSchema["additionalProperties"] is False
    assert tools[0].outputSchema is not None
    assert "total" in tools[0].outputSchema["properties"]


def test_mcp_adapter_executes_through_core() -> None:
    result = asyncio.run(build_mcp().call_tool("add", {"left": 2, "right": 3}))

    _, structured = result
    assert structured == {"total": 5}

def test_mcp_adapter_rejects_and_hides_extra_input() -> None:
    with pytest.raises(ToolError) as caught:
        asyncio.run(
            build_mcp().call_tool(
                "add",
                {"left": 2, "right": 3, "token": "secret-value"},
            )
        )

    assert "Extra inputs are not permitted" in str(caught.value)
    assert "secret-value" not in str(caught.value)
