"""Tests for the extensible provider plugin and smart-routing platform."""

import asyncio
from collections.abc import AsyncIterator

from toolbridge.config import Settings
from toolbridge.providers.adapters.plugin import (
    ProviderPlugin,
    ProviderPluginRegistry,
    discover_provider_plugins,
)
from toolbridge.providers.application.budget import BudgetPolicy, ProviderBudgetManager
from toolbridge.providers.application.ports import BaseProvider
from toolbridge.providers.application.router import ProviderRegistration, ProviderRouter
from toolbridge.providers.application.scoring import ModelRankingEngine
from toolbridge.providers.domain.models import (
    ChatMessage,
    GenerationChunk,
    GenerationRequest,
    GenerationResponse,
    ProviderCapabilities,
    ProviderCapability,
    ProviderHealthCheck,
    ProviderModel,
    ProviderStatus,
    RoutingTask,
)


class PluginProvider(BaseProvider):
    """Offline provider used to verify plugin-neutral router behavior."""

    def __init__(
        self,
        name: str,
        capabilities: ProviderCapabilities,
        models: tuple[ProviderModel, ...],
    ) -> None:
        self._name = name
        self._capabilities = capabilities
        self._models = models
        self.initialized = False
        self.closed = False

    @property
    def name(self) -> str:
        return self._name

    @property
    def capabilities(self) -> ProviderCapabilities:
        return self._capabilities

    async def initialize(self) -> None:
        self.initialized = True

    async def health_check(self) -> ProviderHealthCheck:
        return ProviderHealthCheck(provider=self.name, latency_ms=2.0)

    async def list_models(self) -> tuple[ProviderModel, ...]:
        return self._models

    async def generate(self, request: GenerationRequest) -> GenerationResponse:
        return GenerationResponse(
            provider=self.name,
            request_id=request.request_id or "generated",
            model=request.model or self._models[0].id,
            content="safe",
        )

    async def stream_generate(self, request: GenerationRequest) -> AsyncIterator[GenerationChunk]:
        yield GenerationChunk(
            provider=self.name,
            request_id=request.request_id or "generated",
            model=request.model or self._models[0].id,
            delta="safe",
        )

    async def close(self) -> None:
        self.closed = True


def request(**changes: object) -> GenerationRequest:
    values: dict[str, object] = {
        "messages": (ChatMessage(role="user", content="route safely"),),
        "request_id": "plugin-request",
    }
    values.update(changes)
    return GenerationRequest.model_validate(values, strict=True)


def router(*registrations: ProviderRegistration, priority: tuple[str, ...] = ()) -> ProviderRouter:
    return ProviderRouter(
        registrations=registrations,
        priority=priority,
        retry_backoff_seconds=0,
        max_retry_backoff_seconds=0,
        max_request_bytes=65_536,
    )


def test_local_plugin_registry_accepts_arbitrary_provider_identifier() -> None:
    registry = ProviderPluginRegistry()
    plugin = ProviderPlugin(
        name="future_provider",
        factory=lambda settings, transport: PluginProvider(
            "future_provider", ProviderCapabilities(chat=True), ()
        ),
        capabilities=ProviderCapabilities(chat=True),
    )

    registry.register(plugin)

    assert registry.get("future_provider") is plugin
    assert registry.discover() == (plugin,)


def test_package_discovery_loads_self_registered_builtin_plugins() -> None:
    names = {str(plugin.name) for plugin in discover_provider_plugins()}

    assert names == {"cerebras", "nvidia", "openrouter"}


def test_generic_provider_configuration_accepts_future_plugin_settings() -> None:
    settings = Settings(
        _env_file=None,
        providers={
            "future_provider": {
                "base_url": "https://future.example/v1",
                "enabled": False,
            }
        },
        provider_priority="future_provider",
    )

    assert "future_provider" in settings.providers
    assert settings.provider_priority_order == ("future_provider",)


def test_ranking_filters_models_by_task_capability() -> None:
    engine = ModelRankingEngine()
    chat = ProviderModel(
        id="chat",
        provider="chat_provider",
        capabilities=ProviderCapabilities(chat=True),
    )
    vision = ProviderModel(
        id="vision",
        provider="vision_provider",
        capabilities=ProviderCapabilities(chat=True, vision=True),
    )

    ranked = engine.rank(
        (chat, vision),
        request(task=RoutingTask.VISION),
        provider_health={"chat_provider": 1.0, "vision_provider": 1.0},
        soft_limited=frozenset(),
        explicit_priority=(),
    )

    assert [item.model.id for item in ranked] == ["vision"]


def test_dynamic_ranking_prefers_free_healthy_model() -> None:
    engine = ModelRankingEngine()
    paid = ProviderModel(
        id="paid",
        provider="paid_provider",
        capabilities=ProviderCapabilities(chat=True),
        input_cost_per_million_tokens_usd=20,
        output_cost_per_million_tokens_usd=20,
    )
    free = ProviderModel(
        id="free",
        provider="free_provider",
        capabilities=ProviderCapabilities(chat=True),
        is_free=True,
    )

    ranked = engine.rank(
        (paid, free),
        request(),
        provider_health={"paid_provider": 0.8, "free_provider": 1.0},
        soft_limited=frozenset(),
        explicit_priority=(),
    )

    assert ranked[0].model.id == "free"
    assert "free" in ranked[0].reason


def test_budget_manager_enforces_per_request_and_daily_limits() -> None:
    manager = ProviderBudgetManager(
        {
            "limited": BudgetPolicy(
                daily_limit_usd=1.0,
                per_request_limit_usd=0.5,
                soft_limit_ratio=0.8,
            )
        }
    )

    assert manager.permits("limited", 0.51) is False
    manager.record("limited", 0.8)
    snapshot = manager.snapshot("limited")

    assert snapshot.soft_limit_reached is True
    assert snapshot.hard_limit_reached is False
    assert manager.permits("limited", 0.3) is False


def test_router_selects_provider_by_required_capability() -> None:
    chat_caps = ProviderCapabilities(chat=True, streaming=True)
    vision_caps = ProviderCapabilities(chat=True, streaming=True, vision=True)
    chat_model = ProviderModel(id="chat", provider="chat_provider", capabilities=chat_caps)
    vision_model = ProviderModel(id="vision", provider="vision_provider", capabilities=vision_caps)
    service = router(
        ProviderRegistration(
            PluginProvider("chat_provider", chat_caps, (chat_model,)),
            0,
            model_template=chat_model,
        ),
        ProviderRegistration(
            PluginProvider("vision_provider", vision_caps, (vision_model,)),
            0,
            model_template=vision_model,
        ),
    )

    async def run() -> GenerationResponse:
        await service.initialize()
        return await service.generate(
            request(required_capabilities=frozenset({ProviderCapability.VISION}))
        )

    response = asyncio.run(run())

    assert response.provider == "vision_provider"
    assert service.last_selection is not None
    assert "capabilities matched" in service.last_selection.reason


def test_router_fails_over_when_primary_budget_is_exceeded() -> None:
    caps = ProviderCapabilities(chat=True, streaming=True)
    expensive = ProviderModel(
        id="expensive",
        provider="primary",
        capabilities=caps,
        input_cost_per_million_tokens_usd=1.0,
    )
    free = ProviderModel(id="free", provider="fallback", capabilities=caps, is_free=True)
    service = router(
        ProviderRegistration(
            PluginProvider("primary", caps, (expensive,)),
            0,
            model_template=expensive,
            budget_policy=BudgetPolicy(per_request_limit_usd=0.0),
        ),
        ProviderRegistration(
            PluginProvider("fallback", caps, (free,)),
            0,
            model_template=free,
        ),
        priority=("primary", "fallback"),
    )

    async def run() -> GenerationResponse:
        await service.initialize()
        return await service.generate(request(estimated_input_tokens=10))

    response = asyncio.run(run())

    assert response.provider == "fallback"
    assert service.active_provider == "fallback"


def test_startup_discovers_models_and_records_provider_health() -> None:
    caps = ProviderCapabilities(chat=True, streaming=True, reasoning=True)
    model = ProviderModel(id="discovered", provider="plugin", capabilities=caps)
    provider = PluginProvider("plugin", caps, (model,))
    service = router(
        ProviderRegistration(
            provider,
            0,
            capabilities=caps,
            startup_discovery=True,
        )
    )

    async def run() -> None:
        await service.initialize()

    asyncio.run(run())

    assert provider.initialized is True
    assert [item.id for item in service.discovered_models()] == ["discovered"]
    status = service.provider_status()[0]
    assert status.status is ProviderStatus.HEALTHY
    assert status.health_score > 0
