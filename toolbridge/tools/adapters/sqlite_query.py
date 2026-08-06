"""Cancellable read-only SQLite adapter behind a database-neutral port."""

import asyncio
import sqlite3
from math import isfinite
from pathlib import Path
from time import monotonic, perf_counter

from toolbridge.tools.application.phase5_ports import ReadOnlyQueryExecutor
from toolbridge.tools.domain.sql_query import SQLQueryOutput, SqlValue
from toolbridge.tools.domain.tool_errors import DatabaseQueryFailedError


class SQLiteReadOnlyQueryExecutor(ReadOnlyQueryExecutor):
    """Execute one statement in SQLite query-only mode with progress timeout."""

    def __init__(
        self,
        database_path: str,
        *,
        database_root: Path,
        timeout_seconds: float,
        progress_operations: int,
    ) -> None:
        self._database_path = database_path
        self._database_root = database_root.resolve()
        self._timeout_seconds = timeout_seconds
        self._progress_operations = progress_operations

    async def execute(
        self,
        query: str,
        parameters: dict[str, SqlValue],
        *,
        max_rows: int,
    ) -> SQLQueryOutput:
        """Run SQLite work in a thread while its progress handler enforces time."""

        return await asyncio.to_thread(
            self._execute_sync,
            query,
            parameters,
            max_rows,
        )

    def _execute_sync(
        self,
        query: str,
        parameters: dict[str, SqlValue],
        max_rows: int,
    ) -> SQLQueryOutput:
        started_at = perf_counter()
        deadline = monotonic() + self._timeout_seconds
        try:
            connection = self._connect()
            try:
                connection.execute("PRAGMA query_only = ON")
                connection.set_progress_handler(
                    lambda: int(monotonic() >= deadline),
                    self._progress_operations,
                )
                cursor = connection.execute(query, parameters)
                if cursor.description is None:
                    raise DatabaseQueryFailedError()
                columns = [str(item[0]) for item in cursor.description]
                if len(columns) != len(set(columns)) or any(
                    not name or len(name) > 256
                    for name in columns
                ):
                    raise DatabaseQueryFailedError()
                raw_rows = cursor.fetchmany(max_rows + 1)
            finally:
                connection.close()
        except DatabaseQueryFailedError:
            raise
        except sqlite3.OperationalError as error:
            timed_out = "interrupted" in str(error).lower() or monotonic() >= deadline
            raise DatabaseQueryFailedError(timed_out=timed_out) from error
        except sqlite3.Error as error:
            raise DatabaseQueryFailedError() from error

        truncated = len(raw_rows) > max_rows
        rows = [
            {name: _normalize_sql_value(value) for name, value in zip(columns, row, strict=True)}
            for row in raw_rows[:max_rows]
        ]
        return SQLQueryOutput(
            columns=columns,
            rows=rows,
            row_count=len(rows),
            truncated=truncated,
            execution_ms=round((perf_counter() - started_at) * 1_000, 3),
        )

    def _connect(self) -> sqlite3.Connection:
        if self._database_path == ":memory:":
            return sqlite3.connect(":memory:", timeout=self._timeout_seconds)
        candidate = (self._database_root / self._database_path).resolve()
        if not candidate.is_relative_to(self._database_root) or not candidate.is_file():
            raise DatabaseQueryFailedError()
        uri = f"{candidate.as_uri()}?mode=ro"
        return sqlite3.connect(uri, uri=True, timeout=self._timeout_seconds)


def _normalize_sql_value(value: object) -> SqlValue:
    """Permit only JSON-safe scalar database values."""

    if value is None or isinstance(value, (str, int, bool)):
        return value
    if isinstance(value, float) and isfinite(value):
        return value
    raise DatabaseQueryFailedError()
