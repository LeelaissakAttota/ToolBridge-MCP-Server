"""Enterprise CSV Intelligence Engine.

Provides comprehensive CSV processing capabilities including schema detection,
column mapping, data profiling, filtering, sorting, grouping, aggregation,
and export functionality.
"""

from __future__ import annotations

import asyncio
import csv
import io
import json
import os
import re
import uuid
from abc import ABC, abstractmethod
from collections import defaultdict
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Any, Optional

try:
    import pandas as pd
    PANDAS_AVAILABLE = True
except ImportError:
    PANDAS_AVAILABLE = False

import logging

logger = logging.getLogger(__name__)


class ColumnType(Enum):
    """Detected column data types."""
    INTEGER = "integer"
    FLOAT = "float"
    STRING = "string"
    BOOLEAN = "boolean"
    DATE = "date"
    DATETIME = "datetime"
    CURRENCY = "currency"
    PERCENTAGE = "percentage"
    CATEGORICAL = "categorical"
    UNKNOWN = "unknown"


class AggregationFunction(Enum):
    """Supported aggregation functions."""
    SUM = "sum"
    MEAN = "mean"
    MEDIAN = "median"
    MIN = "min"
    MAX = "max"
    COUNT = "count"
    COUNT_DISTINCT = "count_distinct"
    STD = "std"
    VAR = "var"
    FIRST = "first"
    LAST = "last"


@dataclass
class ColumnProfile:
    """Profile of a CSV column."""
    name: str
    index: int
    detected_type: ColumnType
    sample_values: list[Any] = field(default_factory=list)
    null_count: int = 0
    unique_count: int = 0
    total_count: int = 0
    min_value: Optional[Any] = None
    max_value: Optional[Any] = None
    mean_value: Optional[float] = None
    std_value: Optional[float] = None
    top_values: list[tuple[Any, int]] = field(default_factory=list)
    is_monotonic: bool = False
    is_unique: bool = False
    pattern: Optional[str] = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "index": self.index,
            "type": self.detected_type.value,
            "null_count": self.null_count,
            "unique_count": self.unique_count,
            "total_count": self.total_count,
            "null_percentage": self.null_count / self.total_count * 100 if self.total_count > 0 else 0,
            "min": self.min_value,
            "max": self.max_value,
            "mean": self.mean_value,
            "std": self.std_value,
            "top_values": self.top_values[:10],
            "is_monotonic": self.is_monotonic,
            "is_unique": self.is_unique,
            "pattern": self.pattern,
        }


@dataclass
class CSVSchema:
    """Detected schema for a CSV file."""
    columns: list[ColumnProfile]
    row_count: int
    delimiter: str
    encoding: str
    has_header: bool
    file_size: int
    detected_at: datetime = field(default_factory=datetime.now)

    @property
    def column_count(self) -> int:
        return len(self.columns)

    def to_dict(self) -> dict[str, Any]:
        return {
            "columns": [c.to_dict() for c in self.columns],
            "row_count": self.row_count,
            "delimiter": self.delimiter,
            "encoding": self.encoding,
            "has_header": self.has_header,
            "file_size": self.file_size,
            "detected_at": self.detected_at.isoformat(),
        }


@dataclass
class CSVFilter:
    """Filter specification for CSV data."""
    column: str
    operator: str  # eq, ne, gt, gte, lt, lte, in, not_in, contains, startswith, endswith
    value: Any
    case_sensitive: bool = False


@dataclass
class CSVSort:
    """Sort specification for CSV data."""
    column: str
    ascending: bool = True


@dataclass
class CSVGroupBy:
    """Group by specification for CSV data."""
    columns: list[str]
    aggregations: dict[str, list[AggregationFunction]]  # column -> [functions]


@dataclass
class CSVStats:
    """Statistical summary of CSV data."""
    row_count: int
    column_count: int
    memory_usage_mb: float
    null_counts: dict[str, int]
    numeric_columns: list[str]
    categorical_columns: list[str]
    date_columns: list[str]
    column_profiles: dict[str, dict[str, Any]]


class CSVEngine:
    """Enterprise CSV intelligence engine."""

    def __init__(self, max_rows_in_memory: int = 100000):
        self.max_rows_in_memory = max_rows_in_memory
        self._data: Optional[pd.DataFrame] = None
        self._schema: Optional[CSVSchema] = None
        self._file_path: Optional[Path] = None

    async def load_csv(
        self,
        source: Union[str, Path, io.StringIO, bytes],
        delimiter: Optional[str] = None,
        encoding: str = "utf-8",
        has_header: bool = True,
        sample_rows: int = 1000,
    ) -> CSVSchema:
        """Load CSV file and detect schema."""
        if isinstance(source, (str, Path)):
            self._file_path = Path(source)
            file_size = self._file_path.stat().st_size
        elif isinstance(source, bytes):
            file_size = len(source)
            self._file_path = None
        else:
            # StringIO or similar - treat as in-memory data
            file_size = 0
            self._file_path = None

        # Use pandas if available for better performance
        if PANDAS_AVAILABLE:
            return await self._load_with_pandas(
                source, delimiter, encoding, has_header, sample_rows, file_size
            )
        else:
            return await self._load_with_stdlib(
                source, delimiter, encoding, has_header, sample_rows, file_size
            )

    async def _load_with_pandas(
        self,
        source: Union[str, Path, io.StringIO, bytes],
        delimiter: Optional[str],
        encoding: str,
        has_header: bool,
        sample_rows: int,
        file_size: int,
    ) -> CSVSchema:
        """Load CSV using pandas."""
        # Convert source to a string IO for reading
        if isinstance(source, (str, Path)):
            # Read the entire file into a string
            with open(source, "r", encoding=encoding) as f:
                content = f.read()
            string_io = io.StringIO(content)
        elif isinstance(source, bytes):
            # Decode bytes to string
            string_io = io.StringIO(source.decode(encoding))
        else:
            # Assume it has a read() method (StringIO, BytesIO, or file object)
            # Save current position if possible
            pos = None
            if hasattr(source, "tell"):
                pos = source.tell()
            data = source.read()
            # Restore position if possible
            if hasattr(source, "seek") and pos is not None:
                try:
                    source.seek(pos)
                except Exception:
                    pass  # Ignore if seek fails
            if isinstance(data, bytes):
                data = data.decode(encoding)
            string_io = io.StringIO(data)

        # Detect delimiter if not provided
        if delimiter is None:
            delimiter = await self._detect_delimiter(string_io, encoding)
            # Reset after detection
            string_io.seek(0)

        # Read sample for schema detection
        sample_df = pd.read_csv(
            string_io,
            delimiter=delimiter,
            encoding=encoding,
            nrows=sample_rows,
            header=0 if has_header else None,
        )
        # Reset for reading the full data
        string_io.seek(0)

        # Read the entire data for schema
        full_df = pd.read_csv(
            string_io,
            delimiter=delimiter,
            encoding=encoding,
            header=0 if has_header else None,
        )

        self._data = full_df

        # Build column profiles
        columns = []
        for idx, col_name in enumerate(full_df.columns):
            profile = await self._profile_column(full_df[col_name], col_name, idx)
            columns.append(profile)

        schema = CSVSchema(
            columns=columns,
            row_count=len(full_df),
            delimiter=delimiter,
            encoding=encoding,
            has_header=has_header,
            file_size=file_size,
        )
        self._schema = schema
        return schema
    async def _load_with_stdlib(
        self,
        source: Union[str, Path, io.StringIO, bytes],
        delimiter: Optional[str],
        encoding: str,
        has_header: bool,
        sample_rows: int,
        file_size: int,
    ) -> CSVSchema:
        """Load CSV using standard library."""
        # Implementation for when pandas is not available
        # This is a simplified version
        rows = []
        if isinstance(source, (str, Path)):
            with open(source, 'r', encoding=encoding) as f:
                reader = csv.reader(f, delimiter=delimiter or ',')
                rows = list(reader)
        elif isinstance(source, bytes):
            text = source.decode(encoding)
            reader = csv.reader(io.StringIO(text), delimiter=delimiter or ',')
            rows = list(reader)
        else:
            reader = csv.reader(source, delimiter=delimiter or ',')
            rows = list(reader)

        if not rows:
            raise ValueError("Empty CSV file")

        headers = rows[0] if has_header else [f"col_{i}" for i in range(len(rows[0]))]
        data_rows = rows[1:] if has_header else rows

        # Profile columns
        columns = []
        for idx, col_name in enumerate(headers):
            col_data = [row[idx] if idx < len(row) else None for row in data_rows]
            profile = await self._profile_column_stdlib(col_data, col_name, idx)
            columns.append(profile)

        schema = CSVSchema(
            columns=columns,
            row_count=len(data_rows),
            delimiter=delimiter or ',',
            encoding=encoding,
            has_header=has_header,
            file_size=file_size,
        )
        self._schema = schema
        return schema

    async def _detect_delimiter(self, source: Union[str, Path, io.StringIO, bytes], encoding: str) -> str:
        """Detect CSV delimiter."""
        if isinstance(source, (str, Path)):
            with open(source, 'r', encoding=encoding) as f:
                sample = f.read(8192)
        elif isinstance(source, bytes):
            sample = source[:8192].decode(encoding)
        else:
            pos = source.tell()
            sample = source.read(8192)
            source.seek(pos)

        sniffer = csv.Sniffer()
        try:
            dialect = sniffer.sniff(sample)
            return dialect.delimiter
        except Exception:
            return ','

    async def _profile_column(self, series: pd.Series, col_name: str, idx: int) -> ColumnProfile:
        # Get the column type
        col_type = self._detect_column_type(series)
        
        # Get non-null values
        non_null = series.dropna()
        null_count = len(series) - len(non_null)
        
        # Initialize default values
        min_val = None
        max_val = None
        mean_val = None
        std_val = None
        top_values = []
        is_monotonic = False
        is_unique = False
        pattern = None
        
        if len(non_null) > 0:
            # For numeric types, compute min, max, mean, std
            if col_type in (ColumnType.INTEGER, ColumnType.FLOAT):
                try:
                    numeric_series = pd.to_numeric(non_null, errors='coerce')
                    if not numeric_series.isnull().all():
                        min_val = float(numeric_series.min())
                        max_val = float(numeric_series.max())
                        mean_val = float(numeric_series.mean())
                        std_val = float(numeric_series.std()) if len(non_null) > 1 else 0.0
                except (ValueError, TypeError):
                    pass  # Keep defaults if conversion fails
            
            # Check if all values are unique
            is_unique = len(non_null) == len(non_null.unique())
            
            # Check if the series is monotonic (increasing or decreasing)
            try:
                # Try to convert to numeric for monotonic check
                numeric_for_monotonic = pd.to_numeric(non_null, errors='coerce')
                if not numeric_for_monotonic.isnull().all():
                    diff = numeric_for_monotonic.diff().dropna()
                    if len(diff) > 0:
                        is_monotonic = (diff > 0).all() or (diff < 0).all()
            except (ValueError, TypeError):
                pass  # Keep default if conversion fails
            
            # For categorical and string types, get top values
            if col_type in (ColumnType.CATEGORICAL, ColumnType.STRING):
                # Get the top 5 most common values
                top_values = non_null.value_counts().head(5).index.tolist()
                # Convert to strings for consistency
                top_values = [str(v) for v in top_values]
        
        return ColumnProfile(
            name=col_name,
            index=idx,
            detected_type=col_type,
            sample_values=non_null.head(10).tolist() if len(non_null) > 0 else [],
            null_count=null_count,
            total_count=len(series),
            min_value=min_val,
            max_value=max_val,
            mean_value=mean_val,
            std_value=std_val,
            top_values=top_values,
            is_monotonic=is_monotonic,
            is_unique=is_unique,
            pattern=pattern
        )
    async def _profile_column_stdlib(
        self,
        values: list[Any],
        name: str,
        index: int,
    ) -> ColumnProfile:
        """Profile a column using standard library."""
        total = len(values)
        non_null = [v for v in values if v is not None and v != '']
        null_count = total - len(non_null)
        unique_count = len(set(non_null))

        # Detect type from sample
        sample = non_null[:100]
        detected_type = ColumnType.STRING
        if sample:
            # Try integer
            if all(self._is_int(v) for v in sample):
                detected_type = ColumnType.INTEGER
            # Try float
            elif all(self._is_float(v) for v in sample):
                detected_type = ColumnType.FLOAT
            # Try date
            elif all(self._is_date(v) for v in sample):
                detected_type = ColumnType.DATE

        profile = ColumnProfile(
            name=name,
            index=index,
            detected_type=detected_type,
            sample_values=sample[:10],
            null_count=null_count,
            unique_count=unique_count,
            total_count=total,
        )

        if detected_type in (ColumnType.INTEGER, ColumnType.FLOAT):
            numeric_values = [float(v) for v in non_null if self._is_float(v)]
            if numeric_values:
                profile.min_value = min(numeric_values)
                profile.max_value = max(numeric_values)
                profile.mean_value = sum(numeric_values) / len(numeric_values)

        if unique_count < total * 0.5 and unique_count < 100:
            from collections import Counter
            counts = Counter(non_null)
            profile.top_values = [(str(v), c) for v, c in counts.most_common(10)]
            profile.detected_type = ColumnType.CATEGORICAL

        profile.is_unique = unique_count == total

        return profile

    def _detect_column_type(self, series: pd.Series) -> ColumnType:
        # Drop nulls and take a sample
        non_null = series.dropna()
        if len(non_null) == 0:
            return ColumnType.STRING

        # Take up to 100 non-null values
        sample = non_null.head(100)
        # Convert to string for consistency in checking
        sample_str = [str(v) for v in sample]

        # Check for currency
        if all(self._is_currency(v) for v in sample_str):
            return ColumnType.CURRENCY
        # Check for percentage
        if all(self._is_percentage(v) for v in sample_str):
            return ColumnType.PERCENTAGE
        # Check for date
        if all(self._is_date(v) for v in sample_str):
            return ColumnType.DATE

        # Check pandas dtypes for numeric, boolean, datetime
        if series.dtype == 'bool':
            return ColumnType.BOOLEAN
        elif pd.api.types.is_integer_dtype(series):
            return ColumnType.INTEGER
        elif pd.api.types.is_float_dtype(series):
            return ColumnType.FLOAT
        elif pd.api.types.is_datetime64_any_dtype(series):
            return ColumnType.DATETIME

        # Check for categorical: if the number of unique strings is low and we have enough samples
        if len(set(sample_str)) <= 10 and len(sample_str) >= 5:
            return ColumnType.CATEGORICAL

        return ColumnType.STRING
    def _is_int(self, value: str) -> bool:
        try:
            int(value)
            return True
        except ValueError:
            return False

    def _is_float(self, value: str) -> bool:
        try:
            float(value)
            return True
        except ValueError:
            return False

    def _is_date(self, value: str) -> bool:
        date_patterns = [
            r'^\d{4}-\d{2}-\d{2}$',
            r'^\d{2}/\d{2}/\d{4}$',
            r'^\d{2}-\d{2}-\d{4}$',
            r'^\d{4}/\d{2}/\d{2}$',
        ]
        return any(re.match(p, value.strip()) for p in date_patterns)

    def _is_currency(self, value: str) -> bool:
        return bool(re.match(r'^[$£€]\s*\d{1,3}(?:,\d{3})*(?:\.\d{2})?$', value.strip()))

    def _is_percentage(self, value: str) -> bool:
        return bool(re.match(r'^\d+(?:\.\d+)?%$', value.strip()))

    async def filter(self, filters: list[CSVFilter]) -> 'CSVEngine':
        """Apply filters to the data."""
        if self._data is None:
            raise ValueError("No data loaded")

        if PANDAS_AVAILABLE:
            mask = pd.Series([True] * len(self._data), index=self._data.index)
            for f in filters:
                if f.column not in self._data.columns:
                    continue
                col = self._data[f.column]

                if f.operator == 'eq':
                    mask &= (col == f.value)
                elif f.operator == 'ne':
                    mask &= (col != f.value)
                elif f.operator == 'gt':
                    mask &= (col > f.value)
                elif f.operator == 'gte':
                    mask &= (col >= f.value)
                elif f.operator == 'lt':
                    mask &= (col < f.value)
                elif f.operator == 'lte':
                    mask &= (col <= f.value)
                elif f.operator == 'in':
                    mask &= col.isin(f.value if isinstance(f.value, list) else [f.value])
                elif f.operator == 'not_in':
                    mask &= ~col.isin(f.value if isinstance(f.value, list) else [f.value])
                elif f.operator == 'contains':
                    mask &= col.astype(str).str.contains(str(f.value), case=f.case_sensitive, na=False)
                elif f.operator == 'startswith':
                    mask &= col.astype(str).str.startswith(str(f.value), na=False)
                elif f.operator == 'endswith':
                    mask &= col.astype(str).str.endswith(str(f.value), na=False)

            self._data = self._data[mask].reset_index(drop=True)
        return self

    async def sort(self, sorts: list[CSVSort]) -> 'CSVEngine':
        """Sort the data."""
        if self._data is None:
            raise ValueError("No data loaded")

        if PANDAS_AVAILABLE:
            by = [s.column for s in sorts]
            ascending = [s.ascending for s in sorts]
            self._data = self._data.sort_values(by=by, ascending=ascending).reset_index(drop=True)
        return self

    async def group_by(self, group_by: CSVGroupBy) -> pd.DataFrame:
        """Group and aggregate data."""
        if self._data is None:
            raise ValueError("No data loaded")

        if PANDAS_AVAILABLE:
            agg_dict = {}
            for col, funcs in group_by.aggregations.items():
                if col in self._data.columns:
                    agg_dict[col] = [f.value for f in funcs]

            result = self._data.groupby(group_by.columns).agg(agg_dict)
            result.columns = ['_'.join(col).strip() for col in result.columns.values]
            return result.reset_index()

        return pd.DataFrame()

    async def select_columns(self, columns: list[str]) -> 'CSVEngine':
        """Select specific columns."""
        if self._data is None:
            raise ValueError("No data loaded")

        if PANDAS_AVAILABLE:
            available = [c for c in columns if c in self._data.columns]
            self._data = self._data[available]
        return self

    async def limit(self, n: int, offset: int = 0) -> 'CSVEngine':
        """Limit rows."""
        if self._data is None:
            raise ValueError("No data loaded")

        if PANDAS_AVAILABLE:
            self._data = self._data.iloc[offset:offset + n].reset_index(drop=True)
        return self

    async def get_stats(self) -> CSVStats:
        """Get statistical summary."""
        if self._data is None:
            raise ValueError("No data loaded")

        if PANDAS_AVAILABLE and self._schema is not None:
            # Use the schema for column type information
            null_counts = self._data.isnull().sum().to_dict()
            numeric_columns = [col.name for col in self._schema.columns if col.detected_type in (ColumnType.INTEGER, ColumnType.FLOAT)]
            categorical_columns = [col.name for col in self._schema.columns if col.detected_type in (ColumnType.STRING, ColumnType.CATEGORICAL)]
            date_columns = [col.name for col in self._schema.columns if col.detected_type in (ColumnType.DATE, ColumnType.DATETIME)]

            profiles = {}
            for col in self._data.columns:
                profile = await self._profile_column(self._data[col], col, 0)
                profiles[col] = profile.to_dict()

            return CSVStats(
                row_count=len(self._data),
                column_count=len(self._data.columns),
                memory_usage_mb=self._data.memory_usage(deep=True).sum() / (1024 * 1024),
                null_counts=null_counts,
                numeric_columns=numeric_columns,
                categorical_columns=categorical_columns,
                date_columns=date_columns,
                column_profiles=profiles,
            )

        # Fallback to the original method if pandas is not available or schema is not ready
        null_counts = self._data.isnull().sum().to_dict()
        numeric_cols = self._data.select_dtypes(include=['number']).columns.tolist()
        cat_cols = self._data.select_dtypes(include=['object', 'category']).columns.tolist()
        date_cols = self._data.select_dtypes(include=['datetime64']).columns.tolist()

        profiles = {}
        for col in self._data.columns:
            profile = await self._profile_column(self._data[col], col, 0)
            profiles[col] = profile.to_dict()

        return CSVStats(
            row_count=len(self._data),
            column_count=len(self._data.columns),
            memory_usage_mb=self._data.memory_usage(deep=True).sum() / (1024 * 1024),
            null_counts=null_counts,
            numeric_columns=numeric_cols,
            categorical_columns=cat_cols,
            date_columns=date_cols,
            column_profiles=profiles,
        )
    async def export(
        self,
        format: str = "csv",
        path: Optional[Union[str, Path]] = None,
        **kwargs,
    ) -> Union[str, bytes]:
        """Export data to various formats."""
        if self._data is None:
            raise ValueError("No data loaded")

        if PANDAS_AVAILABLE:
            if format == "csv":
                if path:
                    self._data.to_csv(path, index=False, **kwargs)
                    return str(path)
                return self._data.to_csv(index=False, **kwargs)
            elif format == "json":
                if path:
                    self._data.to_json(path, orient='records', **kwargs)
                    return str(path)
                return self._data.to_json(orient='records', **kwargs)
            elif format == "parquet":
                if not path:
                    raise ValueError("Path required for parquet")
                self._data.to_parquet(path, **kwargs)
                return str(path)
            elif format == "excel":
                if not path:
                    raise ValueError("Path required for excel")
                self._data.to_excel(path, index=False, **kwargs)
                return str(path)
            elif format == "html":
                if path:
                    self._data.to_html(path, index=False, **kwargs)
                    return str(path)
                return self._data.to_html(index=False, **kwargs)

        raise ValueError(f"Unsupported format: {format}")

    @property
    def schema(self) -> Optional[CSVSchema]:
        return self._schema

    @property
    def data(self) -> Optional[pd.DataFrame]:
        return self._data

    @property
    def row_count(self) -> int:
        return len(self._data) if self._data is not None else 0


# Convenience functions
async def load_csv(
    source: Union[str, Path, io.StringIO, bytes],
    **kwargs,
) -> CSVEngine:
    """Load CSV and return engine."""
    engine = CSVEngine()
    await engine.load_csv(source, **kwargs)
    return engine


async def csv_to_sql(
    engine: CSVEngine,
    table_name: str,
    connection_string: str,
    if_exists: str = "replace",
) -> str:
    """Export CSV engine data to SQL database."""
    if engine.data is None:
        raise ValueError("No data in engine")

    if not PANDAS_AVAILABLE:
        raise RuntimeError("pandas and sqlalchemy required for SQL export")

    df = engine.data

    # Generate CREATE TABLE statement
    columns = []
    for col in df.columns:
        dtype = df[col].dtype
        if dtype == 'int64':
            col_type = 'INTEGER'
        elif dtype == 'float64':
            col_type = 'REAL'
        else:
            col_type = 'TEXT'
        columns.append(f'"{col}" {col_type}')
    create_table = f'CREATE TABLE {table_name} ({", ".join(columns)})'

    # Generate INSERT statement
    if len(df) == 0:
        # If no data, we still return a valid INSERT statement (though it will insert nothing)
        insert_statement = f'INSERT INTO {table_name} DEFAULT VALUES;'
    else:
        rows = []
        for _, row in df.iterrows():
            values = []
            for val in row:
                if pd.isna(val):
                    values.append('NULL')
                elif isinstance(val, str):
                    # Escape single quotes by doubling them
                    val = val.replace("'", "''")
                    values.append(f"'{val}'")
                elif isinstance(val, bool):
                    values.append(str(int(val)))
                elif isinstance(val, (int, float)):
                    values.append(str(val))
                else:
                    # For datetime and other types, convert to string and escape quotes
                    val = str(val)
                    val = val.replace("'", "''")
                    values.append(f"'{val}'")
            rows.append(f"({', '.join(values)})")
        insert_values = ', '.join(rows)
        insert_statement = f'INSERT INTO {table_name} ({", ".join(df.columns)}) VALUES {insert_values};'

    return f"{create_table};\n{insert_statement}"

