"""Cached, retry-bounded Currency Converter Tool."""

import asyncio
from dataclasses import dataclass
from datetime import UTC, datetime
from time import monotonic

from toolbridge.core.contracts import ToolDefinition
from toolbridge.tools.application.phase5_ports import ExchangeRateProvider
from toolbridge.tools.application.ports import BaseTool
from toolbridge.tools.domain.currency import (
    CurrencyConversion,
    CurrencyConverterInput,
    CurrencyConverterOutput,
    CurrencyRateSet,
)
from toolbridge.tools.domain.models import ToolHealthState, ToolHealthStatus
from toolbridge.tools.domain.tool_errors import (
    CurrencyRateUnavailableError,
    ExternalDataError,
    ExternalErrorCategory,
)


@dataclass(frozen=True, slots=True)
class _RateCacheEntry:
    rates: CurrencyRateSet
    expires_at: float


class CurrencyConverterService:
    """Retrieve, cache, and apply normalized base-unit exchange rates."""

    def __init__(
        self,
        provider: ExchangeRateProvider,
        *,
        retry_count: int,
        retry_backoff_seconds: float,
        max_retry_backoff_seconds: float,
        cache_duration_seconds: float,
        max_cache_entries: int,
    ) -> None:
        self._provider = provider
        self._retry_count = retry_count
        self._retry_backoff_seconds = retry_backoff_seconds
        self._max_retry_backoff_seconds = max_retry_backoff_seconds
        self._cache_duration_seconds = cache_duration_seconds
        self._max_cache_entries = max_cache_entries
        self._cache: dict[tuple[str, tuple[str, ...]], _RateCacheEntry] = {}
        self._locks: dict[tuple[str, tuple[str, ...]], asyncio.Lock] = {}
        self._guard = asyncio.Lock()

    async def initialize(self) -> None:
        """Initialize the selected exchange-rate provider."""

        await self._provider.initialize()

    async def convert(self, request: CurrencyConverterInput) -> CurrencyConverterOutput:
        """Convert one amount into every requested target currency."""

        targets = tuple(request.target_currencies)
        rates, cached = await self._get_rates(request.source_currency, targets)
        conversions = [
            CurrencyConversion(
                currency=currency,
                rate=rates.rates[currency],
                amount=round(request.amount * rates.rates[currency], 12),
            )
            for currency in targets
        ]
        return CurrencyConverterOutput(
            source_currency=request.source_currency,
            source_amount=request.amount,
            conversions=conversions,
            rate_date=rates.rate_date,
            provider=rates.provider,
            fetched_at=datetime.now(UTC),
            cached=cached,
        )

    async def close(self) -> None:
        """Close the provider and clear process-local rates."""

        await self._provider.close()
        async with self._guard:
            self._cache.clear()
            self._locks.clear()

    async def _get_rates(
        self,
        base: str,
        targets: tuple[str, ...],
    ) -> tuple[CurrencyRateSet, bool]:
        key = (base, targets)
        cached = await self._cached(key)
        if cached is not None:
            return cached, True
        async with await self._lock(key):
            cached = await self._cached(key)
            if cached is not None:
                return cached, True
            rates = await self._fetch(base, targets)
            await self._store(key, rates)
            return rates, False

    async def _fetch(self, base: str, targets: tuple[str, ...]) -> CurrencyRateSet:
        last_error = ExternalDataError(ExternalErrorCategory.UNAVAILABLE, retryable=True)
        for attempt in range(self._retry_count + 1):
            try:
                return await self._provider.get_rates(base, targets)
            except asyncio.CancelledError:
                raise
            except ExternalDataError as error:
                last_error = error
                if not error.retryable or attempt >= self._retry_count:
                    break
                delay = min(
                    self._retry_backoff_seconds * (2**attempt),
                    self._max_retry_backoff_seconds,
                )
                await asyncio.sleep(delay)
        raise CurrencyRateUnavailableError(last_error.category)

    async def _cached(self, key: tuple[str, tuple[str, ...]]) -> CurrencyRateSet | None:
        async with self._guard:
            entry = self._cache.get(key)
            if entry is None:
                return None
            if entry.expires_at <= monotonic():
                self._cache.pop(key, None)
                return None
            return entry.rates

    async def _store(self, key: tuple[str, tuple[str, ...]], rates: CurrencyRateSet) -> None:
        if self._cache_duration_seconds == 0:
            return
        async with self._guard:
            if key not in self._cache and len(self._cache) >= self._max_cache_entries:
                oldest = min(self._cache, key=lambda item: self._cache[item].expires_at)
                self._cache.pop(oldest, None)
                old_lock = self._locks.get(oldest)
                if old_lock is not None and not old_lock.locked():
                    self._locks.pop(oldest, None)
            self._cache[key] = _RateCacheEntry(
                rates=rates,
                expires_at=monotonic() + self._cache_duration_seconds,
            )

    async def _lock(self, key: tuple[str, tuple[str, ...]]) -> asyncio.Lock:
        async with self._guard:
            return self._locks.setdefault(key, asyncio.Lock())


class CurrencyConverterTool(BaseTool):
    """Managed MCP tool exposing configured multi-currency conversion."""

    def __init__(self, service: CurrencyConverterService, *, timeout_seconds: float) -> None:
        self._service = service
        self._definition = ToolDefinition(
            name="currency_converter",
            description="Convert one amount into multiple currencies using cached provider rates.",
            input_model=CurrencyConverterInput,
            output_model=CurrencyConverterOutput,
            handler=self.execute,
            timeout_seconds=timeout_seconds,
        )
        self._state = ToolHealthState.UNINITIALIZED
        self._last_success_at: datetime | None = None
        self._last_failure_at: datetime | None = None

    @property
    def definition(self) -> ToolDefinition:
        """Return the immutable Currency Converter registration contract."""

        return self._definition

    async def initialize(self) -> None:
        """Initialize the configured exchange-rate provider."""

        await self._service.initialize()
        self._state = ToolHealthState.HEALTHY

    async def execute(self, arguments: CurrencyConverterInput) -> CurrencyConverterOutput:
        """Convert validated input through the application service."""

        try:
            result = await self._service.convert(arguments)
        except BaseException:
            self._last_failure_at = datetime.now(UTC)
            raise
        self._last_success_at = datetime.now(UTC)
        return result

    async def health_check(self) -> ToolHealthStatus:
        """Return local provider lifecycle health without quota usage."""

        return ToolHealthStatus(
            tool_name=self._definition.name,
            status=self._state,
            checked_at=datetime.now(UTC),
            last_success_at=self._last_success_at,
            last_failure_at=self._last_failure_at,
            providers={"exchange_rates": "configured"},
        )

    async def close(self) -> None:
        """Close provider resources and mark the tool closed."""

        await self._service.close()
        self._state = ToolHealthState.CLOSED
