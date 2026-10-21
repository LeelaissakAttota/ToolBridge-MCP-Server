"""Provider-neutral contracts for bounded CSV inspection."""

from enum import StrEnum
from pathlib import PurePath

from pydantic import Field, field_validator

from toolbridge.core.contracts import ToolInput, ToolOutput


class CSVColumnType(StrEnum):
    """Normalized inferred CSV column types."""

    EMPTY = "empty"
    INTEGER = "integer"
    NUMBER = "number"
    BOOLEAN = "boolean"
    TEXT = "text"
    MIXED = "mixed"


class CSVAnalysisInput(ToolInput):
    """Validated relative CSV file request."""

    relative_path: str = Field(min_length=1, max_length=512)
    preview_rows: int | None = Field(default=None, ge=1, le=100)

    @field_validator("relative_path")
    @classmethod
    def require_safe_relative_path(cls, value: str) -> str:
        """Reject absolute paths and traversal before filesystem access."""

        normalized = value.strip().replace("\\", "/")
        path = PurePath(normalized)
        if not normalized or path.is_absolute() or ".." in path.parts:
            raise ValueError("relative_path must stay within the configured CSV root")
        if path.suffix.lower() != ".csv":
            raise ValueError("relative_path must identify a CSV file")
        return normalized


class CSVColumnSummary(ToolOutput):
    """Per-column type, completeness, and numeric statistics."""

    name: str = Field(min_length=1, max_length=256)
    inferred_type: CSVColumnType
    non_null_count: int = Field(ge=0)
    missing_count: int = Field(ge=0)
    unique_count: int = Field(ge=0)
    minimum: float | None = None
    maximum: float | None = None
    mean: float | None = None


class CSVAnalysisOutput(ToolOutput):
    """Structured CSV schema, summary, missing values, and preview."""

    file_name: str = Field(min_length=1, max_length=256)
    delimiter: str = Field(min_length=1, max_length=1)
    columns: list[str] = Field(max_length=256)
    row_count: int = Field(ge=0)
    scanned_rows: int = Field(ge=0)
    truncated: bool
    summaries: list[CSVColumnSummary] = Field(max_length=256)
    preview: list[dict[str, str | None]] = Field(max_length=100)
