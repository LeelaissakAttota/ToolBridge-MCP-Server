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


def test_provider_config_defaults():
    """ProviderConfig should have sensible defaults."""
    config = ProviderConfig()
    assert config.api_key == ""
    assert config.base_url is None
    assert config.timeout == 30.0
    assert config.max_retries == 3
    assert config.default_model is None
    assert config.extra_headers == {}
    assert config.extra_params == {}


def test_provider_config_custom_values():
    """ProviderConfig should accept custom values."""
    config = ProviderConfig(
        api_key="test-key",
        base_url="https://api.test.com",
        timeout=60.0,
        max_retries=5,
        default_model="test-model",
        extra_headers={"X-Custom": "value"},
        extra_params={"custom": "param"},
    )
    assert config.api_key == "test-key"
    assert config.base_url == "https://api.test.com"
    assert config.timeout == 60.0
    assert config.max_retries == 5
    assert config.default_model == "test-model"
    assert config.extra_headers == {"X-Custom": "value"}
    assert config.extra_params == {"custom": "param"}


def test_generation_request_defaults():
    """GenerationRequest should have sensible defaults."""
    from mcp_server.providers.base import GenerationRequest
    request = GenerationRequest(prompt="Hello")
    assert request.prompt == "Hello"
    assert request.model is None
    assert request.max_tokens is None
    assert request.temperature == 0.7
    assert request.top_p == 1.0
    assert request.top_k is None
    assert request.stop is None
    assert request.stream is False
    assert request.extra_params == {}


def test_generation_request_custom():
    """GenerationRequest should accept custom values."""
    from mcp_server.providers.base import GenerationRequest
    request = GenerationRequest(
        prompt="Hello",
        model="gpt-4",
        max_tokens=100,
        temperature=0.5,
        top_p=0.9,
        top_k=50,
        stop=["END"],
        stream=True,
        extra_params={"custom": "value"},
    )
    assert request.prompt == "Hello"
    assert request.model == "gpt-4"
    assert request.max_tokens == 100
    assert request.temperature == 0.5
    assert request.top_p == 0.9
    assert request.top_k == 50
    assert request.stop == ["END"]
    assert request.stream is True
    assert request.extra_params == {"custom": "value"}


def test_generation_response_fields():
    """GenerationResponse should have all required fields."""
    from mcp_server.providers.base import GenerationResponse
    response = GenerationResponse(
        text="Test response",
        model="gpt-4",
        prompt_tokens=100,
        completion_tokens=50,
        total_tokens=150,
        cost_estimate=0.002,
        finish_reason="stop",
        latency_ms=500.0,
        provider="openrouter",
    )
    assert response.text == "Test response"
    assert response.model == "gpt-4"
    assert response.prompt_tokens == 100
    assert response.completion_tokens == 50
    assert response.total_tokens == 150
    assert response.cost_estimate == 0.002
    assert response.finish_reason == "stop"
    assert response.latency_ms == 500.0
    assert response.provider == "openrouter"


def test_health_check_result_fields():
    """HealthCheckResult should have all required fields."""
    from mcp_server.providers.base import HealthCheckResult
    result = HealthCheckResult(
        healthy=True,
        latency_ms=50.0,
        available_models=["model1", "model2"],
    )
    assert result.healthy is True
    assert result.latency_ms == 50.0
    assert result.available_models == ["model1", "model2"]
    assert result.error is None


def test_model_info_fields():
    """ModelInfo should have all required fields."""
    from mcp_server.providers.base import ModelInfo
    model = ModelInfo(
        name="gpt-4",
        max_tokens=8192,
        cost_per_1k_prompt=0.01,
        cost_per_1k_completion=0.03,
        supports_streaming=True,
        context_window=8192,
    )
    assert model.name == "gpt-4"
    assert model.max_tokens == 8192
    assert model.cost_per_1k_prompt == 0.01
    assert model.cost_per_1k_completion == 0.03
    assert model.supports_streaming is True
    assert model.context_window == 8192


def test_token_usage_defaults():
    """TokenUsage should have zero defaults."""
    from mcp_server.providers.base import TokenUsage
    usage = TokenUsage()
    assert usage.prompt_tokens == 0
    assert usage.completion_tokens == 0
    assert usage.total_tokens == 0
    assert usage.cost_estimate == 0.0