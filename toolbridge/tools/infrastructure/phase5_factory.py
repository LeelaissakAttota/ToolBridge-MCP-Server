"""Composition root for the approved Phase 5 managed tools."""

from collections.abc import Mapping
from pathlib import Path

import httpx

from toolbridge.config import Settings
from toolbridge.phase5_config import SQLQueryToolSettings
from toolbridge.providers.application.router import ProviderRouter
from toolbridge.tools.adapters.csv_file import LocalCSVDataSource
from toolbridge.tools.adapters.frankfurter import FrankfurterExchangeRateProvider
from toolbridge.tools.adapters.sqlite_query import SQLiteReadOnlyQueryExecutor
from toolbridge.tools.adapters.website_reader import HostResolver, HttpWebsiteFetcher
from toolbridge.tools.application.csv_analysis import CSVAnalysisTool
from toolbridge.tools.application.currency_converter import (
    CurrencyConverterService,
    CurrencyConverterTool,
)
from toolbridge.tools.application.llm_analysis import LLMAnalysisTool
from toolbridge.tools.application.phase5_ports import ReadOnlyQueryExecutor
from toolbridge.tools.application.ports import BaseTool, StockProviderEventLogger
from toolbridge.tools.application.sql_query import SQLQueryTool
from toolbridge.tools.application.website_reader import WebsiteReaderTool
from toolbridge.tools.domain.models import StockProviderName
from toolbridge.tools.infrastructure.factory import build_managed_tools


def build_sql_query_executor(sql: SQLQueryToolSettings) -> ReadOnlyQueryExecutor:
    """Select the configured read-only SQL adapter. PostgreSQL is not connected here."""

    if sql.backend == "postgres":
        from toolbridge.tools.adapters.postgres_query import PostgresReadOnlyQueryExecutor

        return PostgresReadOnlyQueryExecutor(
            sql.postgres_connection_target(),
            timeout_seconds=sql.timeout_seconds,
            max_value_bytes=sql.max_value_bytes,
        )
    return SQLiteReadOnlyQueryExecutor(
        sql.database_path,
        database_root=Path(sql.database_root),
        timeout_seconds=sql.timeout_seconds,
        progress_operations=sql.progress_operations,
        max_value_bytes=sql.max_value_bytes,
    )


def build_phase5_managed_tools(
    settings: Settings,
    provider_router: ProviderRouter,
    stock_event_logger: StockProviderEventLogger | None = None,
    *,
    stock_transports: Mapping[StockProviderName, httpx.AsyncBaseTransport] | None = None,
    website_transport: httpx.AsyncBaseTransport | None = None,
    website_resolver: HostResolver | None = None,
    currency_transport: httpx.AsyncBaseTransport | None = None,
) -> tuple[BaseTool, ...]:
    """Build Phase 1-5 tools without performing network or file requests."""

    tools = list(
        build_managed_tools(
            settings,
            stock_event_logger,
            transports=stock_transports,
        )
    )
    phase5 = settings.phase5

    website = phase5.website_reader
    if website.enabled:
        fetcher = HttpWebsiteFetcher(
            timeout_seconds=website.timeout_seconds,
            max_response_bytes=website.max_response_bytes,
            user_agent=website.user_agent,
            allowed_hosts=website.allowed_host_set,
            require_public_ip=website.require_public_ip,
            transport=website_transport,
            resolver=website_resolver,
            max_redirects=website.max_redirects,
        )
        tools.append(
            WebsiteReaderTool(
                fetcher,
                timeout_seconds=website.timeout_seconds,
                default_max_characters=website.default_max_characters,
            )
        )

    sql = phase5.sql_query
    if sql.enabled:
        sql_executor = build_sql_query_executor(sql)
        tools.append(
            SQLQueryTool(
                sql_executor,
                timeout_seconds=sql.timeout_seconds,
                default_max_rows=sql.max_rows,
            )
        )

    csv_settings = phase5.csv_analysis
    if csv_settings.enabled:
        csv_source = LocalCSVDataSource(
            Path(csv_settings.root_directory),
            encoding=csv_settings.encoding,
            max_file_bytes=csv_settings.max_file_bytes,
            max_rows_scanned=csv_settings.max_rows_scanned,
            max_columns=csv_settings.max_columns,
            max_field_characters=csv_settings.max_field_characters,
        )
        tools.append(
            CSVAnalysisTool(
                csv_source,
                timeout_seconds=csv_settings.timeout_seconds,
                default_preview_rows=csv_settings.default_preview_rows,
            )
        )

    currency = phase5.currency_converter
    if currency.enabled:
        provider_settings = currency.frankfurter
        provider = FrankfurterExchangeRateProvider(
            base_url=str(provider_settings.base_url),
            latest_path=provider_settings.latest_path,
            timeout_seconds=currency.timeout_seconds,
            max_response_bytes=currency.max_provider_response_bytes,
            user_agent=provider_settings.user_agent,
            transport=currency_transport,
        )
        service = CurrencyConverterService(
            provider,
            retry_count=currency.retry_count,
            retry_backoff_seconds=currency.retry_backoff_seconds,
            max_retry_backoff_seconds=currency.max_retry_backoff_seconds,
            cache_duration_seconds=currency.cache_duration_seconds,
            max_cache_entries=currency.max_cache_entries,
        )
        tools.append(CurrencyConverterTool(service, timeout_seconds=currency.timeout_seconds))

    llm = phase5.llm_analysis
    if llm.enabled:
        tools.append(
            LLMAnalysisTool(
                provider_router,
                timeout_seconds=llm.timeout_seconds,
                max_input_characters=llm.max_input_characters,
                max_tokens=llm.max_tokens,
                temperature=llm.temperature,
                model=llm.model,
                system_prompt=llm.system_prompt,
            )
        )

    return tuple(tools)
