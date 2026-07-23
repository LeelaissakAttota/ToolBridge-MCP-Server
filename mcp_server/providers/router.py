"""Model router for intelligent provider selection and failover."""

import logging
from typing import Optional

from mcp_server.config import settings
from mcp_server.providers.base import (
    GenerationRequest,
    GenerationResponse,
    HealthCheckResult,
)
from mcp_server.providers.factory import provider_factory
from mcp_server.providers.routing import (
    RoutingConfig,
    RoutingStrategy,
)

logger = logging.getLogger(__name__)


class ModelRouter:
    """Intelligent model router with automatic failover and routing strategies.

    Responsibilities:
    - Route requests to appropriate provider/model
    - Handle automatic failover on failures
    - Support multiple routing strategies
    - Track provider health and availability
    """

    def __init__(self, config: Optional[RoutingConfig] = None):
        self.config = config or RoutingConfig()
        self._initialized = False
        self._last_health_check: dict[str, HealthCheckResult] = {}

    async def initialize(self) -> None:
        """Initialize provider instances based on configuration."""
        # Create providers with API keys from settings
        provider_configs = {
            "cerebras": {
                "api_key": settings.CEREBRAS_API_KEY,
                "default_model": self.config.fast_model,
            },
            "nvidia": {
                "api_key": settings.NVIDIA_API_KEY,
                "default_model": self.config.fallback_model,
            },
            "openrouter": {
                "api_key": settings.OPENROUTER_API_KEY,
                "default_model": self.config.default_model or "openai/gpt-4o-mini",
            },
        }

        for name, config in provider_configs.items():
            if config.get("api_key"):
                provider_factory.get_or_create(name, config)

        self._initialized = True
        logger.info("ModelRouter initialized with providers: %s", list(provider_configs.keys()))

    def _ensure_initialized(self) -> None:
        """Ensure router is initialized."""
        if not self._initialized:
            # We can't await here, so we'll lazy-initialize
            pass

    def _get_routing_config(self) -> RoutingConfig:
        """Get routing configuration, preferring settings over defaults."""
        return RoutingConfig(
            default_provider=settings.DEFAULT_PROVIDER,
            default_model=settings.DEFAULT_MODEL,
            fast_provider=settings.FAST_PROVIDER,
            fast_model=settings.FAST_MODEL,
            smart_provider=settings.SMART_PROVIDER,
            smart_model=settings.SMART_MODEL,
            fallback_provider=settings.FALLBACK_PROVIDER,
            fallback_model=settings.FALLBACK_MODEL,
            enable_failover=settings.ENABLE_FAILOVER,
            max_failover_attempts=2,
            cost_optimization=settings.COST_OPTIMIZATION if hasattr(settings, 'COST_OPTIMIZATION') else False,
            max_cost_per_request=1.0,
        )

    def route(self, request: GenerationRequest) -> tuple[str, str]:
        """Determine provider and model for a request.

        Args:
            request: Generation request with optional strategy hints

        Returns:
            Tuple of (provider_name, model_name)
        """
        config = self._get_routing_config()

        # Check if request specifies explicit provider/model
        if request.model and hasattr(request, 'provider') and request.provider:
            return request.provider, request.model

        # Check for explicit strategy in request metadata
        strategy = getattr(request, 'routing_strategy', None)
        if strategy:
            return self._route_by_strategy(strategy, request, config)

        # Auto-detect based on request characteristics
        return self._auto_route(request, config)

    def _route_by_strategy(
        self,
        strategy: RoutingStrategy,
        request: GenerationRequest,
        config: RoutingConfig,
    ) -> tuple[str, str]:
        """Route based on explicit strategy."""
        if strategy == RoutingStrategy.FAST:
            return config.fast_provider, config.fast_model
        elif strategy == RoutingStrategy.SMART:
            return config.smart_provider, config.smart_model
        elif strategy == RoutingStrategy.FALLBACK:
            return config.fallback_provider, config.fallback_model
        elif strategy == RoutingStrategy.COST_OPTIMIZED:
            return self._find_cheapest_provider(request)
        else:  # DEFAULT
            return config.default_provider, config.default_model

    def _auto_route(self, request: GenerationRequest, config: RoutingConfig) -> tuple[str, str]:
        """Auto-detect best routing based on request characteristics."""
        # If streaming, prefer fast provider
        if request.stream:
            return config.fast_provider, config.fast_model

        # If max_tokens is large, use smart path
        if request.max_tokens and request.max_tokens > 2000:
            return config.smart_provider, config.smart_model

        # Default to default provider
        return config.default_provider, config.default_model or config.smart_model

    def _find_cheapest_provider(self, request: GenerationRequest) -> tuple[str, str]:
        """Find cheapest available provider for request."""
        # Simple implementation - use fast provider (usually cheapest)
        config = self._get_routing_config()
        return config.fast_provider, config.fast_model

    async def generate(
        self,
        request: GenerationRequest,
        provider_name: Optional[str] = None,
        model_name: Optional[str] = None,
    ) -> GenerationResponse:
        """Generate with automatic routing and failover.

        Args:
            request: Generation request
            provider_name: Override provider (optional)
            model_name: Override model (optional)

        Returns:
            Generation response

        Raises:
            Exception: If all providers fail
        """
        # Use explicit provider/model if provided, otherwise route
        if provider_name and model_name:
            provider_name, model_name = provider_name, model_name
        else:
            provider_name, model_name = self.route(request)

        # Apply model override
        if model_name:
            request.model = model_name

        # Try primary provider
        provider = provider_factory.get_instance(provider_name)
        if not provider:
            provider = provider_factory.get_or_create(provider_name)

        # Update request with selected model
        if model_name:
            request.model = model_name

        # Try primary with retries
        last_error = None
        for attempt in range(2):
            try:
                response = await provider.generate(request)
                return response
            except Exception as e:
                last_error = e
                logger.warning(f"Provider {provider_name} attempt {attempt + 1} failed: {e}")

                # Try failover
                if settings.ENABLE_FAILOVER:
                    failover = await self._failover(request, provider_name)
                    if failover:
                        continue

        # All retries failed
        raise Exception(f"All providers failed. Last error: {last_error}")

    async def _failover(
        self,
        request: GenerationRequest,
        failed_provider: str,
    ) -> bool:
        """Attempt failover to next available provider.

        Args:
            request: Generation request
            failed_provider: Name of failed provider

        Returns:
            True if failover succeeded, False otherwise
        """
        config = self._get_routing_config()
        tried = [failed_provider]

        # Build failover chain
        failover_chain = []
        if failed_provider != config.fallback_provider:
            failover_chain.append(config.fallback_provider)
        # Add other providers as backup
        for p in ["cerebras", "nvidia", "openrouter"]:
            if p not in tried and p not in failover_chain:
                failover_chain.append(p)

        for provider_name in failover_chain:
            try:
                provider = provider_factory.get_instance(provider_name)
                if not provider:
                    provider = provider_factory.get_or_create(provider_name)

                # Check health before trying
                health = await provider.health_check()
                if not health.healthy:
                    logger.warning(f"Failover provider {provider_name} unhealthy: {health.error}")
                    continue

                logger.info(f"Failing over to {provider_name}")
                return True

            except Exception as e:
                logger.warning(f"Failover to {provider_name} failed: {e}")
                tried.add(provider_name)
                continue

        return False

    async def health_check_all(self) -> dict[str, HealthCheckResult]:
        """Check health of all registered providers."""
        results = {}
        for name, instance in provider_factory._instances.items():
            try:
                results[name] = await instance.health_check()
            except Exception as e:
                results[name] = HealthCheckResult(
                    healthy=False,
                    error=str(e),
                )
        return results

    async def get_available_models(self) -> dict[str, list[str]]:
        """Get available models from all providers."""
        models = {}
        for name, instance in provider_factory._instances.items():
            try:
                models = await instance.available_models()
                models[name] = [m.name for m in models]
            except Exception as e:
                logger.warning(f"Failed to get models from {name}: {e}")
        return models

    async def estimate_cost(self, request: GenerationRequest) -> dict[str, float]:
        """Estimate cost across all providers."""
        costs = {}
        for name, instance in provider_factory._instances.items():
            try:
                cost = await instance.estimate_cost(request)
                costs[name] = cost
            except Exception:
                pass
        return costs

    async def get_cheapest_provider(self, request: GenerationRequest) -> tuple[str, float]:
        """Find cheapest provider for request."""
        costs = await self.estimate_cost(request)
        if not costs:
            return None, 0.0
        cheapest = min(costs.items(), key=lambda x: x[1])
        return cheapest


# Global router instance
model_router = ModelRouter()