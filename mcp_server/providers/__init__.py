"""Provider abstraction layer for ToolBridge MCP Server.

Provides a unified interface for multiple LLM providers with
automatic failover, cost tracking, and intelligent routing.
"""

from mcp_server.providers.base import (
    ProviderBase,
    ProviderConfig,
    GenerationRequest,
    GenerationResponse,
    HealthCheckResult,
    ModelInfo,
    TokenUsage,
)
from mcp_server.providers.cerebras import CerebrasProvider
from mcp_server.providers.nvidia import NvidiaProvider
from mcp_server.providers.openrouter import OpenRouterProvider
from mcp_server.providers.factory import ProviderFactory, provider_factory
from mcp_server.providers.routing import (
    RoutingConfig,
    RoutingDecision,
    RoutingStrategy,
    RoutingReason,
    get_routing_config,
    set_routing_config,
)
from mcp_server.providers.router import ModelRouter, model_router

__all__ = [
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
    "RoutingConfig",
    "RoutingDecision",
    "RoutingStrategy",
    "RoutingReason",
    "get_routing_config",
    "set_routing_config",
    "ModelRouter",
    "model_router",
]