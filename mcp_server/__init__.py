"""ToolBridge MCP Server - Core package.

A production-ready MCP server with dynamic tool registration,
health monitoring, and extensible architecture.
"""

from mcp_server.config import settings
from mcp_server.core.health import (
    HealthService,
    ServerInfo,
    VersionService,
    health_service,
    version_service,
)
from mcp_server.server import create_mcp_server
from mcp_server.tools.base import BaseTool
from mcp_server.tools.manager import ToolManager
from mcp_server.tools.registry import ToolRegistry

__version__ = "0.1.0"
__all__ = [
    "settings",
    "create_mcp_server",
    "HealthService",
    "ServerInfo",
    "VersionService",
    "health_service",
    "version_service",
    "BaseTool",
    "ToolManager",
    "ToolRegistry",
    "__version__",
]