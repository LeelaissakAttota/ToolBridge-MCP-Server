"""MCP Server bootstrap and lifecycle management.

Initializes FastMCP server with custom tool registry, health checks,
and graceful startup/shutdown.
"""

import asyncio
import logging
import signal
from contextlib import asynccontextmanager
from typing import Any

from mcp.server import FastMCP
from mcp.server.fastmcp import Context

from mcp_server.config import settings
from mcp_server.core.health import ServerInfo, health_service, version_service
from mcp_server.logging.logger import logger
from mcp_server.tools.base import BaseTool
from mcp_server.tools.registry import ToolRegistry

logger = logging.getLogger(__name__)


class MCPServer:
    """Production-ready MCP server wrapper.

    Manages FastMCP lifecycle, tool registration, health checks,
    and graceful shutdown.
    """

    def __init__(
        self,
        name: str | None = None,
        instructions: str | None = None,
        host: str | None = None,
        port: int | None = None,
    ) -> None:
        """Initialize MCP server.

        Args:
            name: Server name (defaults to config APP_NAME).
            instructions: Server instructions for clients.
            host: Bind host (defaults to config HOST).
            port: Bind port (defaults to config PORT).
        """
        self._name = name or settings.APP_NAME
        self._instructions = instructions or "ToolBridge MCP Server - Dynamic tool execution platform"
        self._host = host or settings.HOST
        self._port = port or settings.PORT

        # Initialize FastMCP
        self._mcp = FastMCP(
            name=self._name,
            instructions=self._instructions,
            host=self._host,
            port=self._port,
            log_level=settings.LOG_LEVEL,
        )

        # Tool registry
        self._registry = ToolRegistry()

        # Server state
        self._running = False
        self._shutdown_event = asyncio.Event()

        # Setup built-in handlers
        self._setup_handlers()

        # Setup health server info
        self._server_info = ServerInfo(
            name=self._name,
            capabilities={
                "tools": {"listChanged": True},
                "logging": {},
            },
        )
        health_service._server_info = self._server_info
        version_service._server_info = self._server_info

        logger.info(f"MCPServer initialized: {self._name}")

    @property
    def mcp(self) -> FastMCP:
        """Get underlying FastMCP instance."""
        return self._mcp

    @property
    def registry(self) -> ToolRegistry:
        """Get tool registry."""
        return self._registry

    @property
    def is_running(self) -> bool:
        """Check if server is running."""
        return self._running

    def _setup_handlers(self) -> None:
        """Setup built-in MCP protocol handlers."""

        @self._mcp.tool()
        async def health_check(ctx: Context) -> dict[str, Any]:
            """Health check endpoint."""
            status = await health_service.check()
            return status.to_dict()

        @self._mcp.tool()
        async def version_info(ctx: Context) -> dict[str, Any]:
            """Get server version info."""
            return version_service.get_full_info()

        # Register initialize handler
        @self._mcp.tool()
        async def initialize(ctx: Context, params: dict[str, Any]) -> dict[str, Any]:
            """Initialize MCP session."""
            logger.info("MCP initialize request received")
            return {
                "protocolVersion": "2024-11-05",
                "capabilities": self._server_info.capabilities,
                "serverInfo": {
                    "name": self._server_info.name,
                    "version": self._server_info.version,
                },
            }

        @self._mcp.tool()
        async def ping(ctx: Context) -> dict[str, Any]:
            """Ping endpoint."""
            return {"status": "pong"}

    def register_tool(self, tool: BaseTool) -> None:
        """Register a tool with the server.

        Args:
            tool: BaseTool instance to register.

        Raises:
            ValueError: If tool name conflicts.
            TypeError: If not a BaseTool.
        """
        # Validate tool
        is_valid, errors = self._registry.validate_tool(tool.name)
        if not is_valid:
            raise ValueError(f"Tool validation failed: {errors}")

        # Register in our registry
        self._registry.register_tool(tool)

        # Register with FastMCP
        self._mcp.add_tool(
            tool.execute,
            name=tool.name,
            title=getattr(tool, "title", None),
            description=tool.description,
            structured_output=True,
        )

        logger.info(f"Tool registered with FastMCP: {tool.name}")

    def unregister_tool(self, name: str) -> None:
        """Unregister a tool.

        Args:
            name: Tool name to unregister.
        """
        self._registry.unregister_tool(name)
        # Note: FastMCP doesn't support tool removal directly
        # In production, you'd need to recreate the server or mark as disabled
        logger.info(f"Tool unregistered from registry: {name}")

    def get_tool(self, name: str) -> BaseTool | None:
        """Get a registered tool."""
        return self._registry.get_tool(name)

    def list_tools(self) -> list[dict[str, Any]]:
        """List all registered tools."""
        return self._registry.list_tools()

    async def startup(self) -> None:
        """Perform startup tasks."""
        logger.info("Starting MCP server...")
        self._running = True
        self._server_info.started_at = time.time()
        logger.info(f"MCP server started on {self._host}:{self._port}")

    async def shutdown(self) -> None:
        """Perform graceful shutdown."""
        logger.info("Shutting down MCP server...")
        self._running = False
        self._shutdown_event.set()
        logger.info("MCP server shutdown complete")

    async def run(self, transport: str = "streamable-http") -> None:
        """Run the MCP server.

        Args:
            transport: Transport protocol ("stdio", "sse", "streamable-http").
        """
        await self.startup()

        try:
            if transport == "stdio":
                await self._mcp.run_stdio_async()
            elif transport == "sse":
                await self._mcp.run_sse_async()
            elif transport == "streamable-http":
                await self._mcp.run_streamable_http_async()
            else:
                raise ValueError(f"Unknown transport: {transport}")
        finally:
            await self.shutdown()

    def run_sync(self, transport: str = "streamable-http") -> None:
        """Run server synchronously (blocking).

        Args:
            transport: Transport protocol.
        """
        asyncio.run(self.run(transport))


# Time import for startup
import time