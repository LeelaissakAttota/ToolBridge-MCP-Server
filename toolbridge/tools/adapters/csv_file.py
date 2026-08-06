"""Bounded local CSV analyzer with path confinement."""

import asyncio
import csv
from collections import defaultdict
from math import isfinite
from pathlib import Path

from toolbridge.tools.application.phase5_ports import CSVDataSource
from toolbridge.tools.domain.csv_analysis import (
    CSVAnalysisOutput,
    CSVColumnSummary,
    CSVColumnType,
)
from toolbridge.tools.domain.tool_errors import FileAnalysisFailedError


class LocalCSVDataSource(CSVDataSource):
    """Analyze CSV files beneath one configured root with explicit bounds."""

    def __init__(
        self,
        root_directory: Path,
        *,
        encoding: str,
        max_file_bytes: int,
        max_rows_scanned: int,
        max_columns: int,
        max_field_characters: int,
    ) -> None:
        self._root = root_directory.resolve()
        self._encoding = encoding
        self._max_file_bytes = max_file_bytes
        self._max_rows_scanned = max_rows_scanned
        self._max_columns = max_columns
        self._max_field_characters = max_field_characters

    async def analyze(
        self,
        relative_path: str,
        *,
        preview_rows: int,
    ) -> CSVAnalysisOutput:
        """Run bounded filesystem and parsing work outside the event loop."""

        return await asyncio.to_thread(self._analyze_sync, relative_path, preview_rows)

    def _analyze_sync(self, relative_path: str, preview_rows: int) -> CSVAnalysisOutput:
        path = (self._root / relative_path).resolve()
        if not path.is_relative_to(self._root) or not path.is_file():
            raise FileAnalysisFailedError("not_found")
        try:
            if path.stat().st_size > self._max_file_bytes:
                raise FileAnalysisFailedError("file_too_large")
            with path.open("r", encoding=self._encoding, newline="") as handle:
                sample = handle.read(min(self._max_file_bytes, 65_536))
                handle.seek(0)
                delimiter = _detect_delimiter(sample)
                reader = csv.DictReader(handle, delimiter=delimiter)
                columns = list(reader.fieldnames or [])
                _validate_columns(columns, self._max_columns)
                reader.fieldnames = columns
                values: dict[str, list[str]] = defaultdict(list)
                missing = dict.fromkeys(columns, 0)
                preview: list[dict[str, str | None]] = []
                scanned = 0
                truncated = False
                for row in reader:
                    if scanned >= self._max_rows_scanned:
                        truncated = True
                        break
                    if None in row or set(row) != set(columns):
                        raise FileAnalysisFailedError("invalid_shape")
                    normalized: dict[str, str | None] = {}
                    for column in columns:
                        raw = row[column]
                        if raw is not None and len(raw) > self._max_field_characters:
                            raise FileAnalysisFailedError("field_too_large")
                        value = raw.strip() if raw is not None else ""
                        if value == "":
                            missing[column] += 1
                            normalized[column] = None
                        else:
                            values[column].append(value)
                            normalized[column] = value
                    if len(preview) < preview_rows:
                        preview.append(normalized)
                    scanned += 1
        except FileAnalysisFailedError:
            raise
        except (OSError, UnicodeError, csv.Error) as error:
            raise FileAnalysisFailedError("invalid_file") from error

        summaries = [
            _summarize(column, values[column], missing[column])
            for column in columns
        ]
        return CSVAnalysisOutput(
            file_name=path.name,
            delimiter=delimiter,
            columns=columns,
            row_count=scanned,
            scanned_rows=scanned,
            truncated=truncated,
            summaries=summaries,
            preview=preview,
        )


def _detect_delimiter(sample: str) -> str:
    if not sample:
        raise FileAnalysisFailedError("empty_file")
    try:
        dialect = csv.Sniffer().sniff(sample, delimiters=",;\t|")
    except csv.Error as error:
        first_line = sample.splitlines()[0]
        if not any(delimiter in first_line for delimiter in ",;\t|"):
            return ","
        raise FileAnalysisFailedError("unknown_delimiter") from error
    return dialect.delimiter


def _validate_columns(columns: list[str], maximum: int) -> None:
    if not columns or len(columns) > maximum:
        raise FileAnalysisFailedError("invalid_columns")
    normalized = [name.strip() for name in columns]
    if any(not name or len(name) > 256 for name in normalized) or len(
        normalized
    ) != len(set(normalized)):
        raise FileAnalysisFailedError("invalid_columns")
    columns[:] = normalized


def _summarize(name: str, values: list[str], missing_count: int) -> CSVColumnSummary:
    inferred, numbers = _infer(values)
    return CSVColumnSummary(
        name=name,
        inferred_type=inferred,
        non_null_count=len(values),
        missing_count=missing_count,
        unique_count=len(set(values)),
        minimum=min(numbers) if numbers else None,
        maximum=max(numbers) if numbers else None,
        mean=sum(value / len(numbers) for value in numbers) if numbers else None,
    )


def _infer(values: list[str]) -> tuple[CSVColumnType, list[float]]:
    if not values:
        return CSVColumnType.EMPTY, []
    kinds: set[CSVColumnType] = set()
    numbers: list[float] = []
    for value in values:
        lowered = value.lower()
        if lowered in {"true", "false"}:
            kinds.add(CSVColumnType.BOOLEAN)
            continue
        try:
            integer = int(value)
        except ValueError:
            try:
                number = float(value)
            except ValueError:
                kinds.add(CSVColumnType.TEXT)
            else:
                if not isfinite(number):
                    kinds.add(CSVColumnType.TEXT)
                else:
                    kinds.add(CSVColumnType.NUMBER)
                    numbers.append(number)
        else:
            kinds.add(CSVColumnType.INTEGER)
            numbers.append(float(integer))
    if kinds <= {CSVColumnType.INTEGER}:
        return CSVColumnType.INTEGER, numbers
    if kinds <= {CSVColumnType.INTEGER, CSVColumnType.NUMBER}:
        return CSVColumnType.NUMBER, numbers
    if len(kinds) == 1:
        return next(iter(kinds)), []
    return CSVColumnType.MIXED, []
