"""Provider-neutral contracts for bounded read-only SQL queries."""

from re import compile as compile_pattern

from pydantic import Field, field_validator

from toolbridge.core.contracts import ToolInput, ToolOutput

SqlValue = str | int | float | bool | None

_FORBIDDEN_KEYWORDS = frozenset(
    {
        "INSERT",
        "UPDATE",
        "DELETE",
        "DROP",
        "ALTER",
        "CREATE",
        "REPLACE",
        "ATTACH",
        "DETACH",
        "PRAGMA",
        "VACUUM",
        "REINDEX",
        "ANALYZE",
        "BEGIN",
        "COMMIT",
        "ROLLBACK",
        "SAVEPOINT",
        "RELEASE",
    }
)
# Keywords that are also legitimate read-only scalar functions when called as name(...).
_FUNCTION_KEYWORDS = frozenset({"REPLACE"})
_WORD = compile_pattern(r"[A-Za-z_][A-Za-z0-9_$]*")
_QUOTES = {"'": "'", '"': '"', "`": "`", "[": "]"}


def _scan_sql(query: str) -> list[tuple[str, str]]:
    """Split SQL into bare words and punctuation, skipping literals and quoted names.

    Returns ``(kind, value)`` pairs where kind is ``word`` or ``char``. Content inside
    string literals and quoted identifiers is never returned, so keywords there do
    not trigger the read-only checks.
    """

    tokens: list[tuple[str, str]] = []
    index = 0
    length = len(query)
    while index < length:
        char = query[index]
        if char in _QUOTES:
            closing = _QUOTES[char]
            index += 1
            while True:
                if index >= length:
                    raise ValueError("query contains an unterminated quoted value")
                if query[index] == closing:
                    # SQL escapes a quote by doubling it ('it''s'); brackets cannot double.
                    if closing != "]" and index + 1 < length and query[index + 1] == closing:
                        index += 2
                        continue
                    index += 1
                    break
                index += 1
            tokens.append(("literal", ""))
            continue
        match = _WORD.match(query, index)
        if match:
            tokens.append(("word", match.group(0).upper()))
            index = match.end()
            continue
        if query.startswith(("--", "/*", "*/"), index):
            raise ValueError("query comments and statement separators are not allowed")
        if not char.isspace():
            tokens.append(("char", char))
        index += 1
    return tokens


def validate_read_only_sql(query: str) -> str:
    """Reject multi-statement, commented, or mutating SQL before execution."""

    normalized = query.strip()
    tokens = _scan_sql(normalized) if normalized else []
    if not tokens or tokens[0] not in {("word", "SELECT"), ("word", "WITH")}:
        raise ValueError("query must start with SELECT or WITH")
    for position, (kind, value) in enumerate(tokens):
        if kind == "char" and value == ";":
            raise ValueError("query comments and statement separators are not allowed")
        if kind == "word" and value in _FORBIDDEN_KEYWORDS:
            is_call = tokens[position + 1 : position + 2] == [("char", "(")]
            if value in _FUNCTION_KEYWORDS and is_call:
                continue
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
