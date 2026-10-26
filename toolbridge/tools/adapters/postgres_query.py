"""Cancellable read-only PostgreSQL adapter behind a database-neutral port."""

from collections.abc import Awaitable, Callable
from datetime import date, datetime
from decimal import Decimal
from math import isfinite
from re import fullmatch
from time import perf_counter
from typing import Any
from uuid import UUID

from toolbridge.tools.application.phase5_ports import ReadOnlyQueryExecutor
from toolbridge.tools.domain.sql_query import SQLQueryOutput, SqlValue
from toolbridge.tools.domain.tool_errors import DatabaseQueryFailedError

_PARAM_NAME = r"[A-Za-z_][A-Za-z0-9_]*"
_QUOTES = {"'": "'", '"': '"', "`": "`", "[": "]"}
Connect = Callable[..., Awaitable[object]]


def read_only_server_settings(timeout_seconds: float) -> dict[str, str]:
    """Session settings that keep one PostgreSQL connection read-only and bounded."""

    timeout_ms = max(1, min(60_000, round(timeout_seconds * 1000)))
    return {
        "application_name": "toolbridge_sql_query",
        "default_transaction_read_only": "on",
        "statement_timeout": str(timeout_ms),
        "lock_timeout": str(min(timeout_ms, 1_000)),
        "idle_in_transaction_session_timeout": str(timeout_ms),
    }


def bind_named_parameters(
    query: str,
    parameters: dict[str, SqlValue],
    *,
    max_value_bytes: int,
) -> tuple[str, list[SqlValue]]:
    """Rewrite ``:name`` placeholders to asyncpg ``$n`` arguments.

    String literals, quoted identifiers, dollar quotes, and ``::`` casts are copied
    unchanged. Missing or oversized parameters fail before a connection is used.
    """

    rendered: list[str] = []
    arguments: list[SqlValue] = []
    positions: dict[str, int] = {}
    index = 0
    length = len(query)
    while index < length:
        dollar_end = _dollar_quote_end(query, index)
        if dollar_end is not None:
            rendered.append(query[index:dollar_end])
            index = dollar_end
            continue
        char = query[index]
        if char in _QUOTES:
            closing = _QUOTES[char]
            end = _quoted_end(query, index, closing)
            rendered.append(query[index:end])
            index = end
            continue
        if char == ":" and index + 1 < length and query[index + 1] == ":":
            rendered.append("::")
            index += 2
            continue
        if char == ":" and fullmatch(_PARAM_NAME, _parameter_name(query, index + 1)):
            name = _parameter_name(query, index + 1)
            if name not in parameters:
                raise DatabaseQueryFailedError()
            if name not in positions:
                arguments.append(_validate_parameter(parameters[name], max_value_bytes))
                positions[name] = len(arguments)
            rendered.append(f"${positions[name]}")
            index += 1 + len(name)
            continue
        rendered.append(char)
        index += 1
    return "".join(rendered), arguments


class PostgresReadOnlyQueryExecutor(ReadOnlyQueryExecutor):
    """Execute one statement in a read-only PostgreSQL transaction."""

    provider_id = "postgres_read_only"

    def __init__(
        self,
        connection: dict[str, object],
        *,
        timeout_seconds: float,
        max_value_bytes: int = 1_000_000,
        connect: Connect | None = None,
    ) -> None:
        self._connection = dict(connection)
        self._timeout_seconds = timeout_seconds
        self._max_value_bytes = max_value_bytes
        self._connect = connect

    def __repr__(self) -> str:
        """Hide host, user, and password from logs and traces."""

        return "PostgresReadOnlyQueryExecutor(provider_id='postgres_read_only')"

    def connection_arguments(self) -> dict[str, object]:
        """Return asyncpg connect arguments. Do not log the result: it may contain a password."""

        return {
            **self._connection,
            "timeout": self._timeout_seconds,
            "command_timeout": self._timeout_seconds,
            "server_settings": read_only_server_settings(self._timeout_seconds),
        }

    async def execute(
        self,
        query: str,
        parameters: dict[str, SqlValue],
        *,
        max_rows: int,
    ) -> SQLQueryOutput:
        """Run one bound read-only query and close the connection afterwards."""

        rewritten, arguments = bind_named_parameters(
            query,
            parameters,
            max_value_bytes=self._max_value_bytes,
        )
        started_at = perf_counter()
        try:
            connection = await self._open()
            try:
                return await self._execute_connected(
                    connection,
                    rewritten,
                    arguments,
                    max_rows,
                    started_at,
                )
            finally:
                close = getattr(connection, "close", None)
                if close is not None:
                    await close()
        except DatabaseQueryFailedError:
            raise
        except TimeoutError as error:
            raise DatabaseQueryFailedError(timed_out=True) from error
        except Exception as error:
            raise DatabaseQueryFailedError(timed_out=_is_timeout(error)) from error

    async def _open(self) -> object:
        arguments = self.connection_arguments()
        if self._connect is not None:
            return await self._connect(**arguments)
        try:
            import asyncpg
        except ImportError as error:
            raise DatabaseQueryFailedError() from error
        return await asyncpg.connect(**arguments)

    async def _execute_connected(
        self,
        connection: Any,
        query: str,
        arguments: list[SqlValue],
        max_rows: int,
        started_at: float,
    ) -> SQLQueryOutput:
        async with connection.transaction(readonly=True):
            statement = await connection.prepare(query, timeout=self._timeout_seconds)
            columns = [str(item.name) for item in statement.get_attributes()]
            if (
                not columns
                or len(columns) > 256
                or len(columns) != len(set(columns))
                or any(not name or len(name) > 256 for name in columns)
            ):
                raise DatabaseQueryFailedError()
            raw_rows: list[object] = []
            cursor = statement.cursor(
                *arguments,
                prefetch=min(max_rows + 1, 256),
                timeout=self._timeout_seconds,
            )
            async for record in cursor:
                raw_rows.append(record)
                if len(raw_rows) > max_rows:
                    break
        truncated = len(raw_rows) > max_rows
        rows = [
            {
                name: _normalize_sql_value(value, self._max_value_bytes)
                for name, value in zip(columns, _row_values(row, len(columns)), strict=True)
            }
            for row in raw_rows[:max_rows]
        ]
        return SQLQueryOutput(
            columns=columns,
            rows=rows,
            row_count=len(rows),
            truncated=truncated,
            execution_ms=round((perf_counter() - started_at) * 1_000, 3),
        )


def _parameter_name(query: str, start: int) -> str:
    end = start
    while end < len(query) and (query[end].isalnum() or query[end] == "_"):
        end += 1
    return query[start:end]


def _quoted_end(query: str, start: int, closing: str) -> int:
    index = start + 1
    while index < len(query):
        if query[index] == closing:
            if closing != "]" and index + 1 < len(query) and query[index + 1] == closing:
                index += 2
                continue
            return index + 1
        index += 1
    raise DatabaseQueryFailedError()


def _dollar_quote_end(query: str, start: int) -> int | None:
    if start >= len(query) or query[start] != "$":
        return None
    tag_end = query.find("$", start + 1)
    if tag_end == -1:
        return None
    tag = query[start : tag_end + 1]
    if fullmatch(r"\$[A-Za-z0-9_]*\$", tag) is None:
        return None
    close = query.find(tag, tag_end + 1)
    if close == -1:
        raise DatabaseQueryFailedError()
    return close + len(tag)


def _validate_parameter(value: SqlValue, max_value_bytes: int) -> SqlValue:
    if isinstance(value, str) and len(value.encode("utf-8")) > max_value_bytes:
        raise DatabaseQueryFailedError()
    if isinstance(value, int) and not isinstance(value, bool) and len(str(value)) > 256:
        raise DatabaseQueryFailedError()
    if isinstance(value, float) and not isfinite(value):
        raise DatabaseQueryFailedError()
    return value


def _normalize_sql_value(value: object, max_value_bytes: int) -> SqlValue:
    """Permit only JSON-safe scalar database values."""

    if isinstance(value, bool) or value is None:
        return value
    if isinstance(value, int):
        return value
    if isinstance(value, float):
        if not isfinite(value):
            raise DatabaseQueryFailedError()
        return value
    if isinstance(value, str):
        if len(value.encode("utf-8")) > max_value_bytes:
            raise DatabaseQueryFailedError()
        return value
    if isinstance(value, Decimal):
        if not value.is_finite():
            raise DatabaseQueryFailedError()
        rendered = format(value, "f")
        if len(rendered.encode("utf-8")) > max_value_bytes:
            raise DatabaseQueryFailedError()
        return rendered
    if isinstance(value, datetime | date | UUID):
        rendered = value.isoformat() if not isinstance(value, UUID) else str(value)
        if len(rendered.encode("utf-8")) > max_value_bytes:
            raise DatabaseQueryFailedError()
        return rendered
    raise DatabaseQueryFailedError()


def _row_values(row: object, width: int) -> list[object]:
    try:
        return [row[index] for index in range(width)]  # type: ignore[index]
    except (IndexError, KeyError, TypeError) as error:
        raise DatabaseQueryFailedError() from error


def _is_timeout(error: Exception) -> bool:
    return type(error).__name__ in {"QueryCanceledError", "TimeoutError"}
