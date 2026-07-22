"""Tests for ToolManager."""

import pytest
from mcp_server.tools.base import BaseTool
from mcp_server.tools.registry import ToolRegistry
from mcp_server.tools.manager import ToolManager


class SampleTool(BaseTool):
    """Sample tool for testing."""
    name = "sample_tool"
    description = "A sample tool"
    tags = ["test"]
    version = "1.0.0"

    def get_input_schema(self):
        return {
            "type": "object",
            "properties": {
                "message": {"type": "string"}
            },
            "required": ["message"],
            "additionalProperties": False
        }

    async def execute(self, arguments):
        return {"response": f"You said: {arguments['message']}"}


class AnotherTool(BaseTool):
    """Another tool for testing."""
    name = "another_tool"
    description = "Another test tool"

    def get_input_schema(self):
        return {"type": "object", "properties": {}}

    async def execute(self, arguments):
        return {"status": "ok"}


class BadTool(BaseTool):
    """Tool with invalid schema."""
    name = "bad_tool"
    description = "Bad tool"

    def get_input_schema(self):
        return {"properties": {}}  # Missing type

    async def execute(self, arguments):
        return {}


def test_tool_manager_initialization():
    """Test ToolManager initializes with empty registry."""
    manager = ToolManager()
    assert len(manager.registry) == 0
    assert len(manager) == 0


def test_tool_manager_with_existing_registry():
    """Test ToolManager with provided registry."""
    registry = ToolRegistry()
    registry.register_tool(SampleTool())
    manager = ToolManager(registry)
    assert len(manager.registry) == 1
    assert "sample_tool" in manager.registry


def test_discover_tools():
    """Test tool discovery (returns empty for now)."""
    manager = ToolManager()
    discovered = manager.discover_tools("mcp_server.tools")
    assert isinstance(discovered, list)


def test_register_tool():
    """Test registering a tool."""
    manager = ToolManager()
    tool = SampleTool()
    manager.register_tool(tool)
    assert len(manager) == 1
    assert "sample_tool" in manager


def test_register_multiple_tools():
    """Test registering multiple tools."""
    manager = ToolManager()
    manager.register_tool(SampleTool())
    manager.register_tool(AnotherTool())
    assert len(manager) == 2


def test_register_tools_list():
    """Test register_tools with list."""
    manager = ToolManager()
    manager.register_tools([SampleTool(), AnotherTool()])
    assert len(manager) == 2


def test_validate_tool():
    """Test validating a tool."""
    manager = ToolManager()
    manager.register_tool(SampleTool())
    is_valid, errors = manager.validate_tool("sample_tool")
    assert is_valid is True
    assert errors == []


def test_validate_nonexistent_tool():
    """Test validating nonexistent tool."""
    manager = ToolManager()
    is_valid, errors = manager.validate_tool("nonexistent")
    assert is_valid is False
    assert len(errors) > 0
    assert any("not found" in e for e in errors)


def test_validate_all_tools():
    """Test validating all tools."""
    manager = ToolManager()
    manager.register_tool(SampleTool())
    manager.register_tool(AnotherTool())
    results = manager.validate_all_tools()
    assert len(results) == 2
    assert all(v[0] is True for v in results.values())


@pytest.mark.asyncio
async def test_execute_tool():
    """Test synchronous tool execution."""
    manager = ToolManager()
    manager.register_tool(SampleTool())
    result = await manager.execute_tool("sample_tool", {"message": "hello"})
    assert result == {"response": "You said: hello"}


@pytest.mark.asyncio
async def test_execute_nonexistent_tool():
    """Test executing nonexistent tool raises KeyError."""
    manager = ToolManager()
    with pytest.raises(KeyError, match="not found"):
        await manager.execute_tool("nonexistent", {})


@pytest.mark.asyncio
async def test_execute_tool_invalid_args():
    """Test executing tool with invalid arguments."""
    manager = ToolManager()
    manager.register_tool(SampleTool())
    with pytest.raises(Exception):  # Should raise validation error
        await manager.execute_tool("sample_tool", {"wrong_param": "value"})


def test_get_tool():
    """Test getting a tool by name."""
    manager = ToolManager()
    tool = SampleTool()
    manager.register_tool(tool)
    retrieved = manager.get_tool("sample_tool")
    assert retrieved is tool


def test_get_nonexistent_tool():
    """Test getting nonexistent tool returns None."""
    manager = ToolManager()
    assert manager.get_tool("nonexistent") is None


def test_get_tool_info():
    """Test getting tool info."""
    manager = ToolManager()
    manager.register_tool(SampleTool())
    info = manager.get_tool_info("sample_tool")
    assert info is not None
    assert info["name"] == "sample_tool"
    assert info["description"] == "A sample tool"
    assert info["version"] == "1.0.0"


def test_list_tools():
    """Test listing all tools."""
    manager = ToolManager()
    manager.register_tool(SampleTool())
    manager.register_tool(AnotherTool())
    tools = manager.list_tools()
    assert len(tools) == 2
    names = {t["name"] for t in tools}
    assert names == {"sample_tool", "another_tool"}


def test_unregister_tool():
    """Test unregistering a tool."""
    manager = ToolManager()
    manager.register_tool(SampleTool())
    manager.unregister_tool("sample_tool")
    assert len(manager) == 0
    assert "sample_tool" not in manager


def test_unregister_nonexistent():
    """Test unregistering nonexistent tool raises KeyError."""
    manager = ToolManager()
    with pytest.raises(KeyError):
        manager.unregister_tool("nonexistent")


def test_get_registry():
    """Test getting underlying registry."""
    manager = ToolManager()
    registry = manager.get_registry()
    assert registry is manager.registry


def test_manager_len():
    """Test len() on manager."""
    manager = ToolManager()
    assert len(manager) == 0
    manager.register_tool(SampleTool())
    assert len(manager) == 1


def test_manager_contains():
    """Test 'in' operator on manager."""
    manager = ToolManager()
    manager.register_tool(SampleTool())
    assert "sample_tool" in manager
    assert "nonexistent" not in manager


def test_manager_repr():
    """Test manager repr."""
    manager = ToolManager()
    manager.register_tool(SampleTool())
    repr_str = repr(manager)
    assert "ToolManager" in repr_str
    assert "tools=1" in repr_str


@pytest.mark.asyncio
async def test_initialize_all():
    """Test initializing all tools."""
    manager = ToolManager()
    manager.register_tool(SampleTool())
    await manager.initialize_all()  # Should not raise


@pytest.mark.asyncio
async def test_cleanup_all():
    """Test cleaning up all tools."""
    manager = ToolManager()
    manager.register_tool(SampleTool())
    await manager.cleanup_all()  # Should not raise


def test_load_tool_module():
    """Test loading tool from module path (mocked)."""
    manager = ToolManager()
    # This will fail because module doesn't exist, but shouldn't crash
    tool = manager.load_tool_module("nonexistent.module")
    assert tool == []


def test_load_tools_from_path():
    """Test loading tools from path (mocked)."""
    manager = ToolManager()
    # Should handle non-existent path gracefully
    tools = manager.load_tools_from_path("/nonexistent/path")
    assert tools == []