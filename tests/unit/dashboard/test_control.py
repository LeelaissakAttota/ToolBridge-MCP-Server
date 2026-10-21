"""Supervised-control dashboard pages and their control-API client."""

import json
from typing import Any

import httpx
import pytest

from toolbridge.dashboard import app
from toolbridge.dashboard.control_client import (
    ControlApiError,
    ControlClient,
    ControlTarget,
    decision_badge,
    load_target,
    risk_badge,
    validate_control_url,
)
from toolbridge.dashboard.control_page import (
    _parse_inputs,
    approval_feed_rows,
    render_control_page,
)

TOKEN = "z" * 32
SECRET = "sk-or-v1-supersecretvalue9876"


def _target() -> ControlTarget:
    return ControlTarget("deep_research", "http://127.0.0.1:8711", TOKEN)


def test_control_url_must_be_loopback() -> None:
    assert validate_control_url("http://127.0.0.1:8711/") == "http://127.0.0.1:8711"
    for bad in (
        "http://example.com",
        "http://u:p@127.0.0.1",
        "ftp://127.0.0.1",
        "http://127.0.0.1/?a=1",
    ):
        with pytest.raises(ValueError):
            validate_control_url(bad)


def test_target_token_from_env_and_not_in_repr() -> None:
    target = load_target("equity_research", {"TOOLBRIDGE_CONTROL_EQUITY_RESEARCH_TOKEN": TOKEN})
    assert target.configured and target.base_url == "http://127.0.0.1:8712"
    assert TOKEN not in repr(target)
    assert TOKEN not in repr(ControlClient(target))
    assert not load_target("deep_research", {}).configured


def test_client_sends_bearer_and_never_leaks_token_in_errors() -> None:
    seen: list[httpx.Request] = []

    def handler(request: httpx.Request) -> httpx.Response:
        seen.append(request)
        if request.url.path == "/control/keys/OPENROUTER_API_KEY":
            body = json.loads(request.content)
            assert body == {"value": SECRET}
            return httpx.Response(
                200, json={"name": "OPENROUTER_API_KEY", "configured": True, "masked": "****9876"}
            )
        return httpx.Response(401, json={"detail": "invalid or missing bearer token"})

    client = ControlClient(_target(), transport=httpx.MockTransport(handler), operator="leela")
    result = client.set_key("OPENROUTER_API_KEY", SECRET)
    assert result["masked"] == "****9876" and SECRET not in json.dumps(result)
    assert seen[0].headers["authorization"] == f"Bearer {TOKEN}"
    assert seen[0].headers["x-operator"] == "leela"
    with pytest.raises(ControlApiError) as info:
        client.get_settings()
    assert TOKEN not in str(info.value) and "401" in str(info.value)


def test_unreachable_api_is_sanitized() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        raise httpx.ConnectError("boom", request=request)

    client = ControlClient(_target(), transport=httpx.MockTransport(handler))
    with pytest.raises(ControlApiError, match="unreachable"):
        client.list_runs()


def test_badges_are_distinct_and_escaped() -> None:
    auto, manual, rejected = (
        decision_badge("auto"),
        decision_badge("manual"),
        decision_badge("rejected"),
    )
    assert "AUTO" in auto and "MANUAL" in manual and "REJECTED" in rejected
    assert len({auto, manual, rejected}) == 3
    assert "#2ea043" in manual and "#da3633" in rejected and "#5b8def" in auto
    assert "HIGH" in risk_badge("weird")  # unknown risk renders as HIGH
    rows = approval_feed_rows(
        [
            {
                "decision": "manual",
                "risk": "high",
                "step_index": 1,
                "step_name": "<script>",
                "by": "me",
                "at": "t",
            }
        ]
    )
    assert "<script>" not in rows[0] and "&lt;script&gt;" in rows[0]


def test_parse_inputs_returns_only_changes() -> None:
    original = {"objective": "a", "tool": None}
    assert _parse_inputs(json.dumps(original), original) is None
    assert _parse_inputs(json.dumps({"objective": "b", "tool": None}), original) == {
        "objective": "b"
    }
    assert _parse_inputs("not json", original) is None


class FakeUI:
    def __init__(
        self, toggles: dict[str, bool] | None = None, clicks: set[str] | None = None
    ) -> None:
        self.calls: list[tuple[str, Any]] = []
        self.session_state: dict[str, Any] = {}
        self._toggles = toggles or {}
        self._clicks = clicks or set()

    def __enter__(self) -> "FakeUI":
        return self

    def __exit__(self, *args: object) -> None:
        return None

    def columns(self, spec: Any, **kwargs: Any) -> tuple["FakeUI", ...]:
        return tuple(self for _ in range(spec if isinstance(spec, int) else len(spec)))

    def toggle(self, label: str, value: bool = False, key: str = "", **kwargs: Any) -> bool:
        return self._toggles.get(key, value)

    def button(self, label: str, key: str = "", **kwargs: Any) -> bool:
        self.calls.append(("button", key))
        return key in self._clicks

    def form_submit_button(self, label: str) -> bool:
        return False

    def selectbox(self, label: str, options: Any) -> Any:
        return list(options)[0]

    def text_area(self, label: str, value: str = "", key: str = "") -> str:
        return value

    def __getattr__(self, name: str) -> Any:
        def record(*args: Any, **kwargs: Any) -> Any:
            self.calls.append((name, args[0] if args else None))
            if name in {"expander", "container", "form"}:
                return self
            return None

        return record


class FakeClient:
    def __init__(self) -> None:
        self.actions: list[tuple[str, Any]] = []
        self.step = {
            "step_id": "s1",
            "index": 0,
            "kind": "planning",
            "name": "planning (iteration 0)",
            "inputs": {"iteration": 0},
            "risk": "low",
            "state": "pending_approval",
            "decision": None,
            "decided_by": None,
            "overridden": False,
            "attempts": 0,
            "error": None,
        }

    def get_settings(self) -> dict[str, bool]:
        return {"approval_mode": False, "auto_approve_low_risk": False}

    def update_settings(self, **kw: Any) -> dict[str, bool]:
        self.actions.append(("settings", kw))
        return {"approval_mode": True, "auto_approve_low_risk": True}

    def list_runs(self) -> list[dict[str, Any]]:
        return [{"run_id": "r1", "status": "waiting_approval", "created_at": "now"}]

    def get_run(self, run_id: str) -> dict[str, Any]:
        return {
            "run_id": run_id,
            "status": "waiting_approval",
            "step_count": 1,
            "pending_approvals": ["s1"],
            "approval_mode": True,
            "error": None,
            "steps": [self.step],
        }

    def lifecycle(self, run_id: str, action: str) -> dict[str, Any]:
        self.actions.append((action, run_id))
        return {}

    def approve(self, run_id: str, step_id: str, **kw: Any) -> dict[str, Any]:
        self.actions.append(("approve", step_id))
        return {}

    def reject(self, run_id: str, step_id: str, **kw: Any) -> dict[str, Any]:
        self.actions.append(("reject", step_id))
        return {}

    def logs(self, run_id: str, after: int = 0) -> dict[str, Any]:
        return {"logs": [{"at": "t", "level": "error", "message": "boom"}]}

    def approvals(self, run_id: str | None = None, limit: int = 50) -> list[dict[str, Any]]:
        return [
            {
                "decision": "auto",
                "risk": "low",
                "step_index": 0,
                "step_name": "x",
                "by": "policy",
                "at": "t",
            }
        ]

    def keys(self) -> dict[str, Any]:
        return {"keys": {"OPENROUTER_API_KEY": {"configured": True, "masked": "****9876"}}}


def test_page_renders_controls_and_dispatches_actions() -> None:
    client = FakeClient()
    ui = FakeUI(
        toggles={
            "deep_research_approval_mode": True,
            "deep_research_auto_low": True,
            "deep_research_live": False,
        },
        clicks={"deep_research_ok_s1", "deep_research_stop"},
    )
    render_control_page(ui, "deep_research", client)  # type: ignore[arg-type]
    assert ("settings", {"approval_mode": True, "auto_approve_low_risk": True}) in client.actions
    assert ("approve", "s1") in client.actions and ("stop", "r1") in client.actions
    subheaders = [v for n, v in ui.calls if n == "subheader"]
    for section in (
        "Approval policy",
        "Runs",
        "Awaiting your approval",
        "Steps",
        "Live logs",
        "Approval feed",
        "API keys",
    ):
        assert section in subheaders
    rendered = json.dumps([str(v) for _, v in ui.calls])
    assert SECRET not in rendered


def test_unconfigured_page_shows_setup_hint(monkeypatch: Any) -> None:
    monkeypatch.delenv("TOOLBRIDGE_CONTROL_DEEP_RESEARCH_TOKEN", raising=False)
    ui = FakeUI()
    render_control_page(ui, "deep_research")
    assert any(
        n == "info" and "TOOLBRIDGE_CONTROL_DEEP_RESEARCH_TOKEN" in str(v) for n, v in ui.calls
    )


def test_navigation_includes_control_pages() -> None:
    pages = set(app.PageName.__args__)
    assert {"Deep Research Control", "Equity Research Control"} <= pages
