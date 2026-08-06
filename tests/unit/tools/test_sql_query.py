"""Read-only SQL validation, execution, bounds, and failure tests."""

import asyncio
import sqlite3

import pytest
from pydantic import ValidationError

from toolbridge.tools.adapters.sqlite_query import SQLiteReadOnlyQueryExecutor
from toolbridge.tools.application.sql_query import SQLQueryTool
from toolbridge.tools.domain.sql_query import SQLQueryInput
from toolbridge.tools.domain.tool_errors import DatabaseQueryFailedError


def create_database(path: object) -> None:
    """Create a small SQLite fixture database."""

    connection = sqlite3.connect(path)
    connection.execute("CREATE TABLE items (name TEXT, quantity INTEGER)")
    connection.executemany(
        "INSERT INTO items VALUES (?, ?)",
        (("alpha", 2), ("beta", 5), ("gamma", 9)),
    )
    connection.commit()
    connection.close()


def test_sql_query_executes_parameterized_read_only_query(tmp_path: object) -> None:
    database = tmp_path / "inventory.db"
    create_database(database)
    executor = SQLiteReadOnlyQueryExecutor(
        "inventory.db",
        database_root=tmp_path,
        timeout_seconds=1,
        progress_operations=100,
    )
    tool = SQLQueryTool(executor, timeout_seconds=2, default_max_rows=2)

    async def run() -> object:
        await tool.initialize()
        result = await tool.execute(
            SQLQueryInput(
                query=(
                    "SELECT name, quantity FROM items WHERE quantity >= :minimum "
                    "ORDER BY quantity"
                ),
                parameters={"minimum": 2},
                max_rows=2,
            )
        )
        await tool.close()
        return result

    result = asyncio.run(run())

    assert result.columns == ["name", "quantity"]
    assert result.rows == [
        {"name": "alpha", "quantity": 2},
        {"name": "beta", "quantity": 5},
    ]
    assert result.row_count == 2
    assert result.truncated is True


@pytest.mark.parametrize(
    "query",
    (
        "DELETE FROM items",
        "SELECT * FROM items; DROP TABLE items",
        "PRAGMA table_info(items)",
        "SELECT * FROM items -- bypass",
        "WITH changed AS (DELETE FROM items RETURNING *) SELECT * FROM changed",
    ),
)
def test_sql_query_rejects_unsafe_input(query: str) -> None:
    with pytest.raises(ValidationError):
        SQLQueryInput(query=query)


def test_sql_query_normalizes_missing_database_and_duplicate_columns(tmp_path: object) -> None:
    missing = SQLiteReadOnlyQueryExecutor(
        "missing.db",
        database_root=tmp_path,
        timeout_seconds=1,
        progress_operations=100,
    )

    async def run_missing() -> None:
        with pytest.raises(DatabaseQueryFailedError):
            await missing.execute("SELECT 1 AS value", {}, max_rows=10)

    asyncio.run(run_missing())

    database = tmp_path / "data.db"
    create_database(database)
    executor = SQLiteReadOnlyQueryExecutor(
        "data.db",
        database_root=tmp_path,
        timeout_seconds=1,
        progress_operations=100,
    )

    async def run_duplicate() -> None:
        with pytest.raises(DatabaseQueryFailedError):
            await executor.execute("SELECT 1 AS value, 2 AS value", {}, max_rows=10)

    asyncio.run(run_duplicate())


def test_sql_query_progress_handler_enforces_timeout() -> None:
    executor = SQLiteReadOnlyQueryExecutor(
        ":memory:",
        database_root=__import__("pathlib").Path("."),
        timeout_seconds=0.000001,
        progress_operations=1,
    )
    query = (
        "WITH RECURSIVE counter(value) AS ("
        "SELECT 1 UNION ALL SELECT value + 1 FROM counter WHERE value < 1000000"
        ") SELECT sum(value) AS total FROM counter"
    )

    async def run() -> None:
        with pytest.raises(DatabaseQueryFailedError) as captured:
            await executor.execute(query, {}, max_rows=1)
        assert captured.value.retryable is True

    asyncio.run(run())
