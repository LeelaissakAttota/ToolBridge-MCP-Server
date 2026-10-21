"""Automatic registry, discovery, configuration, and response-schema tests."""

import httpx
import pytest
from pydantic import ValidationError

from toolbridge.config import Settings
from toolbridge.core.registry import ToolRegistry
from toolbridge.providers.infrastructure.factory import build_provider_router
from toolbridge.tools.application.manager import ToolManager
from toolbridge.tools.application.metrics import InMemoryToolMetrics
from toolbridge.tools.domain.models import StockProviderName
from toolbridge.tools.infrastructure.phase5_factory import build_phase5_managed_tools


async def public_resolver(_: str) -> tuple[str, ...]:
    return ("93.184.216.34",)


def test_all_phase5_tools_register_and_discover_automatically() -> None:
    settings = Settings(_env_file=None)
    router = build_provider_router(settings)
    stock_transport = httpx.MockTransport(
        lambda request: httpx.Response(
            200,
            json={
                "chart": {
                    "error": None,
                    "result": [
                        {
                            "meta": {
                                "symbol": "MSFT",
                                "regularMarketPrice": 1,
                                "regularMarketTime": 1786000000,
                            },
                            "indicators": {"quote": [{}]},
                        }
                    ],
                }
            },
            request=request,
        )
    )
    tools = build_phase5_managed_tools(
        settings,
        router,
        stock_transports={StockProviderName.YAHOO_FINANCE: stock_transport},
        website_transport=httpx.MockTransport(
            lambda request: httpx.Response(
                200,
                text="ok",
                headers={"content-type": "text/plain"},
                request=request,
            )
        ),
        website_resolver=public_resolver,
        currency_transport=httpx.MockTransport(
            lambda request: httpx.Response(
                200,
                json={"base": "USD", "date": "2026-08-06", "rates": {"EUR": 1}},
                request=request,
            )
        ),
    )
    registry = ToolRegistry()
    ToolManager(tools, InMemoryToolMetrics()).register_all(registry)

    discovered = registry.discover()
    names = [value.name for value in discovered]

    assert names == [
        "csv_analysis",
        "currency_converter",
        "hcl_curie_analysis",
        "sql_query",
        "stock_price",
        "system_status",
        "website_reader",
    ]
    for name in names:
        metadata = registry.get(name).metadata()
        assert metadata.input_schema["additionalProperties"] is False
        assert metadata.output_schema["additionalProperties"] is False


def test_phase5_configuration_is_bounded_and_rejects_unsafe_values() -> None:
    settings = Settings(_env_file=None).phase5

    assert settings.website_reader.require_public_ip is True
    assert settings.sql_query.database_path == "demo.db"
    assert settings.csv_analysis.max_rows_scanned == 10_000
    assert settings.currency_converter.provider == "frankfurter"
    assert settings.llm_analysis.max_input_characters == 50_000

    with pytest.raises(ValidationError, match="safe HTTPS origin"):
        Settings(
            _env_file=None,
            phase5={"currency_converter": {"frankfurter": {"base_url": "http://rates.test"}}},
        )
    with pytest.raises(ValidationError, match="relative SQLite"):
        Settings(
            _env_file=None,
            phase5={"sql_query": {"database_path": "../secret.db"}},
        )
    with pytest.raises(ValidationError, match="safe relative path"):
        Settings(
            _env_file=None,
            phase5={"currency_converter": {"frankfurter": {"latest_path": "//evil.test/latest"}}},
        )
