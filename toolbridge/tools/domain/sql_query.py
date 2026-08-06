"""Provider-neutral contracts for bounded read-only SQL queries."""

from re import IGNORECASE, compile as compile_pattern

from pydantic import Field, field_validator

from toolbridge.core.contracts import ToolInput, ToolOutput

SqlValue = str | int | float | bool | None

_FORBIDDEN_SQL = compile_pattern(
    r"\b(?:INSERT|UPDATE|DELETE|DROP|ALTER|CREATE|REPLACE|ATTACH|DETACH|"
    r"PRAGMA|VACUUM|REINDEX|ANALYZE|BEGIN|COMMIT|ROLLBACK|SAVEPOINT|RELEASE)\b",
    IGNORECASE,
)
_READ_ONLY_START = compile_pattern(r"^\s*(?:SELECT|WITH)\b", IGNORECASE)


def validate_read_only_sql(query: str) -> str:
    """Reject multi-statement, commented, or mutating SQL before execution."""

    normalized = query.strip()
    if not normalized or not _READ_ONLY_START.match(normalized):
        raise ValueError("query must start with SELECT or WITH")
    if ";" in normalized or "--" in normalized or "/*" in normalized or "*/" in normalized:
        raise ValueError("query comments and statement separators are not allowed")
    if _FORBIDDEN_SQL.search(normalized):
        raise ValueError("query contains a forbidden SQL operation")
    return normalized


class SQLQueryInput(ToolInput):
    """Validated read-only SQL query and named parameters."""

    query: str = Field(min_length=1, max_length=20_000)
    parameters: dict[str, SqlValue] = Field(default_factory=dict)
    max_rows: int | None = Field(default=None, ge=1, le=1_000)

    @field_validator("query")
    @classmethod
    def require_read_only_query(cls, value: str) -> str:
        """Apply conservative read-only SQL validation."""

        return validate_read_only_sql(value)


class SQLQueryOutput(ToolOutput):
    """Bounded tabular result returned by a SQL adapter."""

    columns: list[str] = Field(max_length=256)
    rows: list[dict[str, SqlValue]] = Field(max_length=1_000)
    row_count: int = Field(ge=0, le=1_000)
    truncated: bool
    execution_ms: float = Field(ge=0)
