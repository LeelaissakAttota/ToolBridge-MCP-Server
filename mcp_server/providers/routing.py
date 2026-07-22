"""Model routing configuration and decision types."""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Optional


class RoutingStrategy(str, Enum):
    """Strategy for model routing."""
    DEFAULT = "default"           # Use default provider/model
    FAST = "fast"                 # Use fast path (low latency)
    SMART = "smart"               # Use smart path (high quality)
    FALLBACK = "fallback"         # Use fallback provider
    COST_OPTIMIZED = "cost"       # Optimize for cost
    AUTO = "auto"                 # Automatic selection based on request


class RoutingReason(str, Enum):
    """Reason for routing decision."""
    EXPLICIT = "explicit"         # User explicitly specified
    DEFAULT = "default"           # Using default
    FAST_PATH = "fast_path"       # Fast path selected
    SMART_PATH = "smart_path"     # Smart path selected
    FAILOVER = "failover"         # Fallback due to failure
    COST_OPTIMIZED = "cost_optimized"  # Cost optimization
    MODEL_CAPABILITY = "model_capability"  # Model capability match


@dataclass
class RoutingConfig:
    """Configuration for model routing.

    Attributes:
        default_provider: Default provider name
        default_model: Default model name
        fast_provider: Provider for fast path
        fast_model: Model for fast path
        smart_provider: Provider for smart path
        smart_model: Model for smart path
        fallback_provider: Fallback provider name
        fallback_model: Fallback model name
        enable_failover: Enable automatic failover on failure
        max_failover_attempts: Maximum failover attempts
        cost_optimization: Enable cost-based routing
        max_cost_per_request: Maximum cost per request (USD)
    """
    default_provider: str = "openrouter"
    default_model: str = ""
    fast_provider: str = "cerebras"
    fast_model: str = "llama3.1-8b"
    smart_provider: str = "openrouter"
    smart_model: str = "anthropic/claude-3.5-sonnet"
    fallback_provider: str = "nvidia"
    fallback_model: str = "meta-llama/llama-3.1-70b-instruct"
    enable_failover: bool = True
    max_failover_attempts: int = 2
    cost_optimization: bool = False
    max_cost_per_request: float = 1.0


@dataclass
class RoutingDecision:
    """Result of a routing decision.

    Attributes:
        provider: Selected provider name
        model: Selected model name
        strategy: Routing strategy used
        reason: Reason for this decision
        fallback_chain: List of fallback providers tried
        metadata: Additional metadata
    """
    provider: str
    model: str
    strategy: str
    reason: str
    fallback_chain: list[str] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)


# Global routing config (can be overridden by settings)
_routing_config: RoutingConfig = RoutingConfig()


def get_routing_config() -> RoutingConfig:
    """Get current routing configuration."""
    return _routing_config


def set_routing_config(config: RoutingConfig) -> None:
    """Set global routing configuration."""
    global _routing_config
    _routing_config = config