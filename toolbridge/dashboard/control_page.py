"""Supervised-control pages for Deep Research and Equity Research.

The page talks only to the project's local control API (bearer token from the
environment). It never displays, logs, or stores API key values: keys are shown
masked by the API and new values are sent write-only from a password field.
"""

from __future__ import annotations

import json
from html import escape
from typing import Any

from toolbridge.dashboard.control_client import (
    PROJECTS,
    ControlApiError,
    ControlClient,
    ProjectId,
    decision_badge,
    load_target,
    risk_badge,
)

_TERMINAL = {"completed", "failed", "stopped"}
_STATUS_ICONS = {
    "running": "\U0001f7e2",
    "waiting_approval": "\U0001f7e1",
    "paused": "\u23f8",
    "stopping": "\U0001f7e0",
    "stopped": "\u23f9",
    "completed": "\u2705",
    "failed": "\u274c",
    "queued": "\u23f3",
}
_EQUITY_OBJECTIVES = (
    "company_overview",
    "market_analysis",
    "financial_analysis",
    "news_and_events",
    "industry_analysis",
    "regulatory_analysis",
    "comprehensive_equity_research",
)


def _parse_inputs(text: str | None, original: dict[str, Any]) -> dict[str, Any] | None:
    """Return only changed keys from an edited JSON object (None if unchanged/invalid)."""
    if not text:
        return None
    try:
        edited = json.loads(text)
    except ValueError:
        return None
    if not isinstance(edited, dict):
        return None
    changed = {k: v for k, v in edited.items() if original.get(k) != v}
    return changed or None


def approval_feed_rows(entries: list[dict[str, Any]]) -> list[str]:
    """HTML rows (escaped) for the live approval feed."""
    rows = []
    for entry in entries:
        rows.append(
            f"{decision_badge(str(entry.get('decision')))} {risk_badge(str(entry.get('risk')))} "
            f"<b>#{escape(str(entry.get('step_index')))}</b> "
            f"{escape(str(entry.get('step_name', ''))[:120])} "
            f"<span style='color:#8b949e'>by {escape(str(entry.get('by')))} "
            f"at {escape(str(entry.get('at')))}"
            f"{' (inputs overridden)' if entry.get('overridden') else ''}</span>"
        )
    return rows


def render_control_page(ui: Any, project: ProjectId, client: ControlClient | None = None) -> None:
    meta = PROJECTS[project]
    ui.title(f"{meta['title']} Control")
    ui.caption(
        "Supervised control: approve each agent step before it runs, pause/stop runs, "
        "override and re-run steps, and rotate API keys (masked, write-only)."
    )
    if client is None:
        try:
            target = load_target(project)
        except ValueError as error:
            ui.error(str(error))
            return
        if not target.configured:
            ui.info(
                f"Set {meta['token_env']} (and optionally {meta['url_env']}, default "
                f"{meta['default_url']}) and start the project's control API to enable this page."
            )
            return
        client = ControlClient(target)
    try:
        _render_body(ui, project, client)
    except ControlApiError as error:
        ui.error(str(error))


def _render_body(ui: Any, project: ProjectId, client: ControlClient) -> None:
    _render_settings(ui, project, client)
    run_id = _render_runs(ui, project, client)
    if run_id:
        refresh = ui.toggle("Live refresh (2s)", value=True, key=f"{project}_live")
        fragment = getattr(ui, "fragment", None)
        if refresh and callable(fragment):
            fragment(run_every=2.0)(lambda: _render_run(ui, project, client, run_id))()
        else:
            _render_run(ui, project, client, run_id)
    _render_feed(ui, project, client, run_id)
    _render_keys(ui, project, client)


def _render_settings(ui: Any, project: ProjectId, client: ControlClient) -> None:
    ui.subheader("Approval policy")
    current = client.get_settings()
    cols = ui.columns(2)
    approval = cols[0].toggle(
        "Approval mode (gate every step)",
        value=current["approval_mode"],
        key=f"{project}_approval_mode",
    )
    auto = cols[1].toggle(
        "Auto-approve low-risk steps",
        value=current["auto_approve_low_risk"],
        key=f"{project}_auto_low",
        help="LOW = data fetching, analysis, formatting, report rendering. "
        "HIGH-risk and unknown steps always wait for a human.",
    )
    if isinstance(approval, bool) and isinstance(auto, bool):
        if (approval, auto) != (current["approval_mode"], current["auto_approve_low_risk"]):
            client.update_settings(approval_mode=approval, auto_approve_low_risk=auto)
            ui.toast("Policy saved")
    ui.caption("Settings are persisted by the project and apply to new runs.")


def _start_params(ui: Any, project: ProjectId) -> dict[str, Any] | None:
    if project == "deep_research":
        objective = ui.text_input("Research objective", key="dr_objective")
        mode = ui.selectbox("Mode", ("offline", "live"))
        if objective:
            return {"objective": str(objective), "mode": mode}
        return None
    q = ui.text_input("Company name or query", key="er_q")
    ticker = ui.text_input("Ticker (optional)", key="er_ticker")
    country = ui.text_input("Country (US / IN, optional)", key="er_country")
    objective = ui.selectbox("Objective", _EQUITY_OBJECTIVES)
    if q or ticker:
        params: dict[str, Any] = {"q": str(q or ""), "objective": objective}
        if ticker:
            params["ticker"] = str(ticker).upper()
        if country:
            params["country"] = str(country).upper()
        return params
    return None


def _render_runs(ui: Any, project: ProjectId, client: ControlClient) -> str | None:
    ui.subheader("Runs")
    with ui.expander("Start a new run", expanded=False):
        params = _start_params(ui, project)
        if ui.button("Start run", key=f"{project}_start", disabled=params is None) and params:
            run = client.start_run(params)
            ui.session_state[f"{project}_run"] = run["run_id"]
            ui.toast(f"Run {run['run_id']} started")
    runs = client.list_runs()
    if not runs:
        ui.info("No runs yet.")
        return None
    labels = [
        f"{_STATUS_ICONS.get(r['status'], '')} {r['run_id']} · {r['status']} · {r['created_at']}"
        for r in runs
    ]
    chosen = ui.selectbox("Run", labels)
    index = labels.index(chosen) if chosen in labels else 0
    return str(runs[index]["run_id"])


def _render_run(ui: Any, project: ProjectId, client: ControlClient, run_id: str) -> None:
    run = client.get_run(run_id)
    status = run["status"]
    cols = ui.columns(4)
    cols[0].metric("Status", f"{_STATUS_ICONS.get(status, '')} {status}")
    cols[1].metric("Steps", run["step_count"])
    cols[2].metric("Pending approvals", len(run["pending_approvals"]))
    cols[3].metric("Approval mode", "ON" if run["approval_mode"] else "OFF")
    if run.get("error"):
        ui.error(f"Run error: {run['error']}")

    actions = ui.columns(3)
    finished = status in _TERMINAL
    if actions[0].button("Pause", key=f"{project}_pause", disabled=finished or status == "paused"):
        client.lifecycle(run_id, "pause")
    if actions[1].button("Resume", key=f"{project}_resume", disabled=status != "paused"):
        client.lifecycle(run_id, "resume")
    if actions[2].button("Stop", key=f"{project}_stop", disabled=finished, type="primary"):
        client.lifecycle(run_id, "stop")

    steps: list[dict[str, Any]] = run.get("steps", [])
    pending = [s for s in steps if s["state"] == "pending_approval"]
    if pending:
        ui.subheader("Awaiting your approval")
    for step in pending:
        with ui.container(border=True):
            ui.markdown(
                f"{risk_badge(step['risk'])} <b>Step {step['index']}</b> "
                f"{escape(step['name'])} <code>{escape(step['kind'])}</code>",
                unsafe_allow_html=True,
            )
            edited = ui.text_area(
                "Step inputs (edit to override)",
                value=json.dumps(step["inputs"], indent=2),
                key=f"{project}_inputs_{step['step_id']}",
            )
            note = ui.text_input("Note", key=f"{project}_note_{step['step_id']}")
            buttons = ui.columns(2)
            if buttons[0].button("Approve", key=f"{project}_ok_{step['step_id']}", type="primary"):
                client.approve(
                    run_id,
                    step["step_id"],
                    note=note or None,
                    inputs=_parse_inputs(edited, step["inputs"]),
                )
            if buttons[1].button("Reject", key=f"{project}_no_{step['step_id']}"):
                client.reject(run_id, step["step_id"], note=note or None)

    ui.subheader("Steps")
    if steps:
        ui.dataframe(
            [
                {
                    "#": s["index"],
                    "Step": s["name"],
                    "Kind": s["kind"],
                    "Risk": s["risk"].upper(),
                    "State": s["state"],
                    "Decision": (s["decision"] or "pending").upper(),
                    "By": s["decided_by"] or "-",
                    "Overridden": s["overridden"],
                    "Attempts": s["attempts"],
                    "Error": s["error"] or "",
                }
                for s in steps
            ],
            hide_index=True,
        )
        _render_retry(ui, project, client, run_id, steps)
    else:
        ui.info("No steps yet.")

    ui.subheader("Live logs")
    logs = client.logs(run_id)["logs"][-200:]
    errors = [x for x in logs if x["level"] == "error"]
    if errors:
        ui.error(f"{len(errors)} error(s): {errors[-1]['message'][:300]}")
    ui.code("\n".join(f"{x['at']} {x['level'].upper():7} {x['message']}" for x in logs) or "-")


def _render_retry(
    ui: Any, project: ProjectId, client: ControlClient, run_id: str, steps: list[dict[str, Any]]
) -> None:
    finished = [s for s in steps if s["state"] in ("succeeded", "failed", "rejected", "skipped")]
    if not finished:
        return
    with ui.expander("Override & re-run a step", expanded=False):
        labels = [f"#{s['index']} {s['name']} ({s['state']})" for s in finished]
        chosen = ui.selectbox("Step to re-run", labels)
        step = finished[labels.index(chosen) if chosen in labels else 0]
        edited = ui.text_area(
            "Inputs for re-run",
            value=json.dumps(step["inputs"], indent=2),
            key=f"{project}_retry_inputs",
        )
        if ui.button("Re-run step", key=f"{project}_retry"):
            result = client.retry(
                run_id, step["step_id"], inputs=_parse_inputs(edited, step["inputs"])
            )
            ui.toast(f"Re-run finished: {result['state']}")


def _render_feed(ui: Any, project: ProjectId, client: ControlClient, run_id: str | None) -> None:
    ui.subheader("Approval feed")
    ui.markdown(
        f"{decision_badge('auto')} auto-approved low-risk &nbsp; {decision_badge('manual')} "
        f"approved by a human &nbsp; {decision_badge('rejected')} rejected",
        unsafe_allow_html=True,
    )
    entries = client.approvals(run_id=run_id, limit=50)
    if not entries:
        ui.info("No approval decisions recorded yet.")
        return
    ui.markdown("<br>".join(approval_feed_rows(entries)), unsafe_allow_html=True)


def _render_keys(ui: Any, project: ProjectId, client: ControlClient) -> None:
    ui.subheader("API keys")
    data = client.keys()
    keys: dict[str, dict[str, Any]] = data.get("keys", {})
    ui.dataframe(
        [
            {"Key": name, "Configured": info["configured"], "Value": info["masked"] or "-"}
            for name, info in keys.items()
        ],
        hide_index=True,
    )
    ui.caption("Values are masked by the control API; full keys are never sent to the dashboard.")
    if not keys:
        return
    with ui.form(f"{project}_key_form", clear_on_submit=True):
        name = ui.selectbox("Key to set / rotate", tuple(keys))
        value = ui.text_input("New value (leave empty to clear)", type="password")
        if ui.form_submit_button("Save key"):
            result = client.set_key(str(name), str(value or ""))
            ui.success(f"{result['name']} saved ({result['masked'] or 'cleared'})")
