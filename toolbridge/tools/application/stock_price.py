"""Configuration-driven routing and MCP definition for stock prices."""

import asyncio
from collections.abc import Awaitable, Callable
from dataclasses import dataclass
from datetime import UTC, datetime
from time import monotonic, perf_counter
from uuid import uuid4

from toolbridge.core.contracts import ToolDefinition
from toolbridge.tools.application.ports import (
    BaseTool,
    NullStockProviderEventLogger,
    StockProviderEventLogger,
    StockQuoteProvider,
)
from toolbridge.tools.domain.errors import (
    InvalidStockSymbolError,
    StockDataError,
    StockDataUnavailableError,
)
from toolbridge.tools.domain.models import (
    ProviderHealthStatus,
    StockErrorCategory,
    StockPriceInput,
    StockPriceOutput,
    ToolHealthState,
    ToolHealthStatus,
)

Sleep = Callable[[float], Awaitable[None]]


@dataclass(frozen=True, slots=True)
class _CacheEntry:
    quote: StockPriceOutput
    expires_at: float


class StockPriceService:
    """Route stock quote requests through prioritized replaceable providers."""

    def __init__(
        self,
        providers: tuple[StockQuoteProvider, ...],
        *,
        retry_count: int,
        cache_duration_seconds: float,
        max_cache_entries: int,
        retry_backoff_seconds: float,
        max_retry_backoff_seconds: float,
        health_check_symbol: str,
        event_logger: StockProviderEventLogger | None = None,
        sleep: Sleep = asyncio.sleep,
    ) -> None:
        if not providers:
            raise ValueError("at least one stock quote provider is required")
        if retry_count < 0:
            raise ValueError("retry_count cannot be negative")
        if cache_duration_seconds < 0:
            raise ValueError("cache duration cannot be negative")
        if max_cache_entries <= 0:
            raise ValueError("max_cache_entries must be positive")
        if retry_backoff_seconds < 0:
            raise ValueError("retry backoff cannot be negative")
        if max_retry_backoff_seconds < retry_backoff_seconds:
            raise ValueError("maximum retry backoff cannot be smaller than initial")
        self._providers = providers
        self._retry_count = retry_count
        self._cache_duration_seconds = cache_duration_seconds
        self._max_cache_entries = max_cache_entries
        self._retry_backoff_seconds = retry_backoff_seconds
        self._max_retry_backoff_seconds = max_retry_backoff_seconds
        self._health_check_symbol = health_check_symbol
        self._event_logger = event_logger or NullStockProviderEventLogger()
        self._sleep = sleep
        self._cache: dict[str, _CacheEntry] = {}
        self._locks: dict[str, asyncio.Lock] = {}
        self._cache_guard = asyncio.Lock()
        self._initialized: list[StockQuoteProvider] = []

    @property
    def providers(self) -> tuple[StockQuoteProvider, ...]:
        """Return providers in effective priority order."""

        return self._providers

    async def initialize(self) -> None:
        """Initialize provider resources with partial-startup rollback."""

        if self._initialized:
            return
        try:
            for provider in self._providers:
                await provider.initialize()
                self._initialized.append(provider)
        except BaseException:
            await self.close()
            raise

    async def get_quote(self, symbol: str) -> StockPriceOutput:
        """Return a fresh or cached quote after retries and safe failover."""

        cached = await self._cached(symbol)
        if cached is not None:
            return cached

        lock = await self._symbol_lock(symbol)
        async with lock:
            cached = await self._cached(symbol)
            if cached is not None:
                return cached
            quote = await self._fetch(symbol)
            await self._store(symbol, quote)
            return quote

    async def _fetch(self, symbol: str) -> StockPriceOutput:
        last_error: StockDataError | None = None
        saw_non_invalid_error = False

        for provider in self._providers:
            for attempt in range(self._retry_count + 1):
                operation_id = uuid4().hex
                started_at = perf_counter()
                try:
                    quote = await provider.get_quote(symbol)
                except asyncio.CancelledError:
                    raise
                except StockDataError as error:
                    last_error = error
                    saw_non_invalid_error |= (
                        error.category is not StockErrorCategory.INVALID_SYMBOL
                    )
                    self._event_logger.completed(
                        provider=provider.name,
                        operation_id=operation_id,
                        latency_ms=self._duration_ms(started_at),
                        status="failed",
                        error_category=error.category.value,
                    )
                    if error.category is StockErrorCategory.INVALID_SYMBOL:
                        break
                    if not error.retryable or attempt == self._retry_count:
                        break
                    await self._sleep(self._backoff(attempt))
                else:
                    self._event_logger.completed(
                        provider=provider.name,
                        operation_id=operation_id,
                        latency_ms=self._duration_ms(started_at),
                        status="succeeded",
                    )
                    return quote

        if last_error is not None and not saw_non_invalid_error:
            raise InvalidStockSymbolError(symbol)
        raise StockDataUnavailableError(last_error.category if last_error is not None else None)

    async def health_check(self) -> tuple[ProviderHealthStatus, ...]:
        """Probe all configured providers concurrently."""

        results = await asyncio.gather(
            *(provider.health_check(self._health_check_symbol) for provider in self._providers),
            return_exceptions=True,
        )
        normalized: list[ProviderHealthStatus] = []
        for provider, result in zip(self._providers, results, strict=True):
            if isinstance(result, asyncio.CancelledError):
                raise result
            if isinstance(result, BaseException):
                normalized.append(
                    ProviderHealthStatus(
                        provider=provider.name,
                        status=ToolHealthState.UNAVAILABLE,
                        checked_at=datetime.now(UTC),
                        error_category=StockErrorCategory.UNAVAILABLE,
                    )
                )
            else:
                normalized.append(result)
        return tuple(normalized)

    async def close(self) -> None:
        """Close initialized providers in reverse order and clear cached data."""

        failures: list[Exception] = []
        for provider in reversed(self._initialized):
            try:
                await provider.close()
            except Exception as error:
                failures.append(error)
        self._initialized.clear()
        async with self._cache_guard:
            self._cache.clear()
            self._locks.clear()
        if failures:
            raise ExceptionGroup("one or more stock providers failed to close", failures)

    async def _cached(self, symbol: str) -> StockPriceOutput | None:
        async with self._cache_guard:
            entry = self._cache.get(symbol)
            if entry is None:
                return None
            if entry.expires_at <= monotonic():
                self._cache.pop(symbol, None)
                return None
            return entry.quote.model_copy(update={"cached": True})

    async def _store(self, symbol: str, quote: StockPriceOutput) -> None:
        if self._cache_duration_seconds == 0:
            return
        async with self._cache_guard:
            if symbol not in self._cache and len(self._cache) >= self._max_cache_entries:
                oldest_symbol = min(
                    self._cache,
                    key=lambda key: self._cache[key].expires_at,
                )
                self._cache.pop(oldest_symbol, None)
                old_lock = self._locks.get(oldest_symbol)
                if old_lock is not None and not old_lock.locked():
                    self._locks.pop(oldest_symbol, None)
            self._cache[symbol] = _CacheEntry(
                quote=quote.model_copy(update={"cached": False}),
                expires_at=monotonic() + self._cache_duration_seconds,
            )

    async def _symbol_lock(self, symbol: str) -> asyncio.Lock:
        async with self._cache_guard:
            return self._locks.setdefault(symbol, asyncio.Lock())

    def _backoff(self, retry_index: int) -> float:
        delay = self._retry_backoff_seconds * (2**retry_index)
        return min(delay, self._max_retry_backoff_seconds)

    @staticmethod
    def _duration_ms(started_at: float) -> float:
        return round((perf_counter() - started_at) * 1_000, 3)


class StockPriceTool(BaseTool):
    """Managed MCP tool exposing normalized stock quote retrieval."""

    def __init__(
        self,
        service: StockPriceService,
        *,
        timeout_seconds: float,
    ) -> None:
        self._service = service
        self._definition = ToolDefinition(
            name="stock_price",
            description=(
                "Return a validated current stock quote from configured market data providers."
            ),
            input_model=StockPriceInput,
            output_model=StockPriceOutput,
            handler=self.execute,
            timeout_seconds=timeout_seconds,
        )
        self._state = ToolHealthState.UNINITIALIZED
        self._last_success_at: datetime | None = None
        self._last_failure_at: datetime | None = None

    @property
    def definition(self) -> ToolDefinition:
        """Return the immutable Stock Price Tool registration contract."""

        return self._definition

    async def initialize(self) -> None:
        """Initialize configured stock data providers."""

        await self._service.initialize()
        self._state = ToolHealthState.HEALTHY

    async def execute(self, arguments: StockPriceInput) -> StockPriceOutput:
        """Retrieve a normalized quote for validated arguments."""

        try:
            quote = await self._service.get_quote(arguments.symbol)
        except BaseException:
            self._last_failure_at = datetime.now(UTC)
            raise
        self._last_success_at = datetime.now(UTC)
        return quote

    async def health_check(self) -> ToolHealthStatus:
        """Probe all stock data providers and summarize availability."""

        if self._state in {
            ToolHealthState.UNINITIALIZED,
            ToolHealthState.CLOSED,
        }:
            return ToolHealthStatus(
                tool_name=self._definition.name,
                status=self._state,
                checked_at=datetime.now(UTC),
                last_success_at=self._last_success_at,
                last_failure_at=self._last_failure_at,
            )

        started_at = perf_counter()
        providers = await self._service.health_check()
        healthy_count = sum(value.status is ToolHealthState.HEALTHY for value in providers)
        if healthy_count == len(providers):
            state = ToolHealthState.HEALTHY
        elif healthy_count:
            state = ToolHealthState.DEGRADED
        else:
            state = ToolHealthState.UNAVAILABLE
        self._state = state
        if healthy_count:
            self._last_success_at = datetime.now(UTC)
        else:
            self._last_failure_at = datetime.now(UTC)
        return ToolHealthStatus(
            tool_name=self._definition.name,
            status=state,
            checked_at=datetime.now(UTC),
            latency_ms=StockPriceService._duration_ms(started_at),
            last_success_at=self._last_success_at,
            last_failure_at=self._last_failure_at,
            providers={value.provider.value: value.status.value for value in providers},
        )

    async def close(self) -> None:
        """Close stock data resources and mark the tool closed."""

        await self._service.close()
        self._state = ToolHealthState.CLOSED
