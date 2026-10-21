"""Offline contract tests for Yahoo Finance and Alpha Vantage adapters."""

import asyncio
import json
import logging

import httpx
import pytest

from toolbridge.tools.adapters.alpha_vantage import AlphaVantageStockProvider
from toolbridge.tools.adapters.http import HttpStockProviderConfig
from toolbridge.tools.adapters.yahoo_finance import YahooFinanceStockProvider
from toolbridge.tools.domain.errors import StockDataError
from toolbridge.tools.domain.models import (
    MarketStatus,
    StockErrorCategory,
    StockProviderName,
)
from toolbridge.tools.infrastructure.logging import StructuredStockFormatter


def config() -> HttpStockProviderConfig:
    """Return bounded adapter test configuration."""

    return HttpStockProviderConfig(
        base_url="https://stocks.test",
        timeout_seconds=1,
        max_response_bytes=4_096,
        user_agent="ToolBridge-Tests",
    )


def yahoo_payload() -> dict[str, object]:
    """Return a representative Yahoo chart response."""

    return {
        "chart": {
            "error": None,
            "result": [
                {
                    "meta": {
                        "symbol": "NVDA",
                        "longName": "NVIDIA Corporation",
                        "currency": "USD",
                        "fullExchangeName": "NasdaqGS",
                        "regularMarketPrice": 123.45,
                        "regularMarketDayHigh": 125.0,
                        "regularMarketDayLow": 120.0,
                        "regularMarketOpen": 121.0,
                        "previousClose": 122.0,
                        "regularMarketTime": 1_786_000_000,
                        "marketState": "REGULAR",
                    },
                    "indicators": {
                        "quote": [
                            {
                                "open": [121.0],
                                "high": [125.0],
                                "low": [120.0],
                                "close": [123.45],
                            }
                        ]
                    },
                }
            ],
        }
    }


def test_yahoo_adapter_normalizes_all_required_capabilities() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        assert request.url.path == "/v8/finance/chart/NVDA"
        assert request.url.params["range"] == "1d"
        assert request.url.params["interval"] == "1m"
        assert request.headers["User-Agent"] == "ToolBridge-Tests"
        return httpx.Response(200, json=yahoo_payload(), request=request)

    provider = YahooFinanceStockProvider(
        config(),
        quote_path_template="/v8/finance/chart/{symbol}",
        range_value="1d",
        interval="1m",
        transport=httpx.MockTransport(handler),
    )

    async def run() -> object:
        await provider.initialize()
        result = await provider.get_quote("NVDA")
        await provider.close()
        return result

    result = asyncio.run(run())

    assert result.symbol == "NVDA"
    assert result.current_price == 123.45
    assert result.company_name == "NVIDIA Corporation"
    assert result.currency == "USD"
    assert result.exchange == "NasdaqGS"
    assert result.day_high == 125
    assert result.day_low == 120
    assert result.open == 121
    assert result.previous_close == 122
    assert result.market_status is MarketStatus.OPEN
    assert result.provider is StockProviderName.YAHOO_FINANCE
    assert result.timestamp.tzinfo is not None


def test_yahoo_adapter_normalizes_invalid_symbol_and_timeout() -> None:
    invalid = YahooFinanceStockProvider(
        config(),
        quote_path_template="/v8/finance/chart/{symbol}",
        range_value="1d",
        interval="1m",
        transport=httpx.MockTransport(
            lambda request: httpx.Response(
                200,
                json={"chart": {"result": None, "error": {"code": "Not Found"}}},
                request=request,
            )
        ),
    )

    def timeout(request: httpx.Request) -> httpx.Response:
        raise httpx.ReadTimeout("secret upstream detail", request=request)

    timed_out = YahooFinanceStockProvider(
        config(),
        quote_path_template="/v8/finance/chart/{symbol}",
        range_value="1d",
        interval="1m",
        transport=httpx.MockTransport(timeout),
    )

    async def run(provider: YahooFinanceStockProvider) -> StockDataError:
        await provider.initialize()
        with pytest.raises(StockDataError) as caught:
            await provider.get_quote("BAD")
        await provider.close()
        return caught.value

    invalid_error = asyncio.run(run(invalid))
    timeout_error = asyncio.run(run(timed_out))

    assert invalid_error.category is StockErrorCategory.INVALID_SYMBOL
    assert timeout_error.category is StockErrorCategory.TIMEOUT
    assert timeout_error.retryable is True
    assert "secret upstream detail" not in str(timeout_error)


def test_yahoo_adapter_rejects_malformed_or_oversized_response() -> None:
    malformed = YahooFinanceStockProvider(
        config(),
        quote_path_template="/v8/finance/chart/{symbol}",
        range_value="1d",
        interval="1m",
        transport=httpx.MockTransport(
            lambda request: httpx.Response(
                200,
                json={"chart": {"result": [{"meta": {}}], "error": None}},
                request=request,
            )
        ),
    )
    small_config = HttpStockProviderConfig(
        base_url="https://stocks.test",
        timeout_seconds=1,
        max_response_bytes=1,
        user_agent="ToolBridge-Tests",
    )
    oversized = YahooFinanceStockProvider(
        small_config,
        quote_path_template="/v8/finance/chart/{symbol}",
        range_value="1d",
        interval="1m",
        transport=httpx.MockTransport(
            lambda request: httpx.Response(
                200,
                json=yahoo_payload(),
                request=request,
            )
        ),
    )

    async def run(provider: YahooFinanceStockProvider) -> StockDataError:
        await provider.initialize()
        with pytest.raises(StockDataError) as caught:
            await provider.get_quote("NVDA")
        await provider.close()
        return caught.value

    assert asyncio.run(run(malformed)).category is StockErrorCategory.INVALID_RESPONSE
    assert asyncio.run(run(oversized)).category is StockErrorCategory.INVALID_RESPONSE


def test_alpha_vantage_adapter_uses_secret_and_normalizes_quote() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        assert request.url.path == "/query"
        assert request.url.params["function"] == "GLOBAL_QUOTE"
        assert request.url.params["symbol"] == "NVDA"
        assert request.url.params["apikey"] == "test-alpha-key"
        return httpx.Response(
            200,
            json={
                "Global Quote": {
                    "01. symbol": "NVDA",
                    "02. open": "121.0",
                    "03. high": "125.0",
                    "04. low": "120.0",
                    "05. price": "123.45",
                    "07. latest trading day": "2026-08-06",
                    "08. previous close": "122.0",
                }
            },
            request=request,
        )

    provider = AlphaVantageStockProvider(
        config(),
        api_key="test-alpha-key",
        query_path="/query",
        function_name="GLOBAL_QUOTE",
        transport=httpx.MockTransport(handler),
    )

    async def run() -> object:
        await provider.initialize()
        result = await provider.get_quote("NVDA")
        await provider.close()
        return result

    result = asyncio.run(run())

    assert result.current_price == 123.45
    assert result.market_status is MarketStatus.UNKNOWN
    assert result.company_name is None
    assert result.currency is None
    assert result.exchange is None
    assert result.provider is StockProviderName.ALPHA_VANTAGE


def test_stock_log_formatter_excludes_symbols_keys_urls_and_payloads() -> None:
    record = logging.LogRecord(
        name="toolbridge.stock",
        level=logging.WARNING,
        pathname=__file__,
        lineno=1,
        msg="secret message",
        args=(),
        exc_info=None,
    )
    record.event = "stock_provider_attempt_completed"
    record.tool_name = "stock_price"
    record.provider = "alpha_vantage"
    record.operation_id = "operation-1"
    record.latency_ms = 4.2
    record.status = "failed"
    record.error_category = "rate_limit"
    record.symbol = "NVDA"
    record.api_key = "test-alpha-key"
    record.url = "https://stocks.test/query?apikey=test-alpha-key"
    record.payload = {"private": "value"}

    output = StructuredStockFormatter().format(record)
    payload = json.loads(output)

    assert payload["provider"] == "alpha_vantage"
    assert payload["error_category"] == "rate_limit"
    assert "NVDA" not in output
    assert "test-alpha-key" not in output
    assert "stocks.test" not in output
    assert "private" not in output
    assert "secret message" not in output
