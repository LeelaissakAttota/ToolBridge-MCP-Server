"""Tests for MCP Server creation and FastMCP initialization."""

from mcp_server.server import create_mcp_server
from mcp_server.tools.base import BaseTool
from mcp_server.tools.registry import ToolRegistry
from mcp_server.tools.manager import ToolManager
from mcp_server.health import HealthService, VersionService


class TestTool(BaseTool):
    """Test tool for server tests."""
    name = "test_tool"
    description = "A test tool"

    def get_input_schema(self):
        return {"type": "object", "properties": {}}

    async def execute(self, arguments):
        return {"result": "ok"}


def test_create_mcp_server():
    """Test creating MCP server."""
    mcp = create_mcp_server()
    assert mcp is not None
    assert mcp.name == "toolbridge-mcp-server"
    assert mcp.settings.port == 8000
    assert mcp.settings.host == "0.0.0.0"


def test_server_has_health_service():
    """Test server has health service attached."""
    mcp = create_mcp_server()
    assert hasattr(mcp, '_toolbridge_health')
    assert isinstance(mcp._toolbridge_health, HealthService)


def test_server_has_version_service():
    """Test server has version service attached."""
    mcp = create_mcp_server()
    assert hasattr(mcp, '_toolbridge_version')
    assert isinstance(mcp._toolbridge_version, VersionService)


def test_server_has_registry():
    """Test server has tool registry."""
    mcp = create_mcp_server()
    assert hasattr(mcp, '_toolbridge_registry')
    assert isinstance(mcp._toolbridge_registry, ToolRegistry)


def test_server_has_manager():
    """Test server has tool manager."""
    mcp = create_mcp_server()
    assert hasattr(mcp, '_toolbridge_manager')
    assert isinstance(mcp._toolbridge_manager, ToolManager)


def test_server_instructions():
    """Test server has instructions."""
    mcp = create_mcp_server()
    assert "ToolBridge" in mcp.instructions
    assert "Model Context Protocol" in mcp.instructions


def test_register_tool_on_server():
    """Test registering tool via server's registry."""
    mcp = create_mcp_server()
    tool = TestTool()
    mcp._toolbridge_registry.register_tool(tool)
    assert "test_tool" in mcp._toolbridge_registry


def test_list_tools_via_manager():
    """Test listing tools via manager."""
    mcp = create_mcp_server()
    tool = TestTool()
    mcp._toolbridge_manager.register_tool(tool)
    tools = mcp._toolbridge_manager.list_tools()
    assert len(tools) >= 1
    names = [t["name"] for t in tools]
    assert "test_tool" in names


def test_multiple_servers_independent():
    """Test creating multiple independent servers."""
    mcp1 = create_mcp_server()
    mcp2 = create_mcp_server()
    # Each should have its own registry
    mcp1._toolbridge_registry.register_tool(TestTool())
    assert "test_tool" in mcp1._toolbridge_registry
    # mcp2 should not have the tool
    assert "test_tool" not in mcp2._toolbridge_registry