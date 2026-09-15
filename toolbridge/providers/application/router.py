"""Provider discovery, ranking, retry, failover, budget, and health service."""

import asyncio
import json
from collections.abc import AsyncIterator, Awaitable, Callable
from dataclasses import dataclass, field
from datetime import UTC, datetime
from time import perf_counter
from typing import TypeVar
from uuid import uuid4

from toolbridge.providers.application.budget import BudgetPolicy, ProviderBudgetManager
from toolbridge.providers.application.ports import (
    BaseProvider,
    NullProviderEventLogger,
    NullProviderUsageRecorder,
    ProviderEventLogger,
    ProviderUsageRecorder,
)
from toolbridge.providers.application.scoring import ModelRankingEngine
from toolbridge.providers.domain.errors import ProviderError, ProviderRoutingError
from toolbridge.providers.domain.models import (
    GenerationChunk,
    GenerationRequest,
    GenerationResponse,
    ModelSelection,
    ProviderCapabilities,
    ProviderCapability,
    ProviderErrorCategory,
    ProviderModel,
    ProviderStatus,
    ProviderStatusSnapshot,
)

T = TypeVar("T")


@dataclass(frozen=True, slots=True)
class ProviderRegistration:
    """A provider plugin instance and its routing policy."""

    provider: BaseProvider
    retry_count: int
    default_model: str | None = None
    capabilities: ProviderCapabilities = field(
        default_factory=lambda: ProviderCapabilities(chat=True, streaming=True)
    )
    budget_policy: BudgetPolicy = field(default_factory=BudgetPolicy)
    startup_discovery: bool = False
    model_template: ProviderModel | None = None

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
    requests: int = 0
    successes: int = 0
    errors: int = 0
    retries: int = 0
    total_latency_ms: float = 0.0
    discovery_time_ms: float | None = None
    discovered_at: datetime | None = None

    @property
    def success_rate(self) -> float:
        completed = self.successes + self.errors
        return self.successes / completed if completed else 1.0

    @property
    def average_latency_ms(self) -> float:
        completed = self.successes + self.errors
        return self.total_latency_ms / completed if completed else 0.0

    @property
    def health_score(self) -> float:
        availability = 1.0 if self.status is ProviderStatus.HEALTHY else 0.5
        if self.status in {ProviderStatus.UNAVAILABLE, ProviderStatus.CLOSED}:
            availability = 0.0
        latency_factor = max(0.0, 1.0 - min(self.average_latency_ms, 10_000) / 10_000)
        return round(self.success_rate * 0.6 + availability * 0.3 + latency_factor * 0.1, 4)


class ProviderRouter:
    """Hide provider plugins behind capability-aware normalized routing."""

    def __init__(
        self,
        registrations: tuple[ProviderRegistration, ...],
        priority: tuple[str, ...],
        *,
        retry_backoff_seconds: float,
        max_retry_backoff_seconds: float,
        max_request_bytes: int,
        event_logger: ProviderEventLogger | None = None,
        usage_recorder: ProviderUsageRecorder | None = None,
        installed_providers: tuple[str, ...] = (),
        installed_capabilities: dict[str, ProviderCapabilities] | None = None,
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
        if priority and set(priority) != set(providers):
            raise ValueError("provider priority must match configured providers")
        self._providers = providers
        self._priority = priority
        self._installed_providers = installed_providers or tuple(sorted(providers))
        self._installed_capabilities = dict(installed_capabilities or {})
        self._retry_backoff_seconds = retry_backoff_seconds
        self._max_retry_backoff_seconds = max_retry_backoff_seconds
        self._max_request_bytes = max_request_bytes
        self._event_logger = event_logger or NullProviderEventLogger()
        self._usage_recorder = usage_recorder or NullProviderUsageRecorder()
        self._states = {name: _ProviderState() for name in providers}
        self._models: dict[str, tuple[ProviderModel, ...]] = {}
        self._active_provider: str | None = None
        self._active_model: str | None = None
        self._last_selection: ModelSelection | None = None
        self._initialized = False
        self._closed = False
        self._lifecycle_lock = asyncio.Lock()
        self._ranking = ModelRankingEngine()
        self._budgets = ProviderBudgetManager(
            {name: registration.budget_policy for name, registration in providers.items()}
        )

    @property
    def active_provider(self) -> str | None:
        return self._active_provider

    @property
    def active_model(self) -> str | None:
        return self._active_model

    @property
    def last_selection(self) -> ModelSelection | None:
        return self._last_selection

    @property
    def installed_providers(self) -> tuple[str, ...]:
        return self._installed_providers

    @property
    def enabled_providers(self) -> frozenset[str]:
        return frozenset(self._providers)

    @property
    def is_initialized(self) -> bool:
        return self._initialized and not self._closed

    @property
    def priority(self) -> tuple[str, ...]:
        return self._priority

    async def initialize(self) -> None:
        """Initialize, authenticate, probe, and discover every enabled plugin."""

        async with self._lifecycle_lock:
            if self._initialized and not self._closed:
                return
            self._closed = False
            for name, registration in self._providers.items():
                request_id = uuid4().hex
                started_at = perf_counter()
                try:
                    await registration.provider.initialize()
                    if registration.startup_discovery:
                        await registration.provider.health_check()
                        discovery_started = perf_counter()
                        models = await registration.provider.discover_models()
                        state = self._states[name]
                        state.discovery_time_ms = self._duration_ms(discovery_started)
                        state.discovered_at = datetime.now(UTC)
                        self._models[name] = models or self._default_models(registration)
                        self._record_success(name, request_id, started_at)
                    else:
                        self._models[name] = self._default_models(registration)
                except ProviderError as error:
                    self._record_failure(name, request_id, started_at, error)
                except Exception as error:
                    normalized = ProviderError(ProviderErrorCategory.INTERNAL, name)
                    self._record_failure(name, request_id, started_at, normalized)
                    del error
            self._initialized = True
            self._active_provider = self._first_candidate()

    async def close(self) -> None:
        async with self._lifecycle_lock:
            if self._closed:
                return
            for name, registration in self._providers.items():
                try:
                    await registration.provider.close()
                except Exception:
                    pass
                self._states[name].status = ProviderStatus.CLOSED
            self._active_provider = None
            self._active_model = None
            self._closed = True

    async def health_check(self) -> tuple[ProviderStatusSnapshot, ...]:
        """Probe every enabled plugin so unhealthy providers can recover."""

        self._require_ready()

        async def probe(registration: ProviderRegistration) -> None:
            try:
                await self._call_with_retries(
                    registration,
                    registration.provider.health_check,
                    request_id=uuid4().hex,
                )
            except ProviderError:
                return

        await asyncio.gather(*(probe(item) for item in self._providers.values()))
        self._active_provider = self._first_healthy_or_candidate()
        return self.provider_status()

    def provider_status(self) -> tuple[ProviderStatusSnapshot, ...]:
        """Return health, latency, success, error, and retry telemetry."""

        order = self._ordered_names()
        return tuple(
            ProviderStatusSnapshot(
                provider=name,
                status=self._states[name].status,
                latency_ms=self._states[name].latency_ms,
                last_successful_request=self._states[name].last_successful_request,
                last_failed_request=self._states[name].last_failed_request,
                last_error_category=self._states[name].last_error_category,
                requests=self._states[name].requests,
                successes=self._states[name].successes,
                errors=self._states[name].errors,
                retries=self._states[name].retries,
                success_rate=self._states[name].success_rate,
                average_latency_ms=self._states[name].average_latency_ms,
                health_score=self._states[name].health_score,
            )
            for name in order
        )

    def discovered_models(self) -> tuple[ProviderModel, ...]:
        """Return the cached catalog enriched with current provider health."""

        values: list[ProviderModel] = []
        for name in self._ordered_names():
            state = self._states[name]
            for model in self._models.get(name, ()):
                values.append(
                    model.model_copy(
                        update={
                            "latency_ms": state.average_latency_ms or state.latency_ms,
                            "health_score": state.health_score,
                            "available": state.status
                            not in {ProviderStatus.UNAVAILABLE, ProviderStatus.CLOSED},
                        }
                    )
                )
        return tuple(values)

    def provider_capabilities(self, provider: str) -> ProviderCapabilities:
        registration = self._providers.get(provider)
        return (
            registration.capabilities
            if registration
            else self._installed_capabilities.get(provider, ProviderCapabilities())
        )

    def discovery_metadata(self, provider: str) -> tuple[float | None, datetime | None]:
        state = self._states.get(provider)
        return (state.discovery_time_ms, state.discovered_at) if state else (None, None)

    def budget_status(self, provider: str):
        return self._budgets.snapshot(provider)

    async def list_models(self) -> tuple[ProviderModel, ...]:
        self._require_ready()
        cached = self.discovered_models()
        if cached:
            return cached
        return await self._route(lambda provider: provider.list_models, request_id=uuid4().hex)

    async def generate(self, request: GenerationRequest) -> GenerationResponse:
        prepared = self._prepare_request(request)
        response = await self._route_generation(prepared)
        self._usage_recorder.record_generation(
            provider=response.provider,
            input_tokens=response.usage.input_tokens,
            output_tokens=response.usage.output_tokens,
            total_tokens=response.usage.total_tokens,
        )
        selected = self._selected_model(response.provider, response.model)
        if selected is not None:
            self._budgets.record(
                response.provider,
                self._budgets.estimate_cost(
                    selected, response.usage.input_tokens, response.usage.output_tokens
                ),
            )
        return response

    async def stream_generate(self, request: GenerationRequest) -> AsyncIterator[GenerationChunk]:
        prepared = self._prepare_request(request)
        candidates = self._generation_candidates(prepared, streaming=True)
        last_error: ProviderError | None = None
        for registration, model, reason, score in candidates:
            provider = registration.provider
            routed = prepared.model_copy(update={"model": model.id}) if model else prepared

            async def open_stream() -> tuple[GenerationChunk, AsyncIterator[GenerationChunk]]:
                stream = provider.stream_generate(routed)
                try:
                    return await anext(stream), stream
                except StopAsyncIteration as error:
                    raise ProviderError(
                        ProviderErrorCategory.INVALID_RESPONSE, provider.name
                    ) from error

            try:
                first, stream = await self._call_with_retries(
                    registration, open_stream, request_id=prepared.request_id
                )
            except ProviderError as error:
                last_error = error
                if not error.failover_eligible:
                    raise
                continue
            self._select(provider.name, first.model, score, reason)
            self._usage_recorder.record_generation(
                provider=first.provider, input_tokens=0, output_tokens=0, total_tokens=0
            )
            yield first
            try:
                async for chunk in stream:
                    yield chunk
            finally:
                await stream.aclose()
            return
        if last_error:
            raise last_error
        raise ProviderRoutingError()

    async def _route_generation(self, request: GenerationRequest) -> GenerationResponse:
        last_error: ProviderError | None = None
        for registration, model, reason, score in self._generation_candidates(request):
            routed = request.model_copy(update={"model": model.id}) if model else request
            try:
                response = await self._call_with_retries(
                    registration,
                    lambda: registration.provider.generate(routed),
                    request_id=request.request_id or uuid4().hex,
                )
            except ProviderError as error:
                last_error = error
                if not error.failover_eligible:
                    raise
                continue
            self._select(registration.provider.name, response.model, score, reason)
            return response
        if last_error:
            raise last_error
        if not self._providers:
            raise ProviderRoutingError()
        raise ProviderError(ProviderErrorCategory.CAPABILITY_UNAVAILABLE, None)

    def _generation_candidates(
        self, request: GenerationRequest, *, streaming: bool = False
    ) -> tuple[tuple[ProviderRegistration, ProviderModel | None, str, float], ...]:
        self._require_ready()
        models = self.discovered_models()
        if models:
            if streaming:
                request = request.model_copy(
                    update={
                        "required_capabilities": request.required_capabilities
                        | frozenset({ProviderCapability.STREAMING})
                    }
                )
            health = {name: state.health_score for name, state in self._states.items()}
            soft = frozenset(
                name for name in self._providers if self._budgets.soft_limit_reached(name)
            )
            ranked = self._ranking.rank(
                models,
                request,
                provider_health=health,
                soft_limited=soft,
                explicit_priority=self._priority,
            )
            values = []
            for item in ranked:
                registration = self._providers[item.model.provider]
                estimate = self._budgets.estimate_cost(
                    item.model,
                    request.estimated_input_tokens,
                    request.max_tokens or 0,
                )
                if request.max_cost_usd is not None and estimate > request.max_cost_usd:
                    continue
                if not self._budgets.permits(item.model.provider, estimate):
                    continue
                values.append((registration, item.model, item.reason, item.score))
            return tuple(values)
        return tuple(
            (registration, None, "configured provider order", 0.0)
            for registration in self._legacy_candidates()
        )

    async def _route(
        self,
        operation_factory: Callable[[BaseProvider], Callable[[], Awaitable[T]]],
        *,
        request_id: str,
    ) -> T:
        self._require_ready()
        last_error: ProviderError | None = None
        for registration in self._legacy_candidates():
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
        if last_error:
            raise last_error
        raise ProviderRoutingError()

    async def _call_with_retries(
        self,
        registration: ProviderRegistration,
        operation: Callable[[], Awaitable[T]],
        *,
        request_id: str,
    ) -> T:
        provider = registration.provider.name
        self._states[provider].requests += 1
        for attempt in range(registration.retry_count + 1):
            started_at = perf_counter()
            try:
                result = await operation()
            except ProviderError as error:
                self._record_failure(provider, request_id, started_at, error)
                if not error.retryable or attempt >= registration.retry_count:
                    raise
                self._states[provider].retries += 1
                await asyncio.sleep(self._retry_delay(error, attempt))
            except Exception as error:
                normalized = ProviderError(ProviderErrorCategory.INTERNAL, provider)
                self._record_failure(provider, request_id, started_at, normalized)
                raise normalized from error
            else:
                self._record_success(provider, request_id, started_at)
                self._active_provider = provider
                return result
        raise AssertionError("retry loop exited without a result or error")

    def _prepare_request(self, request: GenerationRequest) -> GenerationRequest:
        self._require_ready()
        prepared = request.model_copy(update={"request_id": request.request_id or uuid4().hex})
        encoded = json.dumps(prepared.model_dump(mode="json"), separators=(",", ":")).encode()
        if len(encoded) > self._max_request_bytes:
            raise ProviderError(ProviderErrorCategory.INVALID_REQUEST, None)
        return prepared

    def _legacy_candidates(self) -> tuple[ProviderRegistration, ...]:
        ordered = list(self._ordered_names())
        if self._active_provider in ordered:
            ordered.remove(self._active_provider)
            ordered.insert(0, self._active_provider)
        return tuple(
            self._providers[name]
            for name in ordered
            if self._states[name].status not in {ProviderStatus.UNAVAILABLE, ProviderStatus.CLOSED}
        )

    def _ordered_names(self) -> tuple[str, ...]:
        remaining = tuple(name for name in sorted(self._providers) if name not in self._priority)
        return self._priority + remaining

    def _first_candidate(self) -> str | None:
        return next(
            (
                name
                for name in self._ordered_names()
                if self._states[name].status is not ProviderStatus.UNAVAILABLE
            ),
            None,
        )

    def _first_healthy_or_candidate(self) -> str | None:
        return next(
            (
                name
                for name in self._ordered_names()
                if self._states[name].status is ProviderStatus.HEALTHY
            ),
            self._first_candidate(),
        )

    def _record_success(self, provider: str, request_id: str, started_at: float) -> None:
        latency = self._duration_ms(started_at)
        state = self._states[provider]
        state.status = ProviderStatus.HEALTHY
        state.latency_ms = latency
        state.last_successful_request = datetime.now(UTC)
        state.last_error_category = None
        state.successes += 1
        state.total_latency_ms += latency
        self._event_logger.record(
            provider=provider,
            latency_ms=latency,
            status=ProviderStatus.HEALTHY,
            request_id=request_id,
        )

    def _record_failure(
        self, provider: str, request_id: str, started_at: float, error: ProviderError
    ) -> None:
        latency = self._duration_ms(started_at)
        state = self._states[provider]
        if error.category is ProviderErrorCategory.INVALID_REQUEST:
            pass
        elif error.category in {ProviderErrorCategory.TIMEOUT, ProviderErrorCategory.RATE_LIMIT}:
            state.status = ProviderStatus.DEGRADED
        else:
            state.status = ProviderStatus.UNAVAILABLE
        state.latency_ms = latency
        state.last_failed_request = datetime.now(UTC)
        state.last_error_category = error.category
        state.errors += 1
        state.total_latency_ms += latency
        self._event_logger.record(
            provider=provider,
            latency_ms=latency,
            status=state.status,
            request_id=request_id,
            error_category=error.category,
        )

    def _retry_delay(self, error: ProviderError, attempt: int) -> float:
        configured = min(
            self._retry_backoff_seconds * (2**attempt), self._max_retry_backoff_seconds
        )
        if error.retry_after_seconds is None:
            return configured
        return min(max(error.retry_after_seconds, 0), self._max_retry_backoff_seconds)

    def _select(self, provider: str, model: str, score: float, reason: str) -> None:
        self._active_provider = provider
        self._active_model = model
        self._last_selection = ModelSelection(
            provider=provider, model=model, score=score, reason=reason
        )

    def _default_models(self, registration: ProviderRegistration) -> tuple[ProviderModel, ...]:
        if registration.model_template is not None:
            return (registration.model_template,)
        if registration.default_model is None:
            return ()
        return (
            ProviderModel(
                id=registration.default_model,
                provider=registration.provider.name,
                capabilities=registration.capabilities,
                discovered_at=datetime.now(UTC),
            ),
        )

    def _selected_model(self, provider: str, model: str) -> ProviderModel | None:
        return next((item for item in self._models.get(provider, ()) if item.id == model), None)

    def _require_ready(self) -> None:
        if not self._initialized or self._closed:
            raise ProviderRoutingError()

    @staticmethod
    def _duration_ms(started_at: float) -> float:
        return round((perf_counter() - started_at) * 1000, 3)
