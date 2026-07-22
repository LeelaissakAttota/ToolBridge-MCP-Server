"""MCP Server main entry point.

Initializes and configures the FastMCP server with all core components.
"""

import logging
from typing import Any

from mcp.server.fastmcp import FastMCP

from mcp_server.config import settings
from mcp_server.core.server import MCPServer
from mcp_server.health import HealthService, ServerInfo, VersionService
from mcp_server.tools.manager import ToolManager
from mcp_server.tools.registry import ToolRegistry

logger = logging.getLogger(__name__)


def create_mcp_server() -> FastMCP:
    """Create and configure the FastMCP server instance.

    Returns:
        Configured FastMCP server.
    """
    # Create server info
    server_info = ServerInfo(
        name="toolbridge-mcp-server",
        version="0.2.0",
        description="ToolBridge MCP Server - Dynamic Tool Platform",
        transport="streamable-http",
    )

    # Create FastMCP server
    mcp = FastMCP(
        name=server_info.name,
        instructions=(
            "ToolBridge MCP Server provides dynamic tool registration "
            "and execution via the Model Context Protocol."
        ),
        host=settings.HOST,
        port=settings.PORT,
        log_level=settings.LOG_LEVEL,
    )

    # Set up health and version services
    health_service = HealthService(server_info)
    version_service = VersionService(server_info)

    # Set up tool registry and manager
    registry = ToolRegistry()
    tool_manager = ToolManager(registry)

    # Store references on the server for access in handlers
    mcp._toolbridge_health = health_service
    mcp._toolbridge_version = version_service
    mcp._toolbridge_registry = registry
    mcp._toolbridge_manager = tool_manager

    # Register core handlers
    _register_core_handlers(mcp, health_service, version_service, tool_manager)

    logger.info(f"MCP server created: {server_info.name} v{server_info.version}")
    return mcp


def _register_core_handlers(
    mcp: FastMCP,
    health: HealthService,
    version: VersionService,
    tool_manager: ToolManager,
) -> None:
    """Register core MCP protocol handlers.

    Args:
        mcp: FastMCP server instance.
        health: Health service.
        version: Version service.
        tool_manager: Tool manager.
    """

    @mcp.tool()
    async def initialize() -> dict[str, Any]:
        """Initialize the MCP server.

        Returns:
            Server initialization response with capabilities.
        """
        health.set_ready(True)
        return {
            "protocolVersion": "2024-11-05",
            "capabilities": {
                "tools": {"listChanged": True},
                "resources": {},
                "prompts": {},
            },
            "serverInfo": version.get_version(),
        }

    @mcp.tool()
    async def ping() -> dict[str, Any]:
        """Ping endpoint for health checks.

        Returns:
            Pong response.
        """
        return {"status": "ok", "timestamp": __import__("time").time()}

    @mcp.tool()
    async def tools_list() -> dict[str, Any]:
        """List all available tools.

        Returns:
            Tools list response.
        """
        tools = tool_manager.list_tools()
        return {"tools": tools}

    @mcp.tool()
    async def tools_call(name: str, arguments: dict[str, Any] | None = None) -> dict[str, Any]:
        """Call a tool by name.

        Args:
            name: Tool name.
            arguments: Tool arguments.

        Returns:
            Tool execution result.
        """
        if arguments is None:
            arguments = {}

        result = await tool_manager.execute_tool(name, arguments)
        return {"content": [{"type": "text", "text": str(result)}]}

    # Health endpoints (exposed as resources)
    @mcp.resource("health://liveness")
    async def health_liveness() -> str:
        """Liveness probe endpoint."""
        import json
        result = await health.liveness()
        return json.dumps(result)

    @mcp.resource("health://readiness")
    async def health_readiness() -> str:
        """Readiness probe endpoint."""
        import json
        result = await health.readiness()
        return json.dumps(result)

    @mcp.resource("health://full")
    async def health_full() -> str:
        """Full health check endpoint."""
        import json
        result = await health.full_health()
        return json.dumps(result)

    @mcp.resource("version://info")
    async def version_info() -> str:
        """Version information endpoint."""
        import json
        return json.dumps(version.get_version())

    logger.info("Core MCP handlers registered")


# Create the server instance
mcp = create_mcp_server()


if __name__ == "__main__":
    # Run the server
    mcp.run()