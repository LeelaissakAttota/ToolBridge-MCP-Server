"""Managed CSV Analysis Tool."""

from datetime import UTC, datetime

from toolbridge.core.contracts import ToolDefinition
from toolbridge.tools.application.phase5_ports import CSVDataSource
from toolbridge.tools.application.ports import BaseTool
from toolbridge.tools.domain.csv_analysis import CSVAnalysisInput, CSVAnalysisOutput
from toolbridge.tools.domain.models import ToolHealthState, ToolHealthStatus


class CSVAnalysisTool(BaseTool):
    """Inspect one confined CSV file through a replaceable data-source port."""

    def __init__(
        self,
        data_source: CSVDataSource,
        *,
        timeout_seconds: float,
        default_preview_rows: int,
    ) -> None:
        self._data_source = data_source
        self._default_preview_rows = default_preview_rows
        self._definition = ToolDefinition(
            name="csv_analysis",
            description=(
                "Analyze a configured CSV file with schema, summary, missing values, and preview."
            ),
            input_model=CSVAnalysisInput,
            output_model=CSVAnalysisOutput,
            handler=self.execute,
            timeout_seconds=timeout_seconds,
        )
        self._state = ToolHealthState.UNINITIALIZED
        self._last_success_at: datetime | None = None
        self._last_failure_at: datetime | None = None

    @property
    def definition(self) -> ToolDefinition:
        """Return the immutable CSV Analysis registration contract."""

        return self._definition

    async def initialize(self) -> None:
        """Mark the configured local data source ready."""

        self._state = ToolHealthState.HEALTHY

    async def execute(self, arguments: CSVAnalysisInput) -> CSVAnalysisOutput:
        """Analyze one validated relative CSV path."""

        preview_rows = min(
            arguments.preview_rows or self._default_preview_rows,
            self._default_preview_rows,
        )
        try:
            result = await self._data_source.analyze(
                arguments.relative_path,
                preview_rows=preview_rows,
            )
        except BaseException:
            self._last_failure_at = datetime.now(UTC)
            raise
        self._last_success_at = datetime.now(UTC)
        return result

    async def health_check(self) -> ToolHealthStatus:
        """Return local lifecycle health without reading a file."""

        return ToolHealthStatus(
            tool_name=self._definition.name,
            status=self._state,
            checked_at=datetime.now(UTC),
            last_success_at=self._last_success_at,
            last_failure_at=self._last_failure_at,
        )

    async def close(self) -> None:
        """Mark the stateless CSV tool closed."""

        self._state = ToolHealthState.CLOSED
