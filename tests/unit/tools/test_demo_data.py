"""The bundled demo data must work with the default tool configuration."""

import asyncio
from pathlib import Path

from toolbridge.phase5_config import Phase5ToolSettings
from toolbridge.tools.adapters.csv_file import LocalCSVDataSource
from toolbridge.tools.adapters.sqlite_query import SQLiteReadOnlyQueryExecutor

REPO_ROOT = Path(__file__).resolve().parents[3]


def test_default_sql_config_queries_bundled_demo_database() -> None:
    sql = Phase5ToolSettings().sql_query
    executor = SQLiteReadOnlyQueryExecutor(
        sql.database_path,
        database_root=REPO_ROOT / sql.database_root,
        timeout_seconds=sql.timeout_seconds,
        progress_operations=sql.progress_operations,
    )

    result = asyncio.run(
        executor.execute(
            "SELECT c.ticker, f.revenue_billion FROM companies c JOIN financials f "
            "ON f.ticker = c.ticker WHERE c.country = :country AND f.fiscal_year = 2025 "
            "ORDER BY c.ticker",
            {"country": "IN"},
            max_rows=50,
        )
    )

    assert result.row_count == 5
    assert result.rows[0]["ticker"] == "HDFCBANK.NS"


def test_default_csv_root_contains_analyzable_samples() -> None:
    settings = Phase5ToolSettings().csv_analysis
    source = LocalCSVDataSource(
        REPO_ROOT / settings.root_directory,
        encoding=settings.encoding,
        max_file_bytes=settings.max_file_bytes,
        max_rows_scanned=settings.max_rows_scanned,
        max_columns=settings.max_columns,
        max_field_characters=settings.max_field_characters,
    )

    sales = asyncio.run(source.analyze("sample_sales.csv", preview_rows=3))
    prices = asyncio.run(source.analyze("sample_stock_prices.csv", preview_rows=3))

    assert sales.row_count == 60
    units = next(summary for summary in sales.summaries if summary.name == "units")
    assert units.missing_count == 1
    assert prices.row_count == 60
    assert "close" in prices.columns
