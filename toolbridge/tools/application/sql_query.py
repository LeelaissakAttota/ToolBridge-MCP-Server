"""Managed read-only SQL Query Tool."""

from datetime import UTC, datetime

from toolbridge.core.contracts import ToolDefinition
from toolbridge.tools.application.phase5_ports import ReadOnlyQueryExecutor
from toolbridge.tools.application.ports import BaseTool
from toolbridge.tools.domain.models import ToolHealthState, ToolHealthStatus
from toolbridge.tools.domain.sql_query import SQLQueryInput, SQLQueryOutput


class SQLQueryTool(BaseTool):
    """Execute validated read-only SQL through a database-neutral port."""

    def __init__(
        self,
        executor: ReadOnlyQueryExecutor,
        *,
        timeout_seconds: float,
        default_max_rows: int,
    ) -> None:
        self._executor = executor
        self._default_max_rows = default_max_rows
        self._definition = ToolDefinition(
            name="sql_query",
            description=(
                "Execute one bounded read-only SELECT query against the configured database."
            ),
            input_model=SQLQueryInput,
            output_model=SQLQueryOutput,
            handler=self.execute,
            timeout_seconds=timeout_seconds,
        )
        self._state = ToolHealthState.UNINITIALIZED
        self._last_success_at: datetime | None = None
        self._last_failure_at: datetime | None = None

    @property
    def definition(self) -> ToolDefinition:
        """Return the immutable SQL Query registration contract."""

        return self._definition

    async def initialize(self) -> None:
        """Mark the configured read-only adapter ready."""

        self._state = ToolHealthState.HEALTHY

    async def execute(self, arguments: SQLQueryInput) -> SQLQueryOutput:
        """Execute one validated query with a configured row ceiling."""

        maximum = min(arguments.max_rows or self._default_max_rows, self._default_max_rows)
        try:
            result = await self._executor.execute(
                arguments.query,
                arguments.parameters,
                max_rows=maximum,
            )
        except BaseException:
            self._last_failure_at = datetime.now(UTC)
            raise
        self._last_success_at = datetime.now(UTC)
        return result

    async def health_check(self) -> ToolHealthStatus:
        """Return local adapter lifecycle health without running a query."""

        return ToolHealthStatus(
            tool_name=self._definition.name,
            status=self._state,
            checked_at=datetime.now(UTC),
            last_success_at=self._last_success_at,
            last_failure_at=self._last_failure_at,
            providers={"database": "sqlite_read_only"},
        )

    async def close(self) -> None:
        """Mark the stateless SQL tool closed."""

        self._state = ToolHealthState.CLOSED
