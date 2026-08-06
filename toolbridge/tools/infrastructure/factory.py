"""Compose configured managed tools and stock provider adapters."""

from collections.abc import Mapping

import httpx

from toolbridge.config import Settings
from toolbridge.tools.adapters.alpha_vantage import AlphaVantageStockProvider
from toolbridge.tools.adapters.http import HttpStockProviderConfig
from toolbridge.tools.adapters.yahoo_finance import YahooFinanceStockProvider
from toolbridge.tools.application.managed import DefinitionTool
from toolbridge.tools.application.ports import (
    BaseTool,
    StockProviderEventLogger,
    StockQuoteProvider,
)
from toolbridge.tools.application.stock_price import StockPriceService, StockPriceTool
from toolbridge.tools.definitions import system_status_definition
from toolbridge.tools.domain.models import StockProviderName


def build_managed_tools(
    settings: Settings,
    event_logger: StockProviderEventLogger | None = None,
    *,
    transports: Mapping[
        StockProviderName,
        httpx.AsyncBaseTransport,
    ]
    | None = None,
) -> tuple[BaseTool, ...]:
    """Build enabled tools and providers without making network calls."""

    tools: list[BaseTool] = [
        DefinitionTool(system_status_definition(settings.tool_timeout_seconds))
    ]
    stock = settings.stock_price
    if not stock.enabled:
        return tuple(tools)

    configured_transports = transports or {}
    providers: dict[StockProviderName, StockQuoteProvider] = {}
    common = {
        "timeout_seconds": stock.timeout_seconds,
        "max_response_bytes": stock.max_provider_response_bytes,
        "user_agent": stock.yahoo_finance.user_agent,
    }
    if stock.yahoo_finance.enabled:
        yahoo_config = HttpStockProviderConfig(
            base_url=str(stock.yahoo_finance.base_url).rstrip("/"),
            **common,
        )
        providers[StockProviderName.YAHOO_FINANCE] = YahooFinanceStockProvider(
            yahoo_config,
            quote_path_template=stock.yahoo_finance.quote_path_template,
            range_value=stock.yahoo_finance.range_value,
            interval=stock.yahoo_finance.interval,
            transport=configured_transports.get(StockProviderName.YAHOO_FINANCE),
        )
    if stock.alpha_vantage.enabled:
        api_key = stock.alpha_vantage.api_key
        if api_key is None:
            raise ValueError("enabled Alpha Vantage requires an API key")
        alpha_config = HttpStockProviderConfig(
            base_url=str(stock.alpha_vantage.base_url).rstrip("/"),
            **common,
        )
        providers[StockProviderName.ALPHA_VANTAGE] = AlphaVantageStockProvider(
            alpha_config,
            api_key=api_key.get_secret_value(),
            query_path=stock.alpha_vantage.query_path,
            function_name=stock.alpha_vantage.function_name,
            transport=configured_transports.get(StockProviderName.ALPHA_VANTAGE),
        )

    ordered = tuple(providers[name] for name in stock.provider_priority_order if name in providers)
    service = StockPriceService(
        ordered,
        retry_count=stock.retry_count,
        cache_duration_seconds=stock.cache_duration_seconds,
        max_cache_entries=stock.max_cache_entries,
        retry_backoff_seconds=stock.retry_backoff_seconds,
        max_retry_backoff_seconds=stock.max_retry_backoff_seconds,
        health_check_symbol=stock.health_check_symbol,
        event_logger=event_logger,
    )
    tools.append(
        StockPriceTool(
            service,
            timeout_seconds=stock.timeout_seconds,
        )
    )
    return tuple(tools)
