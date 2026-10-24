"""The shipped .env.example must start the app when copied verbatim to .env."""

from __future__ import annotations

from pathlib import Path

from toolbridge.config import Settings

ROOT = Path(__file__).resolve().parents[2]


def test_env_example_loads_without_validation_errors(monkeypatch) -> None:
    for key in list(__import__("os").environ):
        if key.startswith("TOOLBRIDGE_"):
            monkeypatch.delenv(key, raising=False)
    settings = Settings(_env_file=ROOT / ".env.example")
    assert settings.phase5.llm_analysis.model is None  # blank means auto
    assert str(settings.operations.dashboard_api_url).startswith("http://127.0.0.1:8000")
    assert settings.phase5.sql_query.database_path == "demo.db"
    assert settings.phase5.csv_analysis.root_directory == "data/csv"
