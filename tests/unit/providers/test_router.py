"""Unit tests for provider selection, retries, failover, and health state."""

import asyncio
from collections.abc import AsyncIterator
from typing import Any

import pytest

from toolbridge.providers.application.ports import BaseProvider
from toolbridge.providers.application.router import ProviderRegistration, ProviderRouter
from toolbridge.providers.domain.errors import ProviderError, ProviderRoutingError
from toolbridge.providers.domain.models import (
    ChatMessage,
    GenerationChunk,
    GenerationRequest,
    GenerationResponse,
    ProviderErrorCategory,
    ProviderHealthCheck,
    ProviderModel,
    ProviderName,
    ProviderStatus,
)


class FakeProvider(BaseProvider):
    """Deterministic provider with queued outcomes."""

    def __init__(self, name: ProviderName) -> None:
        self._name = name
        self.generate_actions: list[GenerationResponse | Exception] = []
        self.stream_plans: list[list[str | Exception]] = []
        self.health_error: Exception | None = None
        self.generate_calls = 0
        self.stream_calls = 0
        self.health_calls = 0
        self.initialized = False
        self.closed = False

    @property
    def name(self) -> ProviderName:
        return self._name

    async def initialize(self) -> None:
        self.initialized = True
        self.closed = False

    async def health_check(self) -> ProviderHealthCheck:
        self.health_calls += 1
        if self.health_error is not None:
            raise self.health_error
        return ProviderHealthCheck(provider=self.name, latency_ms=1.0)

    async def list_models(self) -> tuple[ProviderModel, ...]:
        return (ProviderModel(id=f"{self.name}-model", provider=self.name),)

    async def generate(self, request: GenerationRequest) -> GenerationResponse:
        self.generate_calls += 1
        if self.generate_actions:
            action = self.generate_actions.pop(0)
            if isinstance(action, Exception):
                raise action
            return action
        assert request.request_id is not None
        return GenerationResponse(
            provider=self.name,
            request_id=request.request_id,
            model=request.model or "test-model",
            content=f"response-from-{self.name}",
        )

    def stream_generate(self, request: GenerationRequest) -> AsyncIterator[GenerationChunk]:
        self.stream_calls += 1
        plan = self.stream_plans.pop(0) if self.stream_plans else ["chunk"]

        async def stream() -> AsyncIterator[GenerationChunk]:
            assert request.request_id is not None
            for item in plan:
                if isinstance(item, Exception):
                    raise item
                yield GenerationChunk(
                    provider=self.name,
                    request_id=request.request_id,
                    model=request.model or "test-model",
                    delta=item,
                )

        return stream()

    async def close(self) -> None:
        self.closed = True


class RecordingProviderLogger:
    """Capture allowlisted provider events."""

    def __init__(self) -> None:
        self.events: list[dict[str, Any]] = []

    def record(self, **event: Any) -> None:
        self.events.append(event)


class RecordingUsageRecorder:
    """Capture normalized generation usage without request content."""

    def __init__(self) -> None:
        self.events: list[dict[str, Any]] = []

    def record_generation(self, **event: Any) -> None:
        self.events.append(event)


def request() -> GenerationRequest:
    """Build a valid provider-neutral test request."""

    return GenerationRequest(
        messages=(ChatMessage(role="user", content="test prompt"),),
        request_id="request-1",
    )


def build_router(
    providers: tuple[FakeProvider, ...],
    *,
    retry_counts: tuple[int, ...] | None = None,
    logger: RecordingProviderLogger | None = None,
    usage: RecordingUsageRecorder | None = None,
) -> ProviderRouter:
    """Build an isolated router in the supplied priority order."""

    counts = retry_counts or tuple(0 for _ in providers)
    return ProviderRouter(
        registrations=tuple(
            ProviderRegistration(provider=provider, retry_count=count)
            for provider, count in zip(providers, counts, strict=True)
        ),
        priority=tuple(provider.name for provider in providers),
        retry_backoff_seconds=0,
        max_retry_backoff_seconds=0,
        max_request_bytes=4_096,
        event_logger=logger,
        usage_recorder=usage,
    )


def test_router_selects_primary_provider() -> None:
    cerebras = FakeProvider(ProviderName.CEREBRAS)
    nvidia = FakeProvider(ProviderName.NVIDIA)
    router = build_router((cerebras, nvidia))

    async def run() -> GenerationResponse:
        await router.initialize()
        return await router.generate(request())

    response = asyncio.run(run())

    assert response.provider is ProviderName.CEREBRAS
    assert router.active_provider is ProviderName.CEREBRAS
    assert cerebras.generate_calls == 1
    assert nvidia.generate_calls == 0


def test_router_records_normalized_generation_usage() -> None:
    cerebras = FakeProvider(ProviderName.CEREBRAS)
    usage = RecordingUsageRecorder()
    cerebras.generate_actions.append(
        GenerationResponse(
            provider=ProviderName.CEREBRAS,
            request_id="request-1",
            model="test-model",
            content="safe response",
            usage={
                "input_tokens": 12,
                "output_tokens": 8,
                "total_tokens": 20,
            },
        )
    )
    router = build_router((cerebras,), usage=usage)

    async def run() -> None:
        await router.initialize()
        await router.generate(request())

    asyncio.run(run())

    assert usage.events == [
        {
            "provider": ProviderName.CEREBRAS,
            "input_tokens": 12,
            "output_tokens": 8,
            "total_tokens": 20,
        }
    ]


def test_router_fails_over_when_active_provider_is_unavailable() -> None:
    cerebras = FakeProvider(ProviderName.CEREBRAS)
    nvidia = FakeProvider(ProviderName.NVIDIA)
    cerebras.generate_actions.append(
        ProviderError(ProviderErrorCategory.UNAVAILABLE, ProviderName.CEREBRAS)
    )
    router = build_router((cerebras, nvidia))

    async def run() -> GenerationResponse:
        await router.initialize()
        return await router.generate(request())

    response = asyncio.run(run())

    assert response.provider is ProviderName.NVIDIA
    assert router.active_provider is ProviderName.NVIDIA
    assert cerebras.generate_calls == 1
    assert nvidia.generate_calls == 1


def test_router_retries_retryable_error_before_failover() -> None:
    cerebras = FakeProvider(ProviderName.CEREBRAS)
    timeout_error = ProviderError(
        ProviderErrorCategory.TIMEOUT,
        ProviderName.CEREBRAS,
    )
    cerebras.generate_actions.extend([timeout_error, timeout_error])
    router = build_router((cerebras,), retry_counts=(2,))

    async def run() -> GenerationResponse:
        await router.initialize()
        return await router.generate(request())

    response = asyncio.run(run())

    assert response.provider is ProviderName.CEREBRAS
    assert cerebras.generate_calls == 3


def test_invalid_request_is_not_retried_or_failed_over() -> None:
    cerebras = FakeProvider(ProviderName.CEREBRAS)
    nvidia = FakeProvider(ProviderName.NVIDIA)
    cerebras.generate_actions.append(
        ProviderError(ProviderErrorCategory.INVALID_REQUEST, ProviderName.CEREBRAS)
    )
    router = build_router((cerebras, nvidia), retry_counts=(2, 0))

    async def run() -> None:
        await router.initialize()
        with pytest.raises(ProviderError) as caught:
            await router.generate(request())
        assert caught.value.category is ProviderErrorCategory.INVALID_REQUEST

    asyncio.run(run())

    assert cerebras.generate_calls == 1
    assert nvidia.generate_calls == 0
    assert router.provider_status()[0].status is ProviderStatus.UNINITIALIZED


def test_health_checks_update_status_timestamps_and_active_provider() -> None:
    cerebras = FakeProvider(ProviderName.CEREBRAS)
    nvidia = FakeProvider(ProviderName.NVIDIA)
    cerebras.health_error = ProviderError(
        ProviderErrorCategory.AUTHENTICATION,
        ProviderName.CEREBRAS,
    )
    router = build_router((cerebras, nvidia))

    async def run() -> tuple[Any, ...]:
        await router.initialize()
        return await router.health_check()

    statuses = asyncio.run(run())

    assert router.active_provider is ProviderName.NVIDIA
    assert statuses[0].status is ProviderStatus.UNAVAILABLE
    assert statuses[0].last_failed_request is not None
    assert statuses[0].last_error_category is ProviderErrorCategory.AUTHENTICATION
    assert statuses[1].status is ProviderStatus.HEALTHY
    assert statuses[1].latency_ms is not None
    assert statuses[1].last_successful_request is not None


def test_stream_fails_over_before_first_chunk() -> None:
    cerebras = FakeProvider(ProviderName.CEREBRAS)
    nvidia = FakeProvider(ProviderName.NVIDIA)
    cerebras.stream_plans.append(
        [ProviderError(ProviderErrorCategory.UNAVAILABLE, ProviderName.CEREBRAS)]
    )
    nvidia.stream_plans.append(["fallback"])
    router = build_router((cerebras, nvidia))

    async def run() -> list[GenerationChunk]:
        await router.initialize()
        return [chunk async for chunk in router.stream_generate(request())]

    chunks = asyncio.run(run())

    assert [chunk.delta for chunk in chunks] == ["fallback"]
    assert router.active_provider is ProviderName.NVIDIA


def test_stream_records_provider_request_without_inventing_token_usage() -> None:
    cerebras = FakeProvider(ProviderName.CEREBRAS)
    usage = RecordingUsageRecorder()
    router = build_router((cerebras,), usage=usage)

    async def run() -> None:
        await router.initialize()
        _ = [chunk async for chunk in router.stream_generate(request())]

    asyncio.run(run())

    assert usage.events == [
        {
            "provider": ProviderName.CEREBRAS,
            "input_tokens": 0,
            "output_tokens": 0,
            "total_tokens": 0,
        }
    ]


def test_stream_does_not_fail_over_after_emitting_content() -> None:
    cerebras = FakeProvider(ProviderName.CEREBRAS)
    nvidia = FakeProvider(ProviderName.NVIDIA)
    stream_error = ProviderError(
        ProviderErrorCategory.UNAVAILABLE,
        ProviderName.CEREBRAS,
    )
    cerebras.stream_plans.append(["partial", stream_error])
    router = build_router((cerebras, nvidia))

    async def run() -> list[str]:
        await router.initialize()
        chunks: list[str] = []
        with pytest.raises(ProviderError):
            async for chunk in router.stream_generate(request()):
                chunks.append(chunk.delta)
        return chunks

    chunks = asyncio.run(run())

    assert chunks == ["partial"]
    assert nvidia.stream_calls == 0


def test_router_lifecycle_closes_every_provider() -> None:
    cerebras = FakeProvider(ProviderName.CEREBRAS)
    nvidia = FakeProvider(ProviderName.NVIDIA)
    router = build_router((cerebras, nvidia))

    async def run() -> None:
        await router.initialize()
        await router.close()

    asyncio.run(run())

    assert cerebras.initialized and cerebras.closed
    assert nvidia.initialized and nvidia.closed
    assert router.active_provider is None
    assert all(status.status is ProviderStatus.CLOSED for status in router.provider_status())


def test_router_without_configured_providers_fails_safely() -> None:
    router = build_router(())

    async def run() -> None:
        await router.initialize()
        with pytest.raises(ProviderRoutingError):
            await router.generate(request())

    asyncio.run(run())


class _PlainChunkIterator:
    """AsyncIterator without aclose(), as a third-party plugin might return."""

    def __init__(self, provider: ProviderName, deltas: list[str]) -> None:
        self._provider = provider
        self._deltas = list(deltas)

    def __aiter__(self) -> "_PlainChunkIterator":
        return self

    async def __anext__(self) -> GenerationChunk:
        if not self._deltas:
            raise StopAsyncIteration
        return GenerationChunk(
            provider=self._provider,
            request_id="request-1",
            model="plain-model",
            delta=self._deltas.pop(0),
        )


class PlainIteratorProvider(FakeProvider):
    def stream_generate(self, request: GenerationRequest) -> AsyncIterator[GenerationChunk]:
        del request
        return _PlainChunkIterator(self.name, ["a", "b"])


def test_stream_supports_iterators_without_aclose_and_missing_request_id() -> None:
    router = build_router((PlainIteratorProvider(ProviderName.CEREBRAS),))

    async def run() -> list[GenerationChunk]:
        await router.initialize()
        no_id = GenerationRequest(messages=(ChatMessage(role="user", content="hi"),))
        return [chunk async for chunk in router.stream_generate(no_id)]

    assert [chunk.delta for chunk in asyncio.run(run())] == ["a", "b"]


class SlowDripProvider(FakeProvider):
    """Emits chunks forever with small gaps, like a slow-drip upstream."""

    def __init__(self, name: ProviderName, *, first_delay: float = 0.0) -> None:
        super().__init__(name)
        self._first_delay = first_delay

    def stream_generate(self, request: GenerationRequest) -> AsyncIterator[GenerationChunk]:
        del request
        first_delay = self._first_delay

        async def stream() -> AsyncIterator[GenerationChunk]:
            await asyncio.sleep(first_delay)
            while True:
                yield GenerationChunk(
                    provider=self.name, request_id="request-1", model="slow", delta="."
                )
                await asyncio.sleep(0.02)

        return stream()


def _router_with_stream_timeout(provider: FakeProvider, seconds: float) -> ProviderRouter:
    return ProviderRouter(
        registrations=(ProviderRegistration(provider=provider, retry_count=0),),
        priority=(provider.name,),
        retry_backoff_seconds=0,
        max_retry_backoff_seconds=0,
        max_request_bytes=4_096,
        stream_timeout_seconds=seconds,
    )


def test_stream_enforces_overall_deadline_on_slow_drip() -> None:
    router = _router_with_stream_timeout(SlowDripProvider(ProviderName.CEREBRAS), 0.2)
    received: list[str] = []

    async def run() -> None:
        await router.initialize()
        async for chunk in router.stream_generate(request()):
            received.append(chunk.delta)

    with pytest.raises(ProviderError) as caught:
        asyncio.run(asyncio.wait_for(run(), 5))

    assert caught.value.category is ProviderErrorCategory.TIMEOUT
    assert 1 <= len(received) < 50


def test_stream_deadline_covers_time_to_first_chunk() -> None:
    provider = SlowDripProvider(ProviderName.CEREBRAS, first_delay=1.0)
    router = _router_with_stream_timeout(provider, 0.1)

    async def run() -> list[GenerationChunk]:
        await router.initialize()
        return [chunk async for chunk in router.stream_generate(request())]

    with pytest.raises(ProviderError) as caught:
        asyncio.run(asyncio.wait_for(run(), 5))
    assert caught.value.category is ProviderErrorCategory.TIMEOUT


def test_stream_timeout_must_be_positive() -> None:
    with pytest.raises(ValueError):
        _router_with_stream_timeout(FakeProvider(ProviderName.CEREBRAS), 0)
