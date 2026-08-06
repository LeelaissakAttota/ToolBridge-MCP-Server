"""Application tests for stock routing, validation, caching, and metrics."""

import asyncio
from datetime import UTC, datetime
from typing import cast

from toolbridge.core.contracts import ErrorCode
from toolbridge.core.executor import ToolExecutor
from toolbridge.core.registry import ToolRegistry
from toolbridge.core.validation import RequestValidator, ResponseValidator
from toolbridge.tools.application.metrics import InMemoryToolMetrics
from toolbridge.tools.application.ports import StockQuoteProvider
from toolbridge.tools.application.stock_price import StockPriceService, StockPriceTool
from toolbridge.tools.domain.errors import StockDataError
from toolbridge.tools.domain.models import (
    MarketStatus,
    ProviderHealthStatus,
    StockErrorCategory,
    StockPriceOutput,
    StockProviderName,
    ToolHealthState,
)


def quote(
    provider: StockProviderName = StockProviderName.YAHOO_FINANCE,
) -> StockPriceOutput:
    """Return a stable normalized quote fixture."""

    return StockPriceOutput(
        symbol="NVDA",
        current_price=123.45,
        company_name="NVIDIA Corporation",
        currency="USD",
        exchange="NasdaqGS",
        day_high=125.0,
        day_low=120.0,
        open=121.0,
        previous_close=122.0,
        market_status=MarketStatus.OPEN,
        timestamp=datetime(2026, 8, 6, 15, 30, tzinfo=UTC),
        provider=provider,
    )


class FakeStockProvider(StockQuoteProvider):
    """Scriptable provider implementing the project-owned port."""

    def __init__(
        self,
        name: StockProviderName,
        responses: list[StockPriceOutput | StockDataError | object],
        *,
        delay_seconds: float = 0,
        healthy: bool = True,
    ) -> None:
        self._name = name
        self.responses = responses
        self.delay_seconds = delay_seconds
        self.healthy = healthy
        self.calls = 0
        self.initialized = False
        self.closed = False

    @property
    def name(self) -> StockProviderName:
        return self._name

    async def initialize(self) -> None:
        self.initialized = True

    async def get_quote(self, symbol: str) -> StockPriceOutput:
        del symbol
        self.calls += 1
        if self.delay_seconds:
            await asyncio.sleep(self.delay_seconds)
        value = self.responses[min(self.calls - 1, len(self.responses) - 1)]
        if isinstance(value, StockDataError):
            raise value
        return cast(StockPriceOutput, value)

    async def health_check(self, symbol: str) -> ProviderHealthStatus:
        del symbol
        return ProviderHealthStatus(
            provider=self.name,
            status=(
                ToolHealthState.HEALTHY
                if self.healthy
                else ToolHealthState.UNAVAILABLE
            ),
            checked_at=datetime.now(UTC),
            latency_ms=0,
        )

    async def close(self) -> None:
        self.closed = True


def service(
    providers: tuple[StockQuoteProvider, ...],
    *,
    retry_count: int = 0,
    cache_duration_seconds: float = 0,
) -> StockPriceService:
    """Build a bounded service with waits disabled for deterministic tests."""

    async def no_sleep(_: float) -> None:
        return None

    return StockPriceService(
        providers,
        retry_count=retry_count,
        cache_duration_seconds=cache_duration_seconds,
        max_cache_entries=4,
        retry_backoff_seconds=0,
        max_retry_backoff_seconds=0,
        health_check_symbol="MSFT",
        sleep=no_sleep,
    )


def executor_for(
    stock_service: StockPriceService,
    *,
    timeout_seconds: float = 1,
    metrics: InMemoryToolMetrics | None = None,
) -> tuple[ToolExecutor, StockPriceTool]:
    """Register one isolated Stock Price Tool with the MCP Core."""

    tool = StockPriceTool(stock_service, timeout_seconds=timeout_seconds)
    registry = ToolRegistry()
    registry.register(tool.definition)
    return (
        ToolExecutor(
            registry,
            RequestValidator(max_request_bytes=1_024),
            ResponseValidator(max_response_bytes=4_096),
            metrics,
        ),
        tool,
    )


def test_successful_execution_is_normalized_and_measured() -> None:
    provider = FakeStockProvider(StockProviderName.YAHOO_FINANCE, [quote()])
    metrics = InMemoryToolMetrics()
    executor, tool = executor_for(service((provider,)), metrics=metrics)

    async def run() -> object:
        await tool.initialize()
        result = await executor.execute("stock_price", {"symbol": "nvda"})
        await tool.close()
        return result

    response = asyncio.run(run())

    assert response.success is True
    assert response.result is not None
    assert response.result["symbol"] == "NVDA"
    assert response.result["current_price"] == 123.45
    assert response.result["provider"] == "yahoo_finance"
    snapshot = metrics.snapshot("stock_price")
    assert snapshot.total_executions == 1
    assert snapshot.successful_executions == 1
    assert provider.initialized is True
    assert provider.closed is True


def test_invalid_symbol_syntax_is_rejected_before_provider_execution() -> None:
    provider = FakeStockProvider(StockProviderName.YAHOO_FINANCE, [quote()])
    executor, tool = executor_for(service((provider,)))

    async def run() -> object:
        await tool.initialize()
        result = await executor.execute("stock_price", {"symbol": "../NVDA"})
        await tool.close()
        return result

    response = asyncio.run(run())

    assert response.error is not None
    assert response.error.code is ErrorCode.INVALID_REQUEST
    assert provider.calls == 0


def test_unknown_symbol_returns_stable_invalid_symbol_error() -> None:
    provider = FakeStockProvider(
        StockProviderName.YAHOO_FINANCE,
        [
            StockDataError(
                StockErrorCategory.INVALID_SYMBOL,
                StockProviderName.YAHOO_FINANCE,
                retryable=False,
            )
        ],
    )
    executor, tool = executor_for(service((provider,)))

    async def run() -> object:
        await tool.initialize()
        result = await executor.execute("stock_price", {"symbol": "UNKNOWN"})
        await tool.close()
        return result

    response = asyncio.run(run())

    assert response.error is not None
    assert response.error.code is ErrorCode.INVALID_SYMBOL
    assert response.error.retryable is False
    assert response.error.details == {"symbol": "UNKNOWN"}


def test_network_failure_retries_then_returns_safe_unavailable_error() -> None:
    failure = StockDataError(
        StockErrorCategory.NETWORK,
        StockProviderName.YAHOO_FINANCE,
        retryable=True,
    )
    provider = FakeStockProvider(
        StockProviderName.YAHOO_FINANCE,
        [failure, failure, failure],
    )
    executor, tool = executor_for(service((provider,), retry_count=2))

    async def run() -> object:
        await tool.initialize()
        result = await executor.execute("stock_price", {"symbol": "NVDA"})
        await tool.close()
        return result

    response = asyncio.run(run())

    assert response.error is not None
    assert response.error.code is ErrorCode.DATA_SOURCE_UNAVAILABLE
    assert response.error.retryable is True
    assert response.error.details == {"error_category": "network"}
    assert provider.calls == 3


def test_provider_priority_fails_over_without_retrying_authentication() -> None:
    primary = FakeStockProvider(
        StockProviderName.YAHOO_FINANCE,
        [
            StockDataError(
                StockErrorCategory.AUTHENTICATION,
                StockProviderName.YAHOO_FINANCE,
                retryable=False,
            )
        ],
    )
    fallback = FakeStockProvider(
        StockProviderName.ALPHA_VANTAGE,
        [quote(StockProviderName.ALPHA_VANTAGE)],
    )
    executor, tool = executor_for(service((primary, fallback), retry_count=2))

    async def run() -> object:
        await tool.initialize()
        result = await executor.execute("stock_price", {"symbol": "NVDA"})
        await tool.close()
        return result

    response = asyncio.run(run())

    assert response.result is not None
    assert response.result["provider"] == "alpha_vantage"
    assert primary.calls == 1
    assert fallback.calls == 1


def test_cache_prevents_duplicate_provider_calls() -> None:
    provider = FakeStockProvider(StockProviderName.YAHOO_FINANCE, [quote()])
    stock_service = service((provider,), cache_duration_seconds=60)

    async def run() -> tuple[StockPriceOutput, StockPriceOutput]:
        await stock_service.initialize()
        first = await stock_service.get_quote("NVDA")
        second = await stock_service.get_quote("NVDA")
        await stock_service.close()
        return first, second

    first, second = asyncio.run(run())

    assert first.cached is False
    assert second.cached is True
    assert provider.calls == 1


def test_outer_execution_timeout_cancels_slow_provider() -> None:
    provider = FakeStockProvider(
        StockProviderName.YAHOO_FINANCE,
        [quote()],
        delay_seconds=1,
    )
    executor, tool = executor_for(service((provider,)), timeout_seconds=0.01)

    async def run() -> object:
        await tool.initialize()
        result = await executor.execute("stock_price", {"symbol": "NVDA"})
        await tool.close()
        return result

    response = asyncio.run(run())

    assert response.error is not None
    assert response.error.code is ErrorCode.EXECUTION_TIMEOUT


def test_response_validation_rejects_provider_contract_violation() -> None:
    provider = FakeStockProvider(
        StockProviderName.YAHOO_FINANCE,
        [{"symbol": "NVDA", "unexpected": True}],
    )
    executor, tool = executor_for(service((provider,), cache_duration_seconds=0))

    async def run() -> object:
        await tool.initialize()
        result = await executor.execute("stock_price", {"symbol": "NVDA"})
        await tool.close()
        return result

    response = asyncio.run(run())

    assert response.error is not None
    assert response.error.code is ErrorCode.INVALID_RESPONSE


def test_health_status_reports_degraded_when_fallback_is_unavailable() -> None:
    primary = FakeStockProvider(StockProviderName.YAHOO_FINANCE, [quote()])
    fallback = FakeStockProvider(
        StockProviderName.ALPHA_VANTAGE,
        [quote(StockProviderName.ALPHA_VANTAGE)],
        healthy=False,
    )
    tool = StockPriceTool(service((primary, fallback)), timeout_seconds=1)

    async def run() -> object:
        await tool.initialize()
        result = await tool.health_check()
        await tool.close()
        return result

    health = asyncio.run(run())

    assert health.status is ToolHealthState.DEGRADED
    assert health.providers == {
        "yahoo_finance": "healthy",
        "alpha_vantage": "unavailable",
    }
