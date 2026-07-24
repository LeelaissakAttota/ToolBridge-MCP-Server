"""Enterprise SQL Intelligence Engine.

Provides SQL query capabilities including:
- SQLite and DuckDB support
- CSV as SQL tables
- Natural Language to SQL conversion
- Safe query validation
- Read-only execution
"""

from __future__ import annotations

import asyncio
import re
import uuid
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Any, Optional

try:
    import sqlalchemy
    from sqlalchemy import create_engine, text, inspect, MetaData, Table
    from sqlalchemy.engine import Engine
    from sqlalchemy.exc import SQLAlchemyError
    SQLALCHEMY_AVAILABLE = True
except ImportError:
    SQLALCHEMY_AVAILABLE = False
    Engine = Any

try:
    import duckdb
    DUCKDB_AVAILABLE = True
except ImportError:
    DUCKDB_AVAILABLE = False

import logging

logger = logging.getLogger(__name__)


class DatabaseType(Enum):
    """Supported database types."""
    SQLITE = "sqlite"
    DUCKDB = "duckdb"
    POSTGRESQL = "postgresql"
    MYSQL = "mysql"


class QueryType(Enum):
    """Types of SQL queries."""
    SELECT = "select"
    INSERT = "insert"
    UPDATE = "update"
    DELETE = "delete"
    DDL = "ddl"
    UNKNOWN = "unknown"


@dataclass
class QueryResult:
    """Result of a SQL query execution."""
    success: bool
    data: list[dict[str, Any]] = field(default_factory=list)
    columns: list[str] = field(default_factory=list)
    row_count: int = 0
    execution_time_ms: float = 0.0
    error: Optional[str] = None
    query_id: str = field(default_factory=lambda: str(uuid.uuid4())[:8])

    def to_dict(self) -> dict[str, Any]:
        return {
            "success": self.success,
            "data": self.data,
            "columns": self.columns,
            "row_count": self.row_count,
            "execution_time_ms": self.execution_time_ms,
            "error": self.error,
            "query_id": self.query_id,
        }


@dataclass
class TableSchema:
    """Schema information for a table."""
    name: str
    columns: list[dict[str, Any]]
    primary_keys: list[str]
    foreign_keys: list[dict[str, Any]]
    indexes: list[dict[str, Any]]
    row_count: Optional[int] = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "columns": self.columns,
            "primary_keys": self.primary_keys,
            "foreign_keys": self.foreign_keys,
            "indexes": self.indexes,
            "row_count": self.row_count,
        }


@dataclass
class DatabaseInfo:
    """Database connection information."""
    type: DatabaseType
    connection_string: str
    tables: list[str] = field(default_factory=list)
    version: Optional[str] = None


class SQLValidator:
    """Validates SQL queries for safety."""

    # Read-only keywords that are allowed
    ALLOWED_KEYWORDS = {
        'SELECT', 'WITH', 'FROM', 'WHERE', 'GROUP BY', 'ORDER BY',
        'LIMIT', 'OFFSET', 'JOIN', 'INNER JOIN', 'LEFT JOIN', 'RIGHT JOIN',
        'FULL JOIN', 'CROSS JOIN', 'UNION', 'UNION ALL', 'INTERSECT',
        'EXCEPT', 'DISTINCT', 'AS', 'ON', 'AND', 'OR', 'NOT', 'IN',
        'BETWEEN', 'LIKE', 'ILIKE', 'IS', 'NULL', 'TRUE', 'FALSE',
        'CASE', 'WHEN', 'THEN', 'ELSE', 'END', 'CAST', 'EXTRACT',
        'DATE', 'DATETIME', 'TIMESTAMP', 'INTERVAL', 'NOW', 'CURRENT_DATE',
        'CURRENT_TIMESTAMP', 'COALESCE', 'NULLIF', 'ABS', 'ROUND',
        'FLOOR', 'CEIL', 'SQRT', 'POWER', 'LOG', 'LN', 'EXP',
        'UPPER', 'LOWER', 'TRIM', 'SUBSTRING', 'LENGTH', 'CONCAT',
    }

    # Dangerous keywords that are blocked
    BLOCKED_KEYWORDS = {
        'INSERT', 'UPDATE', 'DELETE', 'DROP', 'CREATE', 'ALTER',
        'TRUNCATE', 'REPLACE', 'MERGE', 'EXEC', 'EXECUTE', 'CALL',
        'PRAGMA', 'ATTACH', 'DETACH', 'VACUUM', 'ANALYZE',
        'GRANT', 'REVOKE', 'COMMIT', 'ROLLBACK', 'SAVEPOINT',
        'BEGIN', 'START TRANSACTION', 'SET', 'SHOW', 'DESCRIBE',
        'EXPLAIN', 'PREPARE', 'DEALLOCATE', 'DEALLOCATE PREPARE',
    }

    # Blocked patterns
    BLOCKED_PATTERNS = [
        r';\s*--',  # SQL comment after statement
        r'/\*.*\*/',  # Block comments
        r'xp_cmdshell',  # SQL Server
        r'sp_executesql',  # SQL Server
        r'UTL_FILE',  # Oracle
        r'DBMS_',  # Oracle packages
    ]

    @classmethod
    def validate(cls, query: str, allow_ddl: bool = False) -> tuple[bool, Optional[str]]:
        """Validate SQL query for safety."""
        query_upper = query.upper().strip()

        # Check for blocked keywords
        for keyword in cls.BLOCKED_KEYWORDS:
            if keyword in query_upper:
                # Allow SELECT with some blocked keywords in subqueries (e.g., WITH RECURSIVE)
                if keyword in ('CREATE', 'DROP', 'ALTER') and allow_ddl:
                    continue
                return False, f"Blocked keyword: {keyword}"

        # Check blocked patterns
        for pattern in cls.BLOCKED_PATTERNS:
            if re.search(pattern, query, re.IGNORECASE):
                return False, f"Blocked pattern: {pattern}"

        # Determine query type
        query_type = cls._get_query_type(query_upper)
        if query_type != QueryType.SELECT and not allow_ddl:
            return False, f"Only SELECT queries allowed, got {query_type.value}"

        # Check for multiple statements (basic check)
        statements = [s.strip() for s in query.split(';') if s.strip()]
        if len(statements) > 1:
            return False, "Multiple statements not allowed"

        return True, None

    @classmethod
    def _get_query_type(cls, query_upper: str) -> QueryType:
        """Determine the type of SQL query."""
        # Remove comments and leading whitespace
        cleaned = re.sub(r'--.*$', '', query_upper, flags=re.MULTILINE)
        cleaned = re.sub(r'/\*.*?\*/', '', cleaned, flags=re.DOTALL)
        cleaned = cleaned.strip()

        if cleaned.startswith('SELECT') or cleaned.startswith('WITH'):
            return QueryType.SELECT
        elif cleaned.startswith('INSERT'):
            return QueryType.INSERT
        elif cleaned.startswith('UPDATE'):
            return QueryType.UPDATE
        elif cleaned.startswith('DELETE'):
            return QueryType.DELETE
        elif any(cleaned.startswith(kw) for kw in ('CREATE', 'DROP', 'ALTER', 'TRUNCATE')):
            return QueryType.DDL
        return QueryType.UNKNOWN

    @classmethod
    def sanitize(cls, query: str) -> str:
        """Basic query sanitization."""
        # Remove comments
        query = re.sub(r'--.*$', '', query, flags=re.MULTILINE)
        query = re.sub(r'/\*.*?\*/', '', query, flags=re.DOTALL)
        # Limit length
        if len(query) > 10000:
            query = query[:10000]
        return query.strip()


class SQLExecutor(ABC):
    """Abstract SQL executor."""

    @abstractmethod
    async def execute(self, query: str, params: Optional[dict] = None) -> QueryResult:
        pass

    @abstractmethod
    async def get_schema(self, table_name: Optional[str] = None) -> list[TableSchema]:
        pass

    @abstractmethod
    async def get_tables(self) -> list[str]:
        pass

    @abstractmethod
    async def register_csv(self, csv_path: str, table_name: str) -> bool:
        pass

    @abstractmethod
    async def close(self) -> None:
        pass


class SQLiteExecutor(SQLExecutor):
    """SQLite SQL executor."""

    def __init__(self, connection_string: str = "sqlite:///:memory:"):
        if not SQLALCHEMY_AVAILABLE:
            raise RuntimeError("sqlalchemy not available. Install with: pip install sqlalchemy")

        self._engine = create_engine(connection_string, echo=False)
        self._metadata = MetaData()

    async def execute(self, query: str, params: Optional[dict] = None) -> QueryResult:
        # Validate query
        valid, error = SQLValidator.validate(query)
        if not valid:
            return QueryResult(success=False, error=f"Validation failed: {error}")

        start_time = datetime.now()
        try:
            with self._engine.connect() as conn:
                result = conn.execute(text(query), params or {})
                columns = list(result.keys()) if result.keys() else []
                rows = [dict(zip(columns, row)) for row in result.fetchall()]

            execution_time = (datetime.now() - start_time).total_seconds() * 1000
            return QueryResult(
                success=True,
                data=rows,
                columns=columns,
                row_count=len(rows),
                execution_time_ms=execution_time,
            )
        except SQLAlchemyError as e:
            execution_time = (datetime.now() - start_time).total_seconds() * 1000
            return QueryResult(
                success=False,
                error=str(e),
                execution_time_ms=execution_time,
            )

    async def get_schema(self, table_name: Optional[str] = None) -> list[TableSchema]:
        inspector = inspect(self._engine)
        schemas = []

        tables = [table_name] if table_name else inspector.get_table_names()
        for table in tables:
            columns = inspector.get_columns(table)
            pk = inspector.get_pk_constraint(table)
            fks = inspector.get_foreign_keys(table)
            indexes = inspector.get_indexes(table)

            schemas.append(TableSchema(
                name=table,
                columns=[{
                    "name": c["name"],
                    "type": str(c["type"]),
                    "nullable": c["nullable"],
                    "default": c.get("default"),
                    "primary_key": c["name"] in pk.get("constrained_columns", []),
                } for c in columns],
                primary_keys=pk.get("constrained_columns", []),
                foreign_keys=fks,
                indexes=[{"name": i["name"], "columns": i["column_names"], "unique": i["unique"]} for i in indexes],
            ))

        return schemas

    async def get_tables(self) -> list[str]:
        inspector = inspect(self._engine)
        return inspector.get_table_names()

    async def register_csv(self, csv_path: str, table_name: str) -> bool:
        """Register CSV file as a SQLite table."""
        try:
            import pandas as pd
            df = pd.read_csv(csv_path)
            df.to_sql(table_name, self._engine, if_exists='replace', index=False)
            return True
        except Exception as e:
            logger.error(f"Failed to register CSV: {e}")
            return False

    async def close(self) -> None:
        self._engine.dispose()


class DuckDBExecutor(SQLExecutor):
    """DuckDB SQL executor for analytical queries."""

    def __init__(self, database: str = ":memory:"):
        if not DUCKDB_AVAILABLE:
            raise RuntimeError("duckdb not available. Install with: pip install duckdb")

        self._conn = duckdb.connect(database)

    async def execute(self, query: str, params: Optional[dict] = None) -> QueryResult:
        # Validate query
        valid, error = SQLValidator.validate(query)
        if not valid:
            return QueryResult(success=False, error=f"Validation failed: {error}")

        start_time = datetime.now()
        try:
            if params:
                result = self._conn.execute(query, params).fetchall()
            else:
                result = self._conn.execute(query).fetchall()

            # Get column names
            columns = [desc[0] for desc in self._conn.description] if self._conn.description else []
            rows = [dict(zip(columns, row)) for row in result]

            execution_time = (datetime.now() - start_time).total_seconds() * 1000
            return QueryResult(
                success=True,
                data=rows,
                columns=columns,
                row_count=len(rows),
                execution_time_ms=execution_time,
            )
        except Exception as e:
            execution_time = (datetime.now() - start_time).total_seconds() * 1000
            return QueryResult(
                success=False,
                error=str(e),
                execution_time_ms=execution_time,
            )

    async def get_schema(self, table_name: Optional[str] = None) -> list[TableSchema]:
        schemas = []
        tables = [table_name] if table_name else self._conn.execute("SHOW TABLES").fetchall()

        for (table,) in tables:
            # Get column info
            columns_info = self._conn.execute(f"DESCRIBE {table}").fetchall()
            columns = [{
                "name": c[0],
                "type": c[1],
                "nullable": c[2] == "YES",
                "primary_key": c[3] == "PRI",
            } for c in columns_info]

            schemas.append(TableSchema(
                name=table,
                columns=columns,
                primary_keys=[c["name"] for c in columns if c["primary_key"]],
                foreign_keys=[],
                indexes=[],
            ))

        return schemas

    async def get_tables(self) -> list[str]:
        result = self._conn.execute("SHOW TABLES").fetchall()
        return [row[0] for row in result]

    async def register_csv(self, csv_path: str, table_name: str) -> bool:
        """Register CSV file as a DuckDB table."""
        try:
            # DuckDB can read CSV directly
            self._conn.execute(f"""
                CREATE OR REPLACE TABLE {table_name} AS
                SELECT * FROM read_csv_auto('{csv_path}')
            """)
            return True
        except Exception as e:
            logger.error(f"Failed to register CSV: {e}")
            return False

    async def close(self) -> None:
        self._conn.close()


class SQLIntelligenceEngine:
    """
    Enterprise SQL Intelligence Engine.

    Features:
    - Multiple database backends (SQLite, DuckDB)
    - CSV as SQL tables
    - Natural Language to SQL (template-based)
    - Safe query validation
    - Read-only execution
    - Schema introspection
    """

    def __init__(
        self,
        default_db: DatabaseType = DatabaseType.SQLITE,
        sqlite_path: str = ":memory:",
        duckdb_path: str = ":memory:",
    ):
        self._executors: dict[DatabaseType, SQLExecutor] = {}
        self._default_db = default_db

        if default_db == DatabaseType.SQLITE or DatabaseType.SQLITE in (DatabaseType.SQLITE, DatabaseType.DUCKDB):
            self._executors[DatabaseType.SQLITE] = SQLiteExecutor(f"sqlite:///{sqlite_path}")

        if default_db == DatabaseType.DUCKDB or DatabaseType.DUCKDB in (DatabaseType.SQLITE, DatabaseType.DUCKDB):
            if DUCKDB_AVAILABLE:
                self._executors[DatabaseType.DUCKDB] = DuckDBExecutor(duckdb_path)

    @property
    def default_executor(self) -> SQLExecutor:
        return self._executors.get(self._default_db, next(iter(self._executors.values())))

    async def execute(
        self,
        query: str,
        params: Optional[dict] = None,
        db: Optional[DatabaseType] = None,
    ) -> QueryResult:
        """Execute SQL query."""
        executor = self._executors.get(db or self._default_db, self.default_executor)
        return await executor.execute(query, params)

    async def get_schema(self, table_name: Optional[str] = None, db: Optional[DatabaseType] = None) -> list[TableSchema]:
        """Get table schema."""
        executor = self._executors.get(db or self._default_db, self.default_executor)
        return await executor.get_schema(table_name)

    async def get_tables(self, db: Optional[DatabaseType] = None) -> list[str]:
        """Get list of tables."""
        executor = self._executors.get(db or self._default_db, self.default_executor)
        return await executor.get_tables()

    async def register_csv(
        self,
        csv_path: str,
        table_name: str,
        db: Optional[DatabaseType] = None,
    ) -> bool:
        """Register CSV file as SQL table."""
        executor = self._executors.get(db or self._default_db, self.default_executor)
        return await executor.register_csv(csv_path, table_name)

    async def close(self) -> None:
        """Close all connections."""
        for executor in self._executors.values():
            await executor.close()

    # Natural Language to SQL (template-based)

    @dataclass
    class NLTemplate:
        """Natural language to SQL template."""
        pattern: str
        sql_template: str
        params: list[str] = field(default_factory=list)

    # Built-in NL templates
    NL_TEMPLATES = [
        NLTemplate(
            pattern=r"show (?:me )?(?:all )?(\w+)",
            sql_template="SELECT * FROM {table} LIMIT 100",
            params=["table"],
        ),
        NLTemplate(
            pattern=r"how many (?:rows|records) (?:in|are in) (\w+)",
            sql_template="SELECT COUNT(*) as count FROM {table}",
            params=["table"],
        ),
        NLTemplate(
            pattern=r"(?:top|bottom) (\d+) (\w+) by (\w+)(?: (asc|desc))?",
            sql_template="SELECT * FROM {table} ORDER BY {column} {direction} LIMIT {limit}",
            params=["limit", "table", "column", "direction"],
        ),
        NLTemplate(
            pattern=r"average (\w+) (?:in|of|for) (\w+)(?: where (\w+) (?:>|<|=|>=|<=) (.*))?",
            sql_template="SELECT AVG({column}) as average FROM {table} WHERE {condition}",
            params=["column", "table", "condition"],
        ),
        NLTemplate(
            pattern=r"sum (\w+) (?:in|of|for) (\w+)(?: where (\w+) (?:>|<|=|>=|<=) (.*))?",
            sql_template="SELECT SUM({column}) as total FROM {table} WHERE {condition}",
            params=["column", "table", "condition"],
        ),
        NLTemplate(
            pattern=r"group by (\w+) (?:in|from) (\w+)",
            sql_template="SELECT {column}, COUNT(*) as count FROM {table} GROUP BY {column}",
            params=["column", "table"],
        ),
        NLTemplate(
            pattern=r"(?:show|list) (?:all )?tables",
            sql_template="SELECT name FROM sqlite_master WHERE type='table'",
            params=[],
        ),
    ]

    def natural_language_to_sql(self, query: str) -> Optional[str]:
        """Convert natural language to SQL using templates."""
        query_lower = query.lower().strip()

        for template in self.NL_TEMPLATES:
            match = re.search(template.pattern, query_lower)
            if match:
                params = match.groups()
                param_dict = dict(zip(template.params, params))

                # Handle direction default
                if 'direction' in template.params and 'direction' not in param_dict:
                    param_dict['direction'] = 'DESC'

                # Handle condition default
                if 'condition' in template.params and 'condition' not in param_dict:
                    param_dict['condition'] = '1=1'

                return template.sql_template.format(**param_dict)

        return None

    async def query_from_natural_language(
        self,
        query: str,
        params: Optional[dict] = None,
        db: Optional[DatabaseType] = None,
    ) -> QueryResult:
        """Execute query from natural language."""
        sql = self.natural_language_to_sql(query)
        if not sql:
            return QueryResult(
                success=False,
                error="Could not parse natural language query. Try being more specific."
            )

        logger.info(f"NL to SQL: {query} -> {sql}")
        return await self.execute(sql, params, db)

    # Query builder helpers

    @staticmethod
    def select(
        table: str,
        columns: Optional[list[str]] = None,
        where: Optional[str] = None,
        order_by: Optional[str] = None,
        limit: Optional[int] = None,
        offset: Optional[int] = None,
    ) -> str:
        """Build SELECT query."""
        cols = ", ".join(columns) if columns else "*"
        query = f"SELECT {cols} FROM {table}"

        if where:
            query += f" WHERE {where}"
        if order_by:
            query += f" ORDER BY {order_by}"
        if limit:
            query += f" LIMIT {limit}"
        if offset:
            query += f" OFFSET {offset}"

        return query

    @staticmethod
    def aggregate(
        table: str,
        group_by: list[str],
        aggregations: dict[str, str],  # column -> function
        where: Optional[str] = None,
        having: Optional[str] = None,
    ) -> str:
        """Build aggregation query."""
        group_cols = ", ".join(group_by)
        agg_cols = ", ".join(f"{func}({col}) as {col}_{func.lower()}" for col, func in aggregations.items())

        query = f"SELECT {group_cols}, {agg_cols} FROM {table}"

        if where:
            query += f" WHERE {where}"
        query += f" GROUP BY {group_cols}"
        if having:
            query += f" HAVING {having}"

        return query

    @staticmethod
    def join(
        left_table: str,
        right_table: str,
        left_key: str,
        right_key: str,
        join_type: str = "INNER",
        columns: Optional[list[str]] = None,
        where: Optional[str] = None,
    ) -> str:
        """Build JOIN query."""
        cols = ", ".join(columns) if columns else "*"
        query = f"""
        SELECT {cols}
        FROM {left_table} l
        {join_type} JOIN {right_table} r ON l.{left_key} = r.{right_key}
        """
        if where:
            query += f" WHERE {where}"

        return query.strip()


# Convenience functions
async def create_sql_engine(
    db_type: DatabaseType = DatabaseType.SQLITE,
    **kwargs,
) -> SQLIntelligenceEngine:
    """Create SQL intelligence engine."""
    engine = SQLIntelligenceEngine(default_db=db_type, **kwargs)
    return engine


async def csv_to_sql_table(
    csv_path: str,
    table_name: str,
    db_type: DatabaseType = DatabaseType.SQLITE,
    **kwargs,
) -> bool:
    """Convert CSV to SQL table."""
    engine = await create_sql_engine(db_type, **kwargs)
    try:
        return await engine.register_csv(csv_path, table_name)
    finally:
        await engine.close()


async def query_csv_with_sql(
    csv_path: str,
    query: str,
    table_name: str = "data",
    db_type: DatabaseType = DatabaseType.SQLITE,
    **kwargs,
) -> QueryResult:
    """Query CSV file using SQL."""
    engine = await create_sql_engine(db_type, **kwargs)
    try:
        await engine.register_csv(csv_path, table_name)
        return await engine.execute(query)
    finally:
        await engine.close()