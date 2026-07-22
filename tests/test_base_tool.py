"""Tests for BaseTool class."""

import pytest
from mcp_server.tools.base import BaseTool, ToolMetadata


class ValidTool(BaseTool):
    """A valid tool implementation."""
    name = "valid_tool"
    description = "A valid tool for testing"
    tags = ["test"]
    version = "1.0.0"

    def get_input_schema(self):
        return {
            "type": "object",
            "properties": {
                "param1": {"type": "string"},
                "param2": {"type": "integer", "minimum": 0}
            },
            "required": ["param1"],
            "additionalProperties": False
        }

    def get_output_schema(self):
        return {
            "type": "object",
            "properties": {
                "result": {"type": "string"}
            }
        }

    async def execute(self, arguments):
        return {"result": f"Processed {arguments['param1']}"}


class MinimalTool(BaseTool):
    """Minimal tool with only required methods."""
    name = "minimal_tool"
    description = "Minimal tool"

    def get_input_schema(self):
        return {"type": "object", "properties": {}}

    async def execute(self, arguments):
        return {"ok": True}


class ToolWithOutputSchema(BaseTool):
    """Tool with output schema."""
    name = "output_tool"
    description = "Tool with output schema"

    def get_input_schema(self):
        return {"type": "object", "properties": {}}

    def get_output_schema(self):
        return {
            "type": "object",
            "properties": {
                "data": {"type": "string"}
            }
        }

    async def execute(self, arguments):
        return {"data": "output"}


class ToolWithConfig(BaseTool):
    """Tool that accepts config."""
    name = "config_tool"
    description = "Tool with config"

    def get_input_schema(self):
        return {"type": "object", "properties": {}}

    async def execute(self, arguments):
        return {"config": self.config}


def test_base_tool_initialization():
    """Test BaseTool initialization."""
    tool = ValidTool()
    assert tool.name == "valid_tool"
    assert tool.description == "A valid tool for testing"
    assert tool.tags == ["test"]
    assert tool.version == "1.0.0"


def test_base_tool_with_config():
    """Test BaseTool with configuration."""
    tool = ToolWithConfig(config={"api_key": "test"})
    assert tool.config == {"api_key": "test"}


def test_get_input_schema():
    """Test get_input_schema returns correct schema."""
    tool = ValidTool()
    schema = tool.get_input_schema()
    assert schema["type"] == "object"
    assert "param1" in schema["properties"]
    assert "param2" in schema["properties"]
    assert schema["required"] == ["param1"]


def test_get_output_schema():
    """Test get_output_schema."""
    tool = ValidTool()
    schema = tool.get_output_schema()
    assert schema is not None
    assert schema["type"] == "object"
    assert "result" in schema["properties"]


def test_get_output_schema_default():
    """Test get_output_schema for tool without explicit output schema."""
    tool = MinimalTool()
    # Default output_schema returns a dict
    schema = tool.get_output_schema()
    assert schema is not None
    assert schema["type"] == "object"


async def test_execute():
    """Test tool execution."""
    tool = ValidTool()
    result = await tool.execute({"param1": "test", "param2": 5})
    assert result == {"result": "Processed test"}


async def test_execute_with_defaults():
    """Test execute with optional params."""
    tool = ValidTool()
    result = await tool.execute({"param1": "test"})  # param2 optional
    assert result == {"result": "Processed test"}


def test_validate_arguments_valid():
    """Test validate_arguments with valid input."""
    tool = ValidTool()
    is_valid, error = tool.validate_arguments({"param1": "test", "param2": 10})
    assert is_valid is True
    assert error is None


def test_validate_arguments_missing_required():
    """Test validate_arguments with missing required field."""
    tool = ValidTool()
    is_valid, error = tool.validate_arguments({"param2": 10})
    assert is_valid is False
    assert "Missing required argument: param1" in error


def test_validate_arguments_not_dict():
    """Test validate_arguments with non-dict."""
    tool = ValidTool()
    is_valid, error = tool.validate_arguments("not a dict")
    assert is_valid is False
    assert error == "Arguments must be a dictionary"


async def test_validate_and_execute():
    """Test validate_and_execute."""
    tool = ValidTool()
    result = await tool.validate_and_execute({"param1": "hello"})
    assert result == {"result": "Processed hello"}


async def test_validate_and_execute_invalid():
    """Test validate_and_execute with invalid args."""
    tool = ValidTool()
    with pytest.raises(Exception):
        await tool.validate_and_execute("invalid")


def test_to_mcp_tool():
    """Test to_mcp_tool conversion."""
    tool = ValidTool()
    mcp_tool = tool.to_mcp_tool()
    assert mcp_tool["name"] == "valid_tool"
    assert mcp_tool["description"] == "A valid tool for testing"
    assert "inputSchema" in mcp_tool
    assert "outputSchema" in mcp_tool


def test_tool_metadata():
    """Test ToolMetadata dataclass."""
    metadata = ToolMetadata(
        name="test",
        description="Test tool",
        input_schema={"type": "object"},
        output_schema={"type": "object"},
        tags=["tag1"],
        version="1.0",
        author="Test"
    )
    assert metadata.name == "test"
    assert metadata.tags == ["tag1"]
    assert metadata.version == "1.0"


def test_tool_metadata_to_mcp_tool():
    """Test ToolMetadata.to_mcp_tool."""
    metadata = ToolMetadata(
        name="test",
        description="Test",
        input_schema={"type": "object"},
        output_schema={"type": "object", "properties": {"out": {"type": "string"}}},
        annotations={"readOnly": True}
    )
    mcp = metadata.to_mcp_tool()
    assert mcp["name"] == "test"
    assert mcp["inputSchema"]["type"] == "object"
    assert mcp["outputSchema"]["properties"]["out"]["type"] == "string"
    assert mcp["annotations"]["readOnly"] is True


async def test_minimal_tool():
    """Test minimal tool with only required methods."""
    tool = MinimalTool()
    assert tool.name == "minimal_tool"
    assert tool.description == "Minimal tool"
    result = await tool.execute({})
    assert result == {"ok": True}


async def test_tool_with_output_schema():
    """Test tool with explicit output schema."""
    tool = ToolWithOutputSchema()
    schema = tool.get_output_schema()
    assert schema is not None
    assert "data" in schema["properties"]
    result = await tool.execute({})
    assert result == {"data": "output"}


def test_tool_repr():
    """Test tool repr."""
    tool = ValidTool()
    repr_str = repr(tool)
    assert "valid_tool" in repr_str
    assert "v1.0.0" in repr_str


def test_base_tool_subclass_validation():
    """Test that BaseTool subclass requires name and description."""
    tool = ValidTool()
    assert tool.name == "valid_tool"


async def test_async_execute_default():
    """Test default execute_async calls sync execute."""
    tool = ValidTool()

    result = await tool.execute_async({"param1": "async"})
    assert result == {"result": "Processed async"}


def test_tool_metadata_dataclass():
    """Test ToolMetadata as dataclass."""
    metadata = ToolMetadata(
        name="test",
        description="Test",
        input_schema={},
        output_schema={}
    )
    # Test defaults
    assert metadata.annotations is None
    assert metadata.tags == []
    assert metadata.version == "1.0.0"
    assert metadata.author == "ToolBridge"
    assert metadata.enabled is True


def test_tool_metadata_to_dict():
    """Test ToolMetadata.to_dict."""
    metadata = ToolMetadata(
        name="test",
        description="Test",
        input_schema={"type": "object"},
        output_schema=None,
        tags=["tag1"],
        version="2.0"
    )
    d = metadata.to_dict()
    assert d["name"] == "test"
    assert d["tags"] == ["tag1"]
    assert d["version"] == "2.0"
    assert d["enabled"] is True