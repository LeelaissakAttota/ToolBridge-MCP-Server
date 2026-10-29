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


def _ready_snapshot() -> object:
    runtime = build_core_runtime(Settings(_env_file=None), NullExecutionEventLogger())

    async def prepare() -> None:
        runtime.operations.validate_startup()
        await runtime.tool_manager.initialize()
        await runtime.provider_router.initialize()
        runtime.operations.mark_ready()

    asyncio.run(prepare())
    return runtime.operations.snapshot()


def test_navigation_has_no_placeholder_pages() -> None:
    pages = set(app.PageName.__args__)

    assert {"Chat", "Agent"}.isdisjoint(pages)
    assert "History" in pages
    assert not hasattr(app, "_render_placeholder")


class ContainerFakeStreamlit(FakeStreamlit):
    """Fake that also supports container-style elements used by page renderers."""

    def columns(self, spec: object, **kwargs: object) -> tuple["FakeStreamlit", ...]:
        del kwargs
        count = len(spec) if isinstance(spec, (list, tuple)) else int(spec)
        return tuple(self for _ in range(count))

    def radio(self, label: str, options: Any, **kwargs: object) -> Any:
        del kwargs
        return list(options)[0]

    def button(self, *args: object, **kwargs: object) -> bool:
        del args, kwargs
        return False

    def toggle(self, *args: object, **kwargs: object) -> bool:
        del args, kwargs
        return False

    def __getattr__(self, name: str) -> Any:
        if name in {"container", "expander", "popover", "form", "empty", "status"}:

            def container(*args: object, **kwargs: object) -> "ContainerFakeStreamlit":
                del kwargs
                self.calls.append((name, args[0] if args else None))
                return self

            return container
        return super().__getattr__(name)


def test_every_navigation_page_renders_real_content(monkeypatch: Any) -> None:
    snapshot = _ready_snapshot()
    for page in app.PageName.__args__:
        fake = ContainerFakeStreamlit()
        monkeypatch.setattr(app, "st", fake)
        app._render_page(page, snapshot)
        rendered = " ".join(str(value) for _, value in fake.calls)
        assert "Not Implemented" not in rendered
        assert "CrewAI" not in rendered
        assert not any(name == "warning" for name, _ in fake.calls), page


def test_history_page_shows_usage_and_empty_states(monkeypatch: Any) -> None:
    fake = FakeStreamlit()
    monkeypatch.setattr(app, "st", fake)

    app._render_history(_ready_snapshot())

    subheaders = [value for name, value in fake.calls if name == "subheader"]
    assert subheaders == ["Tool Usage", "Model Routing", "Recent Events"]
    assert any(name == "metric" for name, _ in fake.calls)


def test_dashboard_html_fragments_escape_snapshot_text() -> None:
    from toolbridge.operations.domain.models import ProviderMonitor, ToolMonitor

    payload = "<img src=x onerror=alert(1)>"
    provider = ProviderMonitor(
        provider=payload,
        configured=True,
        priority=1,
        status="healthy",
        active=True,
        failover_active=False,
        requests=0,
        total_tokens=0,
        estimated_cost_usd=0.0,
    )
    tool = ToolMonitor(
        tool_name="evil",
        display_name=payload,
        registered=True,
        health="healthy",
        execution_count=0,
        average_response_time_ms=0.0,
    )

    for fragment in (app._provider_item_html(provider), app._tool_item_html(tool)):
        assert "<img" not in fragment.lower()
        assert "&lt;img" in fragment.lower()


def test_dashboard_source_avoids_removed_streamlit_arguments() -> None:
    from pathlib import Path

    source = Path(app.__file__).read_text(encoding="utf-8")

    assert "use_container_width" not in source
