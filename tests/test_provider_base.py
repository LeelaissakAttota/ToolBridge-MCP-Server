"""Tests for ProviderBase abstract class."""

import pytest
from mcp_server.providers.base import ProviderBase, ProviderConfig


def test_provider_base_is_abstract():
    """ProviderBase should be an abstract base class."""
    assert hasattr(ProviderBase, '__abstractmethods__')
    expected_methods = {
        'name', 'default_model', '_initialize_client',
        'generate', 'stream', 'health_check',
        'available_models', 'count_tokens', 'estimate_cost'
    }
    assert set(ProviderBase.__abstractmethods__) == expected_methods


def test_provider_base_cannot_instantiate():
    """Direct instantiation of ProviderBase should raise TypeError."""
    with pytest.raises(TypeError):
        ProviderBase(ProviderConfig())


def test_provider_base_subclass_must_implement():
    """Subclass without implementing abstract methods should raise TypeError."""

    class IncompleteProvider(ProviderBase):
        pass

    with pytest.raises(TypeError):
        IncompleteProvider(ProviderConfig())


def test_provider_base_concrete_subclass():
    """Fully implemented subclass should be instantiable."""

    class ConcreteProvider(ProviderBase):
        @property
        def name(self) -> str:
            return "test"

        @property
        def default_model(self) -> str:
            return "test-model"

        async def _initialize_client(self) -> None:
            pass

        async def generate(self, request):
            from mcp_server.providers.base import GenerationResponse
            return GenerationResponse(
                text="test", model="test-model",
                prompt_tokens=10, completion_tokens=5,
                total_tokens=15, cost_estimate=0.0,
                finish_reason="stop", latency_ms=10.0, provider="test"
            )

        async def stream(self, request):
            yield "test"

        async def health_check(self):
            from mcp_server.providers.base import HealthCheckResult
            return HealthCheckResult(healthy=True, latency_ms=10.0)

        async def available_models(self):
            from mcp_server.providers.base import ModelInfo
            return [ModelInfo(name="test-model", max_tokens=4096)]

        async def count_tokens(self, text: str, model: str = None) -> int:
            return len(text) // 4

        async def estimate_cost(self, request):
            return 0.001

    provider = ConcreteProvider(ProviderConfig())
    assert provider.name == "test"
    assert provider.default_model == "test-model"