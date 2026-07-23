"""Tests for CerebrasProvider."""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from mcp_server.providers.cerebras import CerebrasProvider
from mcp_server.providers.base import ProviderConfig, GenerationRequest, GenerationResponse


class MockAsyncContextManager:
    """Helper to create proper async context manager mocks."""
    
    def __init__(self, enter_value=None, exit_value=None):
        self._enter_value = enter_value
        self._exit_value = exit_value
    
    async def __aenter__(self):
        return self._enter_value
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        return self._exit_value


class TestCerebrasProvider:
    """Tests for CerebrasProvider."""

    @pytest.fixture
    def config(self):
        return ProviderConfig(
            api_key="test-key",
            default_model="llama3.1-70b",
            timeout=30.0,
            max_retries=3,
        )

    @pytest.fixture
    def provider(self, config):
        return CerebrasProvider(config)

    def test_provider_name(self, provider):
        assert provider.name == "cerebras"

    def test_default_model(self, provider):
        assert provider.default_model == "llama3.1-70b"

    def test_model_max_tokens(self, provider):
        assert provider.MODEL_MAX_TOKENS["llama3.1-8b"] == 8192
        assert provider.MODEL_MAX_TOKENS["llama3.1-70b"] == 8192

    def test_model_pricing(self, provider):
        assert "llama3.1-8b" in provider.MODEL_PRICING
        assert "llama3.1-70b" in provider.MODEL_PRICING
        pricing = provider.MODEL_PRICING["llama3.1-8b"]
        assert "prompt" in pricing
        assert "completion" in pricing

    @pytest.mark.asyncio
    async def test_initialize_client(self, provider):
        with patch("aiohttp.ClientSession") as mock_session:
            mock_session_instance = AsyncMock()
            mock_session.return_value = mock_session_instance
            await provider._initialize_client()
            assert provider._session is not None
            assert provider._initialized is True

    @pytest.mark.asyncio
    async def test_generate_success(self, provider):
        """Test successful text generation."""
        mock_response = AsyncMock()
        mock_response.status = 200
        mock_response.json = AsyncMock(return_value={
            "choices": [{"message": {"content": "Hello world"}, "finish_reason": "stop"}],
            "usage": {"prompt_tokens": 10, "completion_tokens": 5, "total_tokens": 15}
        })

        # Create proper async context manager
        mock_cm = MagicMock()
        mock_cm.__aenter__ = AsyncMock(return_value=mock_response)
        mock_cm.__aexit__ = AsyncMock(return_value=None)

        provider._session = MagicMock()
        provider._session.post = MagicMock(return_value=mock_cm)
        provider._initialized = True

        request = GenerationRequest(prompt="Hello", model="llama3.1-8b")
        response = await provider.generate(request)

        assert isinstance(response, GenerationResponse)
        assert response.text == "Hello world"
        assert response.model == "llama3.1-8b"
        assert response.prompt_tokens == 10
        assert response.completion_tokens == 5
        assert response.total_tokens == 15

    @pytest.mark.asyncio
    async def test_generate_retry_on_429(self, provider):
        """Test retry on rate limit (429)."""
        # First call returns 429
        mock_response_429 = AsyncMock()
        mock_response_429.status = 429
        mock_cm_429 = MagicMock()
        mock_cm_429.__aenter__ = AsyncMock(return_value=mock_response_429)
        mock_cm_429.__aexit__ = AsyncMock(return_value=None)

        # Second call returns 200
        mock_response_200 = AsyncMock()
        mock_response_200.status = 200
        mock_response_200.json = AsyncMock(return_value={
            "choices": [{"message": {"content": "Success"}, "finish_reason": "stop"}],
            "usage": {"prompt_tokens": 5, "completion_tokens": 3, "total_tokens": 8}
        })
        mock_cm_200 = MagicMock()
        mock_cm_200.__aenter__ = AsyncMock(return_value=mock_response_200)
        mock_cm_200.__aexit__ = AsyncMock(return_value=None)

        provider._session = MagicMock()
        provider._session.post = MagicMock(side_effect=[mock_cm_429, mock_cm_200])
        provider._initialized = True

        request = GenerationRequest(prompt="Test", model="llama3.1-8b")
        response = await provider.generate(request)

        assert response.text == "Success"

    @pytest.mark.asyncio
    async def test_stream(self, provider):
        """Test streaming generation."""
        async def mock_stream():
            lines = [
                b'data: {"choices": [{"delta": {"content": "Hello"}}]}',
                b'data: {"choices": [{"delta": {"content": " world"}}]}',
                b"data: [DONE]",
            ]
            for line in lines:
                yield line

        mock_response = AsyncMock()
        mock_response.status = 200
        mock_response.content = mock_stream()

        mock_cm = MagicMock()
        mock_cm.__aenter__ = AsyncMock(return_value=mock_response)
        mock_cm.__aexit__ = AsyncMock(return_value=None)

        provider._session = MagicMock()
        provider._session.post = MagicMock(return_value=mock_cm)
        provider._initialized = True

        request = GenerationRequest(prompt="Hello", stream=True, model="llama3.1-8b")
        chunks = []
        async for chunk in provider.stream(request):
            chunks.append(chunk)

        assert chunks == ["Hello", " world"]

    @pytest.mark.asyncio
    async def test_health_check_healthy(self, provider):
        """Test health check when healthy."""
        mock_response = AsyncMock()
        mock_response.status = 200
        mock_response.json = AsyncMock(return_value={"data": [{"id": "model1"}, {"id": "model2"}]})

        mock_cm = MagicMock()
        mock_cm.__aenter__ = AsyncMock(return_value=mock_response)
        mock_cm.__aexit__ = AsyncMock(return_value=None)

        provider._session = MagicMock()
        provider._session.get = MagicMock(return_value=mock_cm)
        provider._initialized = True

        result = await provider.health_check()

        assert result.healthy is True
        assert result.latency_ms > 0
        assert "model1" in result.available_models

    @pytest.mark.asyncio
    async def test_health_check_unhealthy(self, provider):
        """Test health check when unhealthy."""
        mock_response = AsyncMock()
        mock_response.status = 500

        mock_cm = MagicMock()
        mock_cm.__aenter__ = AsyncMock(return_value=mock_response)
        mock_cm.__aexit__ = AsyncMock(return_value=None)

        provider._session = MagicMock()
        provider._session.get = MagicMock(return_value=mock_cm)
        provider._initialized = True

        result = await provider.health_check()

        assert result.healthy is False
        assert result.error is not None

    @pytest.mark.asyncio
    async def test_count_tokens(self, provider):
        """Test token counting."""
        text = "Hello world"
        count = await provider.count_tokens(text)
        assert count == len(text) // 4

    @pytest.mark.asyncio
    async def test_estimate_cost(self, provider):
        """Test cost estimation."""
        request = GenerationRequest(prompt="Hello world", max_tokens=100, model="llama3.1-8b")
        cost = await provider.estimate_cost(request)

        assert cost >= 0
        assert isinstance(cost, float)

    @pytest.mark.asyncio
    async def test_available_models(self, provider):
        """Test fetching available models."""
        mock_response = AsyncMock()
        mock_response.status = 200
        mock_response.json = AsyncMock(return_value={
            "data": [
                {"id": "llama3.1-8b"},
                {"id": "llama3.1-70b"}
            ]
        })

        mock_cm = MagicMock()
        mock_cm.__aenter__ = AsyncMock(return_value=mock_response)
        mock_cm.__aexit__ = AsyncMock(return_value=None)

        provider._session = MagicMock()
        provider._session.get = MagicMock(return_value=mock_cm)
        provider._initialized = True

        models = await provider.available_models()

        assert len(models) == 2
        assert models[0].name == "llama3.1-8b"
        assert models[1].name == "llama3.1-70b"

    @pytest.mark.asyncio
    async def test_count_tokens_with_model(self, provider):
        """Test count_tokens with model parameter."""
        count = await provider.count_tokens("Hello", "llama3.1-8b")
        assert count == 1  # "Hello" = 5 chars // 4 = 1

    @pytest.mark.asyncio
    async def test_estimate_cost_with_custom_model(self, provider):
        """Test cost estimation with custom model."""
        request = GenerationRequest(prompt="Test", max_tokens=50, model="llama3.1-70b")
        cost = await provider.estimate_cost(request)
        assert cost > 0

    @pytest.mark.asyncio
    async def test_close_session(self, provider):
        """Test closing session."""
        mock_session = AsyncMock()
        mock_session.closed = False
        provider._session = mock_session
        provider._initialized = True

        await provider.close()

        assert mock_session.close.called
        assert provider._initialized is False

    def test_get_token_usage(self, provider):
        """Test getting token usage."""
        usage = provider.get_token_usage()
        assert usage.prompt_tokens == 0
        assert usage.completion_tokens == 0

    def test_get_cost_estimate(self, provider):
        """Test getting cost estimate."""
        assert provider.get_cost_estimate() == 0.0