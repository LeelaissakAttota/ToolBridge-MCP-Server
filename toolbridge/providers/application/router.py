"""Provider selection, retry, failover, and health-state application service."""

import asyncio
import json
from collections.abc import AsyncIterator, Awaitable, Callable
from dataclasses import dataclass
from datetime import UTC, datetime
from time import perf_counter
from typing import TypeVar
from uuid import uuid4

from toolbridge.providers.application.ports import (
    BaseProvider,
    NullProviderEventLogger,
    NullProviderUsageRecorder,
    ProviderEventLogger,
    ProviderUsageRecorder,
)
from toolbridge.providers.domain.errors import ProviderError, ProviderRoutingError
from toolbridge.providers.domain.models import (
    GenerationChunk,
    GenerationRequest,
    GenerationResponse,
    ProviderErrorCategory,
    ProviderModel,
    ProviderName,
    ProviderStatus,
    ProviderStatusSnapshot,
)

T = TypeVar("T")


@dataclass(frozen=True, slots=True)
class ProviderRegistration:
    """A provider and its configured retry allowance."""

    provider: BaseProvider
    retry_count: int

    def __post_init__(self) -> None:
        if self.retry_count < 0:
            raise ValueError("retry_count cannot be negative")


@dataclass(slots=True)
class _ProviderState:
    status: ProviderStatus = ProviderStatus.UNINITIALIZED
    latency_ms: float | None = None
    last_successful_request: datetime | None = None
    last_failed_request: datetime | None = None
    last_error_category: ProviderErrorCategory | None = None


class ProviderRouter:
    """Route provider-neutral requests using configured priority and safe failover."""

    def __init__(
        self,
        registrations: tuple[ProviderRegistration, ...],
        priority: tuple[ProviderName, ...],
        *,
        retry_backoff_seconds: float,
        max_retry_backoff_seconds: float,
        max_request_bytes: int,
        event_logger: ProviderEventLogger | None = None,
        usage_recorder: ProviderUsageRecorder | None = None,
    ) -> None:
        if retry_backoff_seconds < 0:
            raise ValueError("retry_backoff_seconds cannot be negative")
        if max_retry_backoff_seconds < retry_backoff_seconds:
            raise ValueError("max retry backoff cannot be smaller than initial backoff")
        if max_request_bytes <= 0:
            raise ValueError("max_request_bytes must be greater than zero")

        providers = {item.provider.name: item for item in registrations}
        if len(providers) != len(registrations):
            raise ValueError("provider registrations must have unique names")
        if len(set(priority)) != len(priority):
            raise ValueError("provider priority must contain unique names")
        if set(priority) != set(providers):
            raise ValueError("provider priority must match configured providers")

        self._providers = providers
        self._priority = priority
        self._retry_backoff_seconds = retry_backoff_seconds
        self._max_retry_backoff_seconds = max_retry_backoff_seconds
        self._max_request_bytes = max_request_bytes
        self._event_logger = event_logger or NullProviderEventLogger()
        self._usage_recorder = usage_recorder or NullProviderUsageRecorder()
        self._states = {name: _ProviderState() for name in priority}
        self._active_provider: ProviderName | None = None
        self._initialized = False
        self._closed = False
        self._lifecycle_lock = asyncio.Lock()

    @property
    def active_provider(self) -> ProviderName | None:
        """Return the currently selected provider, if any."""

        return self._active_provider

    @property
    def is_initialized(self) -> bool:
        """Return whether router lifecycle startup completed and remains open."""

        return self._initialized and not self._closed

    @property
    def priority(self) -> tuple[ProviderName, ...]:
        """Return enabled providers in configured routing order."""

        return self._priority

    async def initialize(self) -> None:
        """Initialize configured providers and select the highest-priority candidate."""

        async with self._lifecycle_lock:
            if self._initialized and not self._closed:
                return
            self._closed = False
            for name in self._priority:
                registration = self._providers[name]
                request_id = uuid4().hex
                started_at = perf_counter()
                try:
                    await registration.provider.initialize()
                except ProviderError as error:
                    self._record_failure(name, request_id, started_at, error)
                except Exception:
                    error = ProviderError(ProviderErrorCategory.INTERNAL, name)
                    self._record_failure(name, request_id, started_at, error)
                else:
                    self._states[name].status = ProviderStatus.UNINITIALIZED
            self._initialized = True
            self._active_provider = self._first_candidate()

    async def close(self) -> None:
        """Close every initialized provider, logging cleanup failures safely."""

        async with self._lifecycle_lock:
            if self._closed:
                return
            for name in self._priority:
                request_id = uuid4().hex
                started_at = perf_counter()
                try:
                    await self._providers[name].provider.close()
                except ProviderError as error:
                    self._record_failure(name, request_id, started_at, error)
                except Exception:
                    error = ProviderError(ProviderErrorCategory.INTERNAL, name)
                    self._record_failure(name, request_id, started_at, error)
                finally:
                    self._states[name].status = ProviderStatus.CLOSED
            self._active_provider = None
            self._closed = True

    async def health_check(self) -> tuple[ProviderStatusSnapshot, ...]:
        """Probe all providers concurrently and refresh active-provider selection."""

        self._require_ready()

        async def probe(registration: ProviderRegistration) -> None:
            request_id = uuid4().hex
            try:
                await self._call_with_retries(
                    registration,
                    registration.provider.health_check,
                    request_id=request_id,
                )
            except ProviderError:
                return

        await asyncio.gather(*(probe(self._providers[name]) for name in self._priority))
        self._active_provider = self._first_healthy_or_candidate()
        return self.provider_status()

    def provider_status(self) -> tuple[ProviderStatusSnapshot, ...]:
        """Return immutable health snapshots in configured priority order."""

        return tuple(
            ProviderStatusSnapshot(
                provider=name,
                status=self._states[name].status,
                latency_ms=self._states[name].latency_ms,
                last_successful_request=self._states[name].last_successful_request,
                last_failed_request=self._states[name].last_failed_request,
                last_error_category=self._states[name].last_error_category,
            )
            for name in self._priority
        )

    async def list_models(self) -> tuple[ProviderModel, ...]:
        """List models through the active provider with retry and failover."""

        request_id = uuid4().hex
        return await self._route(
            lambda provider: provider.list_models,
            request_id=request_id,
        )

    async def generate(self, request: GenerationRequest) -> GenerationResponse:
        """Generate through the active provider and fail over when safe."""

        prepared = self._prepare_request(request)
        assert prepared.request_id is not None
        response = await self._route(
            lambda provider: lambda: provider.generate(prepared),
            request_id=prepared.request_id,
        )
        self._usage_recorder.record_generation(
            provider=response.provider,
            input_tokens=response.usage.input_tokens,
            output_tokens=response.usage.output_tokens,
            total_tokens=response.usage.total_tokens,
        )
        return response

    async def stream_generate(
        self,
        request: GenerationRequest,
    ) -> AsyncIterator[GenerationChunk]:
        """Stream with retry/failover only before the first chunk is emitted."""

        prepared = self._prepare_request(request)
        assert prepared.request_id is not None
        last_error: ProviderError | None = None

        for registration in self._candidates():
            provider = registration.provider

            async def open_stream() -> tuple[GenerationChunk, AsyncIterator[GenerationChunk]]:
                stream = provider.stream_generate(prepared)
                try:
                    first = await anext(stream)
                except StopAsyncIteration as error:
                    raise ProviderError(
                        ProviderErrorCategory.INVALID_RESPONSE,
                        provider.name,
                    ) from error
                except BaseException:
                    await stream.aclose()
                    raise
                return first, stream

            try:
                first, stream = await self._call_with_retries(
                    registration,
                    open_stream,
                    request_id=prepared.request_id,
                )
            except ProviderError as error:
                last_error = error
                if not error.failover_eligible:
                    raise
                continue

            self._usage_recorder.record_generation(
                provider=first.provider,
                input_tokens=0,
                output_tokens=0,
                total_tokens=0,
            )
            yield first
            stream_started_at = perf_counter()
            try:
                async for chunk in stream:
                    yield chunk
            except ProviderError as error:
                self._record_failure(
                    provider.name,
                    prepared.request_id,
                    stream_started_at,
                    error,
                )
                raise
            except Exception as error:
                normalized = ProviderError(
                    ProviderErrorCategory.INTERNAL,
                    provider.name,
                )
                self._record_failure(
                    provider.name,
                    prepared.request_id,
                    stream_started_at,
                    normalized,
                )
                raise normalized from error
            finally:
                await stream.aclose()
            return

        if last_error is not None:
            raise last_error
        raise ProviderRoutingError()

    async def _route(
        self,
        operation_factory: Callable[[BaseProvider], Callable[[], Awaitable[T]]],
        *,
        request_id: str,
    ) -> T:
        self._require_ready()
        last_error: ProviderError | None = None
        for registration in self._candidates():
            try:
                return await self._call_with_retries(
                    registration,
                    operation_factory(registration.provider),
                    request_id=request_id,
                )
            except ProviderError as error:
                last_error = error
                if not error.failover_eligible:
                    raise
        if last_error is not None:
            raise last_error
        raise ProviderRoutingError()

    async def _call_with_retries(
        self,
        registration: ProviderRegistration,
        operation: Callable[[], Awaitable[T]],
        *,
        request_id: str,
    ) -> T:
        provider_name = registration.provider.name
        for attempt in range(registration.retry_count + 1):
            started_at = perf_counter()
            try:
                result = await operation()
            except ProviderError as error:
                self._record_failure(provider_name, request_id, started_at, error)
                if not error.retryable or attempt >= registration.retry_count:
                    raise
                await asyncio.sleep(self._retry_delay(error, attempt))
            except Exception as error:
                normalized = ProviderError(
                    ProviderErrorCategory.INTERNAL,
                    provider_name,
                )
                self._record_failure(
                    provider_name,
                    request_id,
                    started_at,
                    normalized,
                )
                raise normalized from error
            else:
                self._record_success(provider_name, request_id, started_at)
                self._active_provider = provider_name
                return result
        raise AssertionError("retry loop exited without a result or error")

    def _prepare_request(self, request: GenerationRequest) -> GenerationRequest:
        self._require_ready()
        request_id = request.request_id or uuid4().hex
        prepared = request.model_copy(update={"request_id": request_id})
        encoded = json.dumps(
            prepared.model_dump(mode="json"),
            ensure_ascii=False,
            separators=(",", ":"),
        ).encode("utf-8")
        if len(encoded) > self._max_request_bytes:
            raise ProviderError(ProviderErrorCategory.INVALID_REQUEST, provider=None)
        return prepared

    def _candidates(self) -> tuple[ProviderRegistration, ...]:
        ordered = list(self._priority)
        if self._active_provider in ordered:
            ordered.remove(self._active_provider)
            ordered.insert(0, self._active_provider)
        return tuple(
            self._providers[name]
            for name in ordered
            if self._states[name].status not in {ProviderStatus.UNAVAILABLE, ProviderStatus.CLOSED}
        )

    def _first_candidate(self) -> ProviderName | None:
        return next(
            (
                name
                for name in self._priority
                if self._states[name].status is not ProviderStatus.UNAVAILABLE
            ),
            None,
        )

    def _first_healthy_or_candidate(self) -> ProviderName | None:
        healthy = next(
            (
                name
                for name in self._priority
                if self._states[name].status is ProviderStatus.HEALTHY
            ),
            None,
        )
        return healthy or self._first_candidate()

    def _record_success(
        self,
        provider: ProviderName,
        request_id: str,
        started_at: float,
    ) -> None:
        latency_ms = self._duration_ms(started_at)
        state = self._states[provider]
        state.status = ProviderStatus.HEALTHY
        state.latency_ms = latency_ms
        state.last_successful_request = datetime.now(UTC)
        state.last_error_category = None
        self._event_logger.record(
            provider=provider,
            latency_ms=latency_ms,
            status=ProviderStatus.HEALTHY,
            request_id=request_id,
        )

    def _record_failure(
        self,
        provider: ProviderName,
        request_id: str,
        started_at: float,
        error: ProviderError,
    ) -> None:
        latency_ms = self._duration_ms(started_at)
        state = self._states[provider]
        if error.category is ProviderErrorCategory.INVALID_REQUEST:
            pass
        elif error.category in {
            ProviderErrorCategory.TIMEOUT,
            ProviderErrorCategory.RATE_LIMIT,
        }:
            state.status = ProviderStatus.DEGRADED
        else:
            state.status = ProviderStatus.UNAVAILABLE
        state.latency_ms = latency_ms
        state.last_failed_request = datetime.now(UTC)
        state.last_error_category = error.category
        self._event_logger.record(
            provider=provider,
            latency_ms=latency_ms,
            status=state.status,
            request_id=request_id,
            error_category=error.category,
        )

    def _retry_delay(self, error: ProviderError, attempt: int) -> float:
        configured = min(
            self._retry_backoff_seconds * (2**attempt),
            self._max_retry_backoff_seconds,
        )
        if error.retry_after_seconds is None:
            return configured
        return min(max(error.retry_after_seconds, 0), self._max_retry_backoff_seconds)

    def _require_ready(self) -> None:
        if not self._initialized or self._closed:
            raise ProviderRoutingError()

    @staticmethod
    def _duration_ms(started_at: float) -> float:
        return round((perf_counter() - started_at) * 1000, 3)
