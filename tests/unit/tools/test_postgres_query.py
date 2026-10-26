"""PostgreSQL read-only adapter, configuration, and optional live-database tests."""

import asyncio
import os
from contextlib import asynccontextmanager
from datetime import UTC, datetime
from decimal import Decimal

import pytest
from pydantic import SecretStr, ValidationError

from toolbridge.config import Settings
from toolbridge.phase5_config import SQLQueryToolSettings
from toolbridge.tools.adapters.postgres_query import (
    PostgresReadOnlyQueryExecutor,
    bind_named_parameters,
)
from toolbridge.tools.adapters.sqlite_query import SQLiteReadOnlyQueryExecutor
from toolbridge.tools.application.sql_query import SQLQueryTool
from toolbridge.tools.domain.sql_query import SQLQueryInput
from toolbridge.tools.domain.tool_errors import DatabaseQueryFailedError
from toolbridge.tools.infrastructure.phase5_factory import build_sql_query_executor

LIVE_DSN = os.environ.get("TOOLBRIDGE_TEST_POSTGRES_DSN", "").strip()


class FakeAttribute:
    def __init__(self, name: str) -> None:
        self.name = name


class FakeStatement:
    def __init__(self, columns: list[str], rows: list[tuple[object, ...]]) -> None:
        self.columns = columns
        self.rows = rows
        self.arguments: tuple[object, ...] | None = None
        self.prefetch: int | None = None

    def get_attributes(self) -> list[FakeAttribute]:
        return [FakeAttribute(name) for name in self.columns]

    def cursor(
        self, *arguments: object, prefetch: int | None = None, timeout: float | None = None
    ):
        del timeout
        self.arguments = arguments
        self.prefetch = prefetch

        async def iterate():
            for row in self.rows:
                yield row

        return iterate()


class FakeConnection:
    def __init__(self, statement: FakeStatement) -> None:
        self.statement = statement
        self.readonly: bool | None = None
        self.prepared: str | None = None
        self.closed = False

    @asynccontextmanager
    async def transaction(self, *, readonly: bool = False):
        self.readonly = readonly
        yield

    async def prepare(self, query: str, *, timeout: float | None = None) -> FakeStatement:
        del timeout
        self.prepared = query
        return self.statement

    async def close(self) -> None:
        self.closed = True


def postgres_settings() -> SQLQueryToolSettings:
    return SQLQueryToolSettings(
        backend="postgres",
        postgres_host="127.0.0.1",
        postgres_database="demo",
        postgres_user="toolbridge_ro",
        postgres_password=SecretStr("secret-password"),
    )


def test_named_parameters_skip_literals_casts_and_dollar_quotes() -> None:
    query, arguments = bind_named_parameters(
        "SELECT :id, ':id', value::int, $$ :id $$, $tag$ :id $tag$ FROM items WHERE id = :id",
        {"id": 7},
        max_value_bytes=100,
    )

    assert (
        query
        == "SELECT $1, ':id', value::int, $$ :id $$, $tag$ :id $tag$ FROM items WHERE id = $1"
    )
    assert arguments == [7]


def test_missing_or_oversized_parameter_fails_before_connect() -> None:
    opened = False

    async def connect(**_: object) -> object:
        nonlocal opened
        opened = True
        raise AssertionError("connect must not be called")

    executor = PostgresReadOnlyQueryExecutor(
        {"host": "127.0.0.1", "database": "demo"},
        timeout_seconds=1,
        max_value_bytes=4,
        connect=connect,
    )

    async def run() -> None:
        with pytest.raises(DatabaseQueryFailedError):
            await executor.execute("SELECT :missing", {}, max_rows=1)
        with pytest.raises(DatabaseQueryFailedError):
            await executor.execute("SELECT :value", {"value": "12345"}, max_rows=1)

    asyncio.run(run())
    assert opened is False


def test_postgres_executor_bounds_rows_and_enforces_read_only_session() -> None:
    statement = FakeStatement(
        ["name", "quantity", "price", "updated_at"],
        (
            ("alpha", 2, Decimal("1.50"), datetime(2026, 10, 26, tzinfo=UTC)),
            ("beta", 5, Decimal("2.00"), datetime(2026, 10, 26, tzinfo=UTC)),
            ("gamma", 9, Decimal("3.00"), datetime(2026, 10, 26, tzinfo=UTC)),
        ),
    )
    connection = FakeConnection(statement)
    seen: dict[str, object] = {}

    async def connect(**kwargs: object) -> FakeConnection:
        seen.update(kwargs)
        return connection

    executor = PostgresReadOnlyQueryExecutor(
        {"host": "127.0.0.1", "user": "toolbridge_ro", "password": "secret-password"},
        timeout_seconds=5,
        connect=connect,
    )

    result = asyncio.run(
        executor.execute(
            "SELECT name, quantity FROM items WHERE quantity >= :minimum",
            {"minimum": 2},
            max_rows=2,
        )
    )

    assert connection.readonly is True
    assert connection.closed is True
    assert connection.prepared == "SELECT name, quantity FROM items WHERE quantity >= $1"
    assert statement.arguments == (2,)
    assert seen["server_settings"]["default_transaction_read_only"] == "on"
    assert seen["command_timeout"] == 5
    assert "secret-password" not in repr(executor)
    assert result.truncated is True
    assert result.row_count == 2
    assert result.rows[0]["price"] == "1.50"
    assert result.rows[0]["updated_at"] == "2026-10-26T00:00:00+00:00"


def test_postgres_executor_hides_driver_errors_and_marks_timeouts() -> None:
    async def fail(**_: object) -> object:
        raise RuntimeError("password=secret-password host=db.internal")

    async def time_out(**_: object) -> object:
        raise TimeoutError()

    hidden = PostgresReadOnlyQueryExecutor({}, timeout_seconds=1, connect=fail)
    timed = PostgresReadOnlyQueryExecutor({}, timeout_seconds=1, connect=time_out)

    async def run() -> None:
        with pytest.raises(DatabaseQueryFailedError) as captured:
            await hidden.execute("SELECT 1 AS value", {}, max_rows=1)
        assert captured.value.retryable is False
        assert "secret-password" not in str(captured.value)
        assert "db.internal" not in str(captured.value)
        with pytest.raises(DatabaseQueryFailedError) as timed_out:
            await timed.execute("SELECT 1 AS value", {}, max_rows=1)
        assert timed_out.value.retryable is True

    asyncio.run(run())


@pytest.mark.parametrize(
    "columns,rows",
    [
        (["value", "value"], [(1, 2)]),
        (["blob"], [(b"abc",)]),
    ],
)
def test_postgres_executor_rejects_duplicate_columns_and_binary_values(
    columns: list[str],
    rows: list[tuple[object, ...]],
) -> None:
    connection = FakeConnection(FakeStatement(columns, rows))

    async def connect(**_: object) -> FakeConnection:
        return connection

    executor = PostgresReadOnlyQueryExecutor({}, timeout_seconds=1, connect=connect)

    with pytest.raises(DatabaseQueryFailedError):
        asyncio.run(executor.execute("SELECT 1 AS value", {}, max_rows=1))


def test_postgres_configuration_requires_a_target_and_hides_the_password() -> None:
    settings = postgres_settings()
    target = settings.postgres_connection_target()

    assert settings.backend == "postgres"
    assert target["host"] == "127.0.0.1"
    assert target["password"] == "secret-password"
    assert target["ssl"] == "prefer"
    assert "secret-password" not in repr(settings)
    assert Settings(_env_file=None).phase5.sql_query.backend == "sqlite"

    with pytest.raises(ValidationError, match="host, database, and user"):
        SQLQueryToolSettings(backend="postgres")
    with pytest.raises(ValidationError, match="sslmode"):
        SQLQueryToolSettings(
            backend="postgres",
            postgres_dsn="postgresql://reader@127.0.0.1/demo?options=-cdefault_transaction_read_only%3Doff",
        )


def test_postgres_dsn_is_split_so_the_password_is_not_a_url() -> None:
    settings = SQLQueryToolSettings(
        backend="postgres",
        postgres_dsn="postgresql://reader:secret-password@127.0.0.1:5432/demo?sslmode=require",
    )
    target = settings.postgres_connection_target()

    assert "dsn" not in target
    assert target["user"] == "reader"
    assert target["password"] == "secret-password"
    assert target["database"] == "demo"
    assert target["ssl"] == "require"
    assert "secret-password" not in repr(settings)


def test_factory_selects_sqlite_by_default_and_postgres_when_configured() -> None:
    sqlite_executor = build_sql_query_executor(Settings(_env_file=None).phase5.sql_query)
    postgres_executor = build_sql_query_executor(postgres_settings())

    assert isinstance(sqlite_executor, SQLiteReadOnlyQueryExecutor)
    assert isinstance(postgres_executor, PostgresReadOnlyQueryExecutor)
    assert "secret-password" not in repr(postgres_executor)

    tool = SQLQueryTool(postgres_executor, timeout_seconds=5, default_max_rows=10)

    async def health() -> str:
        await tool.initialize()
        status = await tool.health_check()
        return status.providers["database"]

    assert asyncio.run(health()) == "postgres_read_only"


def test_sql_input_validation_still_rejects_writes_for_either_backend() -> None:
    with pytest.raises(ValidationError):
        SQLQueryInput(query="DELETE FROM items")


@pytest.mark.postgres
@pytest.mark.skipif(not LIVE_DSN, reason="TOOLBRIDGE_TEST_POSTGRES_DSN is not set")
def test_live_postgres_read_only_select_and_rejects_writes() -> None:
    settings = SQLQueryToolSettings(backend="postgres", postgres_dsn=LIVE_DSN)
    executor = PostgresReadOnlyQueryExecutor(
        settings.postgres_connection_target(),
        timeout_seconds=5,
    )

    async def run() -> None:
        result = await executor.execute("SELECT 1 AS value", {}, max_rows=1)
        assert result.rows == [{"value": 1}]
        assert result.truncated is False
        with pytest.raises(DatabaseQueryFailedError):
            await executor.execute("CREATE TABLE toolbridge_should_fail(id int)", {}, max_rows=1)

    asyncio.run(run())
