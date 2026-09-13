"""Offline contract tests for Cerebras, NVIDIA, and OpenRouter adapters."""

import asyncio
import json
from collections.abc import Callable

import httpx
import pytest

from toolbridge.providers.adapters.cerebras import CerebrasProvider
from toolbridge.providers.adapters.nvidia import NvidiaProvider
from toolbridge.providers.adapters.openai_compatible import OpenAICompatibleConfig
from toolbridge.providers.adapters.openrouter import OpenRouterProvider
from toolbridge.providers.application.ports import BaseProvider
from toolbridge.providers.domain.errors import ProviderError
from toolbridge.providers.domain.models import (
    ChatMessage,
    GenerationRequest,
    ProviderErrorCategory,
    ProviderName,
)

ProviderFactory = Callable[
    [OpenAICompatibleConfig, httpx.AsyncBaseTransport],
    BaseProvider,
]


def config() -> OpenAICompatibleConfig:
    """Return bounded test adapter configuration."""

    return OpenAICompatibleConfig(
        base_url="https://provider.test/v1",
        api_key="test-api-key",
        default_model="default-model",
        timeout_seconds=1,
        max_tokens=64,
        temperature=0.25,
        max_prompt_bytes=1_024,
        models_path="/models",
        chat_completions_path="/chat/completions",
    )


def request(**changes: object) -> GenerationRequest:
    """Return a normalized generation request."""

    values: dict[str, object] = {
        "messages": (ChatMessage(role="user", content="hello"),),
        "request_id": "request-1",
    }
    values.update(changes)
    return GenerationRequest.model_validate(values, strict=True)


def cerebras_factory(
    adapter_config: OpenAICompatibleConfig,
    transport: httpx.AsyncBaseTransport,
) -> BaseProvider:
    return CerebrasProvider(adapter_config, transport=transport)


def nvidia_factory(
    adapter_config: OpenAICompatibleConfig,
    transport: httpx.AsyncBaseTransport,
) -> BaseProvider:
    return NvidiaProvider(adapter_config, transport=transport)


def openrouter_factory(
    adapter_config: OpenAICompatibleConfig,
    transport: httpx.AsyncBaseTransport,
) -> BaseProvider:
    return OpenRouterProvider(
        adapter_config,
        http_referer="https://toolbridge.test",
        app_title="ToolBridge Tests",
        transport=transport,
    )


PROVIDERS = (
    (cerebras_factory, ProviderName.CEREBRAS),
    (nvidia_factory, ProviderName.NVIDIA),
    (openrouter_factory, ProviderName.OPENROUTER),
)


@pytest.mark.parametrize(("factory", "provider_name"), PROVIDERS)
def test_provider_generate_normalizes_response_and_authorization(
    factory: ProviderFactory,
    provider_name: ProviderName,
) -> None:
    def handler(http_request: httpx.Request) -> httpx.Response:
        assert http_request.url.path == "/v1/chat/completions"
        assert http_request.headers["Authorization"] == "Bearer test-api-key"
        body = json.loads(http_request.content)
        assert body == {
            "model": "default-model",
            "messages": [{"role": "user", "content": "hello"}],
            "max_tokens": 64,
            "temperature": 0.25,
            "stream": False,
        }
        return httpx.Response(
            200,
            json={
                "model": "resolved-model",
                "choices": [
                    {
                        "message": {"content": "normalized response"},
                        "finish_reason": "stop",
                    }
                ],
                "usage": {
                    "prompt_tokens": 3,
                    "completion_tokens": 2,
                    "total_tokens": 5,
                },
            },
        )

    provider = factory(config(), httpx.MockTransport(handler))

    async def run() -> object:
        await provider.initialize()
        response = await provider.generate(request())
        await provider.close()
        return response

    response = asyncio.run(run())

    assert response.provider is provider_name
    assert response.request_id == "request-1"
    assert response.content == "normalized response"
    assert response.usage.total_tokens == 5


def test_provider_lists_models_and_measures_health_latency() -> None:
    transport = httpx.MockTransport(
        lambda request: httpx.Response(
            200,
            json={"data": [{"id": "model-a"}, {"id": "model-b"}]},
            request=request,
        )
    )
    provider = CerebrasProvider(config(), transport=transport)

    async def run() -> tuple[object, object]:
        await provider.initialize()
        models = await provider.list_models()
        health = await provider.health_check()
        await provider.close()
        return models, health

    models, health = asyncio.run(run())

    assert [model.id for model in models] == ["model-a", "model-b"]
    assert all(model.provider is ProviderName.CEREBRAS for model in models)
    assert health.provider is ProviderName.CEREBRAS
    assert health.latency_ms >= 0


def test_provider_streams_normalized_sse_chunks() -> None:
    stream_body = (
        'data: {"model":"stream-model","choices":[{"delta":{"content":"one"},'
        '"finish_reason":null}]}\n\n'
        ": keep-alive\n\n"
        'data: {"model":"stream-model","choices":[{"delta":{"content":"two"},'
        '"finish_reason":"stop"}]}\n\n'
        "data: [DONE]\n\n"
    )
    transport = httpx.MockTransport(
        lambda request: httpx.Response(
            200,
            text=stream_body,
            headers={"Content-Type": "text/event-stream"},
            request=request,
        )
    )
    provider = NvidiaProvider(config(), transport=transport)

    async def run() -> list[object]:
        await provider.initialize()
        chunks = [chunk async for chunk in provider.stream_generate(request())]
        await provider.close()
        return chunks

    chunks = asyncio.run(run())

    assert [chunk.delta for chunk in chunks] == ["one", "two"]
    assert chunks[-1].finish_reason == "stop"
    assert all(chunk.provider is ProviderName.NVIDIA for chunk in chunks)


@pytest.mark.parametrize(
    ("status_code", "category"),
    (
        (400, ProviderErrorCategory.INVALID_REQUEST),
        (401, ProviderErrorCategory.AUTHENTICATION),
        (429, ProviderErrorCategory.RATE_LIMIT),
        (503, ProviderErrorCategory.UNAVAILABLE),
    ),
)
def test_provider_normalizes_http_errors_without_response_body(
    status_code: int,
    category: ProviderErrorCategory,
) -> None:
    transport = httpx.MockTransport(
        lambda request: httpx.Response(
            status_code,
            json={"error": {"message": "secret-provider-detail"}},
            request=request,
        )
    )
    provider = OpenRouterProvider(config(), transport=transport)

    async def run() -> ProviderError:
        await provider.initialize()
        with pytest.raises(ProviderError) as caught:
            await provider.generate(request())
        await provider.close()
        return caught.value

    error = asyncio.run(run())

    assert error.category is category
    assert "secret-provider-detail" not in str(error)
    assert "test-api-key" not in str(error)


def test_provider_normalizes_transport_timeout() -> None:
    def timeout(http_request: httpx.Request) -> httpx.Response:
        raise httpx.ReadTimeout("secret timeout detail", request=http_request)

    provider = CerebrasProvider(config(), transport=httpx.MockTransport(timeout))

    async def run() -> ProviderError:
        await provider.initialize()
        with pytest.raises(ProviderError) as caught:
            await provider.generate(request())
        await provider.close()
        return caught.value

    error = asyncio.run(run())

    assert error.category is ProviderErrorCategory.TIMEOUT
    assert "secret timeout detail" not in str(error)


def test_provider_rejects_malformed_response() -> None:
    provider = NvidiaProvider(
        config(),
        transport=httpx.MockTransport(
            lambda request: httpx.Response(
                200,
                json={"choices": [{"message": {"unexpected": True}}]},
                request=request,
            )
        ),
    )

    async def run() -> ProviderError:
        await provider.initialize()
        with pytest.raises(ProviderError) as caught:
            await provider.generate(request())
        await provider.close()
        return caught.value

    error = asyncio.run(run())

    assert error.category is ProviderErrorCategory.INVALID_RESPONSE


def test_provider_enforces_configured_token_and_prompt_limits() -> None:
    provider = CerebrasProvider(
        config(),
        transport=httpx.MockTransport(lambda request: httpx.Response(500, request=request)),
    )

    async def run() -> tuple[ProviderError, ProviderError]:
        await provider.initialize()
        with pytest.raises(ProviderError) as token_error:
            await provider.generate(request(max_tokens=65))
        oversized = GenerationRequest(
            messages=(ChatMessage(role="user", content="x" * 2_000),),
            request_id="request-2",
        )
        with pytest.raises(ProviderError) as prompt_error:
            await provider.generate(oversized)
        await provider.close()
        return token_error.value, prompt_error.value

    token_error, prompt_error = asyncio.run(run())

    assert token_error.category is ProviderErrorCategory.INVALID_REQUEST
    assert prompt_error.category is ProviderErrorCategory.INVALID_REQUEST


def test_openrouter_list_models_parses_per_model_pricing() -> None:
    """OpenRouter adapter reads per-model cost and marks :free models correctly."""

    api_response = {
        "data": [
            {
                "id": "some/model:free",
                "context_length": 131072,
                "pricing": {"prompt": "0", "completion": "0"},
            },
            {
                "id": "some/paid-model",
                "context_length": 32768,
                "pricing": {"prompt": "0.000003", "completion": "0.000015"},
            },
            {
                "id": "some/no-pricing-model",
                "context_length": 8192,
            },
            {
                "id": "openrouter/auto",
                "context_length": 200000,
                "pricing": {"prompt": "-1", "completion": "-1"},
            },
        ]
    }
    transport = httpx.MockTransport(
        lambda request: httpx.Response(200, json=api_response, request=request)
    )
    provider = OpenRouterProvider(config(), transport=transport)

    async def run() -> tuple[object, ...]:
        await provider.initialize()
        models = await provider.list_models()
        await provider.close()
        return models

    models = asyncio.run(run())

    assert len(models) == 4

    free_model = models[0]
    assert free_model.id == "some/model:free"
    assert free_model.is_free is True
    assert free_model.input_cost_per_million_tokens_usd == 0.0
    assert free_model.output_cost_per_million_tokens_usd == 0.0
    assert free_model.context_window == 131072

    paid_model = models[1]
    assert paid_model.id == "some/paid-model"
    assert paid_model.is_free is False
    assert round(paid_model.input_cost_per_million_tokens_usd, 4) == round(3.0, 4)
    assert round(paid_model.output_cost_per_million_tokens_usd, 4) == round(15.0, 4)
    assert paid_model.context_window == 32768

    no_pricing_model = models[2]
    assert no_pricing_model.id == "some/no-pricing-model"
    assert no_pricing_model.is_free is True
    assert no_pricing_model.context_window == 8192

    auto_model = models[3]
    assert auto_model.id == "openrouter/auto"
    assert auto_model.input_cost_per_million_tokens_usd == 0.0
    assert auto_model.output_cost_per_million_tokens_usd == 0.0
    assert auto_model.is_free is True
