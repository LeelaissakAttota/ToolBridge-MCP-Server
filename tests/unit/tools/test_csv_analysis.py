"""CSV schema, statistics, preview, validation, and error tests."""

import asyncio

import pytest
from pydantic import ValidationError

from toolbridge.tools.adapters.csv_file import LocalCSVDataSource
from toolbridge.tools.application.csv_analysis import CSVAnalysisTool
from toolbridge.tools.domain.csv_analysis import CSVAnalysisInput, CSVColumnType
from toolbridge.tools.domain.tool_errors import FileAnalysisFailedError


def build_source(root: object, *, max_rows: int = 100) -> LocalCSVDataSource:
    """Build a bounded local analyzer for tests."""

    return LocalCSVDataSource(
        root,
        encoding="utf-8",
        max_file_bytes=10_000,
        max_rows_scanned=max_rows,
        max_columns=10,
        max_field_characters=1_000,
    )


def test_csv_analysis_returns_columns_statistics_missing_values_and_preview(
    tmp_path: object,
) -> None:
    csv_path = tmp_path / "sales.csv"
    csv_path.write_text(
        "name,amount,active\nalpha,10,true\nbeta,,false\ngamma,20,true\n",
        encoding="utf-8",
    )
    tool = CSVAnalysisTool(
        build_source(tmp_path),
        timeout_seconds=2,
        default_preview_rows=2,
    )

    async def run() -> object:
        await tool.initialize()
        result = await tool.execute(CSVAnalysisInput(relative_path="sales.csv"))
        await tool.close()
        return result

    result = asyncio.run(run())

    assert result.columns == ["name", "amount", "active"]
    assert result.row_count == 3
    assert len(result.preview) == 2
    by_name = {summary.name: summary for summary in result.summaries}
    assert by_name["amount"].inferred_type is CSVColumnType.INTEGER
    assert by_name["amount"].missing_count == 1
    assert by_name["amount"].mean == 15
    assert by_name["active"].inferred_type is CSVColumnType.BOOLEAN


def test_csv_analysis_rejects_traversal_and_non_csv_paths() -> None:
    with pytest.raises(ValidationError):
        CSVAnalysisInput(relative_path="../secret.csv")
    with pytest.raises(ValidationError):
        CSVAnalysisInput(relative_path="notes.txt")


def test_csv_analysis_normalizes_missing_and_malformed_files(tmp_path: object) -> None:
    source = build_source(tmp_path)

    async def missing() -> None:
        with pytest.raises(FileAnalysisFailedError) as captured:
            await source.analyze("missing.csv", preview_rows=2)
        assert captured.value.details == {"error_category": "not_found"}

    asyncio.run(missing())

    malformed = tmp_path / "malformed.csv"
    malformed.write_text("a,b\n1,2,3\n", encoding="utf-8")

    async def invalid() -> None:
        with pytest.raises(FileAnalysisFailedError):
            await source.analyze("malformed.csv", preview_rows=2)

    asyncio.run(invalid())


def test_csv_analysis_enforces_scan_limit(tmp_path: object) -> None:
    (tmp_path / "rows.csv").write_text("value\n1\n2\n3\n", encoding="utf-8")

    result = asyncio.run(build_source(tmp_path, max_rows=2).analyze("rows.csv", preview_rows=5))

    assert result.row_count == 2
    assert result.truncated is True
    assert len(result.preview) == 2
