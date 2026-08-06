"""Registration, discovery, lifecycle, and configuration tests for tools."""

import asyncio

import httpx
import pytest
from pydantic import ValidationError

from toolbridge.config import Settings
from toolbridge.core.registry import ToolRegistry
from toolbridge.tools.application.manager import ToolManager
from toolbridge.tools.application.metrics import InMemoryToolMetrics
from toolbridge.tools.domain.models import StockProviderName, ToolHealthState
from toolbridge.tools.infrastructure.factory import build_managed_tools


def yahoo_payload() -> dict[str, object]:
    """Return the smallest valid Yahoo quote response."""

    return {
        "chart": {
            "error": None,
            "result": [
                {
                    "meta": {
                        "symbol": "MSFT",
                        "regularMarketPrice": 500.0,
                        "regularMarketTime": 1_786_000_000,
                    },
                    "indicators": {"quote": [{}]},
                }
            ],
        }
    }


def test_default_tools_register_and_discover_automatically() -> None:
    settings = Settings(_env_file=None)
    transport = httpx.MockTransport(
        lambda request: httpx.Response(200, json=yahoo_payload(), request=request)
    )
    tools = build_managed_tools(
        settings,
        transports={StockProviderName.YAHOO_FINANCE: transport},
    )
    metrics = InMemoryToolMetrics()
    manager = ToolManager(tools, metrics)
    registry = ToolRegistry()

    manager.register_all(registry)
    discovered = registry.discover()

    assert [value.name for value in discovered] == [
        "stock_price",
        "system_status",
    ]
    stock = registry.get("stock_price")
    assert stock.input_model.model_json_schema()["additionalProperties"] is False
    assert "current_price" in stock.output_model.model_json_schema()["properties"]


def test_tool_manager_lifecycle_and_status_are_independently_testable() -> None:
    settings = Settings(_env_file=None)
    transport = httpx.MockTransport(
        lambda request: httpx.Response(200, json=yahoo_payload(), request=request)
    )
    tools = build_managed_tools(
        settings,
        transports={StockProviderName.YAHOO_FINANCE: transport},
    )
    manager = ToolManager(tools, InMemoryToolMetrics())

    async def run() -> tuple[object, ...]:
        await manager.initialize()
        statuses = await manager.statuses()
        await manager.close()
        return statuses

    statuses = asyncio.run(run())

    assert [value.health.tool_name for value in statuses] == [
        "system_status",
        "stock_price",
    ]
    assert all(
        value.health.status is ToolHealthState.HEALTHY for value in statuses
    )


def test_stock_configuration_defaults_are_bounded_and_explicit() -> None:
    stock = Settings(_env_file=None).stock_price

    assert stock.enabled is True
    assert stock.timeout_seconds == 10
    assert stock.retry_count == 2
    assert stock.cache_duration_seconds == 60
    assert stock.provider_priority_order == (
        StockProviderName.YAHOO_FINANCE,
        StockProviderName.ALPHA_VANTAGE,
    )
    assert stock.yahoo_finance.enabled is True
    assert stock.alpha_vantage.enabled is False


def test_stock_configuration_rejects_insecure_or_unusable_values() -> None:
    with pytest.raises(ValidationError, match="HTTPS"):
        Settings(
            _env_file=None,
            stock_price={
                "yahoo_finance": {"base_url": "http://finance.test"},
            },
        )
    with pytest.raises(ValidationError, match="safe relative path"):
        Settings(
            _env_file=None,
            stock_price={
                "yahoo_finance": {
                    "quote_path_template": "//evil.test/{symbol}"
                },
            },
        )

    with pytest.raises(ValidationError, match="safe relative path"):
        Settings(
            _env_file=None,
            stock_price={"alpha_vantage": {"query_path": "//evil.test/query"}},
        )


    with pytest.raises(ValidationError, match="requires a provider"):
        Settings(
            _env_file=None,
            stock_price={
                "yahoo_finance": {"enabled": False},
                "alpha_vantage": {"enabled": False},
            },
        )

    with pytest.raises(ValidationError, match="API key"):
        Settings(
            _env_file=None,
            stock_price={
                "alpha_vantage": {"enabled": True},
            },
        )


def test_alpha_vantage_secret_loads_from_nested_environment_and_is_masked(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("TOOLBRIDGE_STOCK_PRICE__ALPHA_VANTAGE__ENABLED", "true")
    monkeypatch.setenv(
        "TOOLBRIDGE_STOCK_PRICE__ALPHA_VANTAGE__API_KEY",
        "test-alpha-secret",
    )

    settings = Settings(_env_file=None)

    assert settings.stock_price.alpha_vantage.api_key is not None
    assert (
        settings.stock_price.alpha_vantage.api_key.get_secret_value()
        == "test-alpha-secret"
    )
    assert "test-alpha-secret" not in repr(settings)
