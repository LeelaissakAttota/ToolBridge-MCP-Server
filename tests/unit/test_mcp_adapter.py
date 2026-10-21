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
from toolbridge.tools.domain.llm_analysis import (
    LLMAnalysisInput,
    LLMAnalysisOutput,
)


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


def build_analysis_mcp() -> FastMCP:
    """Build an isolated MCP transport with the enum-bearing analysis contract."""

    registry = ToolRegistry()
    registry.register(
        ToolDefinition(
            name="llm_analysis",
            description="Analyze or summarize text.",
            input_model=LLMAnalysisInput,
            output_model=LLMAnalysisOutput,
            handler=lambda data: LLMAnalysisOutput(
                operation=data.operation,
                content="Processed text.",
                provider="test-provider",
                model="test-model",
                request_id="test-request",
                input_tokens=1,
                output_tokens=2,
                total_tokens=3,
            ),
            timeout_seconds=1.0,
        )
    )
    executor = ToolExecutor(
        registry,
        RequestValidator(max_request_bytes=1_024),
        ResponseValidator(max_response_bytes=1_024),
    )
    mcp = FastMCP("analysis-adapter-test", stateless_http=True, json_response=True)
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


def test_mcp_adapter_preserves_strict_non_enum_validation() -> None:
    with pytest.raises(ToolError):
        asyncio.run(build_mcp().call_tool("add", {"left": "2", "right": 3}))


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


@pytest.mark.parametrize("operation", ["summarize", "analyze"])
def test_mcp_adapter_accepts_advertised_json_enum(operation: str) -> None:
    mcp = build_analysis_mcp()
    tools = asyncio.run(mcp.list_tools())
    operation_schema = tools[0].inputSchema["$defs"]["AnalysisOperation"]

    assert operation in operation_schema["enum"]

    _, structured = asyncio.run(
        mcp.call_tool(
            "llm_analysis",
            {
                "operation": operation,
                "text": "ToolBridge is an MCP server.",
                "instructions": "Reply in one short sentence.",
            },
        )
    )

    assert structured is not None
    assert structured["operation"] == operation


def test_mcp_adapter_rejects_invalid_json_enum() -> None:
    with pytest.raises(ToolError) as caught:
        asyncio.run(
            build_analysis_mcp().call_tool(
                "llm_analysis",
                {"operation": "invalid-operation", "text": "hello"},
            )
        )

    assert "Input should be 'analyze' or 'summarize'" in str(caught.value)
    assert "invalid-operation" not in str(caught.value)


def test_mcp_adapter_treats_default_factory_fields_as_optional() -> None:
    from toolbridge.tools.domain.sql_query import SQLQueryInput, SQLQueryOutput

    registry = ToolRegistry()
    registry.register(
        ToolDefinition(
            name="sql_query",
            description="Run SQL.",
            input_model=SQLQueryInput,
            output_model=SQLQueryOutput,
            handler=lambda data: SQLQueryOutput(
                columns=["n"],
                rows=[{"n": len(data.parameters)}],
                row_count=1,
                truncated=False,
                execution_ms=0.0,
            ),
            timeout_seconds=1.0,
        )
    )
    executor = ToolExecutor(
        registry,
        RequestValidator(max_request_bytes=1_024),
        ResponseValidator(max_response_bytes=1_024),
    )
    mcp = FastMCP("sql-adapter-test", stateless_http=True, json_response=True)
    MCPToolAdapter(mcp, registry, executor).register_tools()

    tools = asyncio.run(mcp.list_tools())
    assert tools[0].inputSchema["required"] == ["query"]
    _, structured = asyncio.run(mcp.call_tool("sql_query", {"query": "SELECT 1"}))
    assert structured["rows"] == [{"n": 0}]
    _, structured = asyncio.run(
        mcp.call_tool("sql_query", {"query": "SELECT 1", "parameters": {"a": 1}})
    )
    assert structured["rows"] == [{"n": 1}]
