"""Component-level tests for every Streamlit dashboard section."""

import asyncio
from typing import Any

from toolbridge.bootstrap import build_core_runtime
from toolbridge.config import Settings
from toolbridge.core.ports import NullExecutionEventLogger
from toolbridge.dashboard import app


class FakeStreamlit:
    """Small recording UI boundary used to test component composition."""

    def __init__(self) -> None:
        self.calls: list[tuple[str, object]] = []

    def __enter__(self) -> "FakeStreamlit":
        return self

    def __exit__(self, *args: object) -> None:
        del args

    def tabs(self, labels: list[str]) -> tuple["FakeStreamlit", ...]:
        self.calls.append(("tabs", labels))
        return tuple(self for _ in labels)

    def columns(self, count: int) -> tuple["FakeStreamlit", ...]:
        return tuple(self for _ in range(count))

    def selectbox(self, label: str, values: tuple[str, ...]) -> str:
        self.calls.append(("selectbox", (label, values)))
        return values[0]

    def __getattr__(self, name: str) -> Any:
        def record(*args: object, **kwargs: object) -> None:
            del kwargs
            self.calls.append((name, args[0] if args else None))

        return record


def test_dashboard_renders_all_required_sections_without_mutations(
    monkeypatch: Any,
) -> None:
    runtime = build_core_runtime(
        Settings(_env_file=None),
        NullExecutionEventLogger(),
    )

    async def prepare() -> None:
        runtime.operations.validate_startup()
        await runtime.tool_manager.initialize()
        await runtime.provider_router.initialize()
        runtime.operations.mark_ready()

    asyncio.run(prepare())
    fake = FakeStreamlit()
    monkeypatch.setattr(app, "st", fake)

    app.render_dashboard(runtime.operations.snapshot())

    subheaders = {value for name, value in fake.calls if name == "subheader"}
    assert {
        "System Overview",
        "Provider Dashboard",
        "MCP Tool Dashboard",
        "Metrics Dashboard",
        "Cost Dashboard",
        "Log Viewer",
    }.issubset(subheaders)
    assert any(name == "dataframe" for name, _ in fake.calls)
    assert any(name == "bar_chart" for name, _ in fake.calls)
