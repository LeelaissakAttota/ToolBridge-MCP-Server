"""Tests for the simplified CSV / SQL / LLM Playground helpers."""

from __future__ import annotations

import sqlite3
from types import SimpleNamespace

import pytest

from toolbridge.dashboard import simple_tools


def test_safe_filename_strips_unsafe_characters() -> None:
    assert simple_tools.safe_filename("../../my report (1).CSV") == "my_report_1.csv"
    assert simple_tools.safe_filename("...") == "upload.csv"


def test_save_upload_never_overwrites(tmp_path) -> None:
    first = simple_tools.save_upload(tmp_path, "data.csv", b"a,b\n1,2\n")
    same = simple_tools.save_upload(tmp_path, "data.csv", b"a,b\n1,2\n")
    other = simple_tools.save_upload(tmp_path, "data.csv", b"a,b\n3,4\n")
    assert first == same == tmp_path / "data.csv"
    assert other == tmp_path / "data_1.csv"
    assert first.read_bytes() == b"a,b\n1,2\n"


@pytest.mark.parametrize(
    ("text", "expected"),
    [
        ("```sql\nSELECT * FROM books;\n```", "SELECT * FROM books"),
        ("Here you go: select a from t; drop table t", "select a from t"),
        ("WITH x AS (SELECT 1) SELECT * FROM x", "WITH x AS (SELECT 1) SELECT * FROM x"),
    ],
)
def test_extract_sql(text, expected) -> None:
    assert simple_tools.extract_sql(text) == expected


@pytest.mark.parametrize(
    ("sql", "ok"),
    [
        ("SELECT genre, COUNT(*) FROM books GROUP BY genre", True),
        ("with t as (select 1) select * from t;", True),
        ("", False),
        ("DELETE FROM books", False),
        ("SELECT 1; DROP TABLE books", False),
    ],
)
def test_validate_select(sql, ok) -> None:
    assert (simple_tools.validate_select(sql) is None) is ok


def _settings(monkeypatch, **phase5) -> None:
    fake = SimpleNamespace(phase5=SimpleNamespace(**phase5))
    monkeypatch.setattr(simple_tools, "get_settings", lambda: fake)


def test_db_candidates_put_the_api_database_first(monkeypatch, tmp_path) -> None:
    db = tmp_path / "api.db"
    sqlite3.connect(db).close()
    _settings(
        monkeypatch,
        sql_query=SimpleNamespace(
            backend="sqlite", database_root=str(tmp_path), database_path="api.db"
        ),
    )
    candidates = simple_tools.db_candidates()
    assert candidates[0] == db
    assert simple_tools.DEMO_DB in candidates  # bundled demo DB stays available


def test_db_candidates_skip_local_files_when_backend_is_postgres(monkeypatch, tmp_path) -> None:
    db = tmp_path / "api.db"
    sqlite3.connect(db).close()
    _settings(
        monkeypatch,
        sql_query=SimpleNamespace(
            backend="postgres",
            database_root=str(tmp_path),
            database_path="api.db",
        ),
    )
    assert simple_tools.db_candidates() == []


def test_csv_roots_put_the_api_root_first(monkeypatch, tmp_path) -> None:
    _settings(monkeypatch, csv_analysis=SimpleNamespace(root_directory=str(tmp_path)))
    roots = simple_tools.csv_root_candidates()
    assert roots[0] == tmp_path
    assert simple_tools.DEMO_CSV in roots


def test_read_schema_lists_tables_and_columns(tmp_path) -> None:
    db = tmp_path / "s.db"
    con = sqlite3.connect(db)
    con.execute("CREATE TABLE books (id INTEGER PRIMARY KEY, title TEXT)")
    con.commit()
    con.close()
    schema = simple_tools.read_schema(db)
    assert "books" in schema and "title" in schema


def test_bundled_demo_database_has_library_tables() -> None:
    schema = simple_tools.read_schema(simple_tools.DEMO_DB)
    assert "books" in schema and "loans" in schema
