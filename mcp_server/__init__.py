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
from mcp_server.providers import (
    ProviderBase,
    ProviderConfig,
    GenerationRequest,
    GenerationResponse,
    HealthCheckResult,
    ModelInfo,
    TokenUsage,
    CerebrasProvider,
    NvidiaProvider,
    OpenRouterProvider,
    ProviderFactory,
    provider_factory,
    ModelRouter,
    RoutingConfig,
    RoutingDecision,
    model_router,
)

__version__ = "0.3.0"
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
    "ProviderBase",
    "ProviderConfig",
    "GenerationRequest",
    "GenerationResponse",
    "HealthCheckResult",
    "ModelInfo",
    "TokenUsage",
    "CerebrasProvider",
    "NvidiaProvider",
    "OpenRouterProvider",
    "ProviderFactory",
    "provider_factory",
    "ModelRouter",
    "RoutingConfig",
    "RoutingDecision",
    "model_router",
    "__version__",
]