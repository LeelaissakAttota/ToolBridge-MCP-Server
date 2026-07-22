"""Tests for ToolRegistry."""

import pytest
from mcp_server.tools.base import BaseTool, ToolRegistry
from mcp_server.tools.base.metadata import ToolMetadata


class SampleTool(BaseTool):
    """Sample tool for testing."""
    name = "sample_tool"
    description = "A sample tool for testing"
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

    def execute(self, arguments):
        return {"response": f"You said: {arguments['message']}"}


class AnotherTool(BaseTool):
    """Another sample tool."""
    name = "another_tool"
    description = "Another tool"
    tags = ["test", "example"]

    def get_input_schema(self):
        return {"type": "object", "properties": {}}

    def execute(self, arguments):
        return {"result": "ok"}


def test_registry_initialization():
    """Test registry initializes empty."""
    registry = ToolRegistry()
    assert len(registry) == 0
    assert list(registry) == []


def test_register_tool():
    """Test registering a tool."""
    registry = ToolRegistry()
    tool = SampleTool()
    registry.register_tool(tool)
    assert len(registry) == 1
    assert "sample_tool" in registry


def test_register_duplicate_tool_raises():
    """Test registering duplicate tool raises ValueError."""
    registry = ToolRegistry()
    tool = SampleTool()
    registry.register_tool(tool)
    with pytest.raises(ValueError, match="already registered"):
        registry.register_tool(SampleTool())


def test_register_non_base_tool_raises():
    """Test registering non-BaseTool raises TypeError."""
    registry = ToolRegistry()
    with pytest.raises(TypeError, match="BaseTool instance"):
        registry.register_tool("not a tool")


def test_unregister_tool():
    """Test unregistering a tool."""
    registry = ToolRegistry()
    tool = SampleTool()
    registry.register_tool(tool)
    registry.unregister_tool("sample_tool")
    assert len(registry) == 0
    assert "sample_tool" not in registry


def test_unregister_nonexistent_raises():
    """Test unregistering nonexistent tool raises KeyError."""
    registry = ToolRegistry()
    with pytest.raises(KeyError, match="not found"):
        registry.unregister_tool("nonexistent")


def test_get_tool():
    """Test getting a tool by name."""
    registry = ToolRegistry()
    tool = SampleTool()
    registry.register_tool(tool)
    retrieved = registry.get_tool("sample_tool")
    assert retrieved is tool


def test_get_nonexistent_tool_returns_none():
    """Test getting nonexistent tool returns None."""
    registry = ToolRegistry()
    assert registry.get_tool("nonexistent") is None


def test_get_metadata():
    """Test getting tool metadata."""
    registry = ToolRegistry()
    tool = SampleTool()
    registry.register_tool(tool)
    metadata = registry.get_metadata("sample_tool")
    assert isinstance(metadata, ToolMetadata)
    assert metadata.name == "sample_tool"
    assert metadata.description == "A sample tool for testing"
    assert metadata.version == "1.0.0"
    assert metadata.tags == ["test"]


def test_list_tools():
    """Test listing all tools."""
    registry = ToolRegistry()
    registry.register_tool(SampleTool())
    registry.register_tool(AnotherTool())
    tools = registry.list_tools()
    assert len(tools) == 2
    names = {t.name for t in tools}
    assert names == {"sample_tool", "another_tool"}


def test_list_tool_names():
    """Test listing tool names."""
    registry = ToolRegistry()
    registry.register_tool(SampleTool())
    registry.register_tool(AnotherTool())
    names = registry.list_tool_names()
    assert sorted(names) == ["another_tool", "sample_tool"]


def test_validate_tool_valid():
    """Test validating a valid tool."""
    registry = ToolRegistry()
    tool = SampleTool()
    registry.register_tool(tool)
    is_valid, errors = registry.validate_tool("sample_tool")
    assert is_valid is True
    assert errors == []


def test_validate_tool_missing_schema_type():
    """Test validating tool with invalid input schema."""

    class BadTool(BaseTool):
        name = "bad_tool"
        description = "Bad tool"

        def get_input_schema(self):
            return {"properties": {}}  # Missing 'type'

        def execute(self, args):
            return {}

    registry = ToolRegistry()
    tool = BadTool()
    registry.register_tool(tool)
    is_valid, errors = registry.validate_tool("bad_tool")
    assert is_valid is False
    assert any("type" in e for e in errors)


def test_validate_nonexistent_tool():
    """Test validating nonexistent tool."""
    registry = ToolRegistry()
    is_valid, errors = registry.validate_tool("nonexistent")
    assert is_valid is False
    assert any("not found" in e for e in errors)


def test_has_tool():
    """Test has_tool method."""
    registry = ToolRegistry()
    registry.register_tool(SampleTool())
    assert registry.has_tool("sample_tool") is True
    assert registry.has_tool("nonexistent") is False


def test_is_enabled():
    """Test is_enabled method."""
    registry = ToolRegistry()
    registry.register_tool(SampleTool())
    assert registry.is_enabled("sample_tool") is True
    assert registry.is_enabled("nonexistent") is False


def test_enable_disable_tool():
    """Test enable/disable tool (no-op but logs)."""
    registry = ToolRegistry()
    registry.register_tool(SampleTool())
    registry.enable_tool("sample_tool")  # Should not raise
    registry.disable_tool("sample_tool")  # Should not raise


def test_clear_registry():
    """Test clearing registry."""
    registry = ToolRegistry()
    registry.register_tool(SampleTool())
    registry.register_tool(AnotherTool())
    registry.clear()
    assert len(registry) == 0


def test_registry_repr():
    """Test registry repr."""
    registry = ToolRegistry()
    registry.register_tool(SampleTool())
    repr_str = repr(registry)
    assert "ToolRegistry" in repr_str
    assert "tools=1" in repr_str


def test_metadata_to_mcp_tool():
    """Test ToolMetadata to_mcp_tool conversion."""
    registry = ToolRegistry()
    tool = SampleTool()
    registry.register_tool(tool)
    metadata = registry.get_metadata("sample_tool")
    mcp_tool = metadata.to_mcp_tool()
    assert mcp_tool["name"] == "sample_tool"
    assert mcp_tool["description"] == "A sample tool for testing"
    assert "inputSchema" in mcp_tool


def test_registry_contains():
    """Test 'in' operator for registry."""
    registry = ToolRegistry()
    registry.register_tool(SampleTool())
    assert "sample_tool" in registry
    assert "nonexistent" not in registry


def test_registry_iter():
    """Test iterating over registry."""
    registry = ToolRegistry()
    registry.register_tool(SampleTool())
    registry.register_tool(AnotherTool())
    names = list(registry)
    assert set(names) == {"sample_tool", "another_tool"}


def test_registry_len():
    """Test len() on registry."""
    registry = ToolRegistry()
    assert len(registry) == 0
    registry.register_tool(SampleTool())
    assert len(registry) == 1
    registry.register_tool(AnotherTool())
    assert len(registry) == 2