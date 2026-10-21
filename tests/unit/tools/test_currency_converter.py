"""Currency conversion provider, cache, retry, validation, and failure tests."""

import asyncio
from datetime import date

import httpx
import pytest
from pydantic import ValidationError

from toolbridge.tools.adapters.frankfurter import FrankfurterExchangeRateProvider
from toolbridge.tools.application.currency_converter import (
    CurrencyConverterService,
    CurrencyConverterTool,
)
from toolbridge.tools.domain.currency import CurrencyConverterInput
from toolbridge.tools.domain.tool_errors import CurrencyRateUnavailableError


def build_provider(handler: object) -> FrankfurterExchangeRateProvider:
    """Build an offline Frankfurter adapter."""

    return FrankfurterExchangeRateProvider(
        base_url="https://rates.test",
        latest_path="/latest",
        timeout_seconds=1,
        max_response_bytes=10_000,
        user_agent="tests",
        transport=httpx.MockTransport(handler),
    )


def build_tool(
    provider: FrankfurterExchangeRateProvider, *, retries: int = 0
) -> CurrencyConverterTool:
    """Build the managed converter with deterministic retry delays."""

    service = CurrencyConverterService(
        provider,
        retry_count=retries,
        retry_backoff_seconds=0,
        max_retry_backoff_seconds=0,
        cache_duration_seconds=60,
        max_cache_entries=10,
    )
    return CurrencyConverterTool(service, timeout_seconds=2)


def test_currency_converter_converts_multiple_targets_and_caches_rates() -> None:
    calls = 0

    def handler(request: httpx.Request) -> httpx.Response:
        nonlocal calls
        calls += 1
        assert request.url.params["from"] == "USD"
        assert request.url.params["to"] == "EUR,JPY"
        return httpx.Response(
            200,
            json={"base": "USD", "date": "2026-08-06", "rates": {"EUR": 0.9, "JPY": 150.0}},
            request=request,
        )

    tool = build_tool(build_provider(handler))
    request = CurrencyConverterInput(
        amount=10,
        source_currency="usd",
        target_currencies=["eur", "jpy"],
    )

    async def run() -> tuple[object, object]:
        await tool.initialize()
        first = await tool.execute(request)
        second = await tool.execute(request)
        await tool.close()
        return first, second

    first, second = asyncio.run(run())

    assert first.rate_date == date(2026, 8, 6)
    assert [item.amount for item in first.conversions] == [9.0, 1500.0]
    assert first.cached is False
    assert second.cached is True
    assert calls == 1


def test_currency_converter_retries_retryable_provider_failure() -> None:
    statuses = iter((503, 200))

    def handler(request: httpx.Request) -> httpx.Response:
        status = next(statuses)
        payload = {"base": "USD", "date": "2026-08-06", "rates": {"EUR": 0.8}}
        return httpx.Response(status, json=payload, request=request)

    tool = build_tool(build_provider(handler), retries=1)

    async def run() -> object:
        await tool.initialize()
        result = await tool.execute(
            CurrencyConverterInput(amount=5, source_currency="USD", target_currencies=["EUR"])
        )
        await tool.close()
        return result

    result = asyncio.run(run())
    assert result.conversions[0].amount == 4


def test_currency_converter_validates_input_and_normalizes_invalid_response() -> None:
    with pytest.raises(ValidationError):
        CurrencyConverterInput(amount=-1, source_currency="USD", target_currencies=["EUR"])
    with pytest.raises(ValidationError):
        CurrencyConverterInput(amount=1, source_currency="USD", target_currencies=["USD"])
    with pytest.raises(ValidationError):
        CurrencyConverterInput(amount=1, source_currency="USD", target_currencies=["EUR", "EUR"])

    with pytest.raises(ValidationError):
        CurrencyConverterInput(amount=1, source_currency="USD", target_currencies=["EU"])

    tool = build_tool(
        build_provider(
            lambda request: httpx.Response(
                200,
                json={"base": "USD", "date": "bad", "rates": {}},
                request=request,
            )
        )
    )

    async def run() -> None:
        await tool.initialize()
        with pytest.raises(CurrencyRateUnavailableError) as captured:
            await tool.execute(
                CurrencyConverterInput(amount=1, source_currency="USD", target_currencies=["EUR"])
            )
        assert captured.value.details == {"error_category": "invalid_response"}
        await tool.close()

    asyncio.run(run())
