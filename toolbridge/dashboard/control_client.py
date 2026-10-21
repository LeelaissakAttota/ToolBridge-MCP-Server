"""Authenticated client for the Deep Research / Equity Research control APIs.

Security properties:
- base URLs must be loopback http(s) without credentials or query strings;
- the bearer token is sent only in the Authorization header, never logged,
  and never included in ``repr`` or error messages;
- API keys are only ever sent (write-only ``set_key``); the control APIs return
  masked values (last 4 characters) and this client never caches them.
"""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from typing import Any, Literal
from urllib.parse import urlsplit

import httpx

ProjectId = Literal["deep_research", "equity_research"]

PROJECTS: dict[ProjectId, dict[str, str]] = {
    "deep_research": {
        "title": "Deep Research",
        "url_env": "TOOLBRIDGE_CONTROL_DEEP_RESEARCH_URL",
        "token_env": "TOOLBRIDGE_CONTROL_DEEP_RESEARCH_TOKEN",
        "default_url": "http://127.0.0.1:8711",
    },
    "equity_research": {
        "title": "Equity Research",
        "url_env": "TOOLBRIDGE_CONTROL_EQUITY_RESEARCH_URL",
        "token_env": "TOOLBRIDGE_CONTROL_EQUITY_RESEARCH_TOKEN",
        "default_url": "http://127.0.0.1:8712",
    },
}

_LOOPBACK = {"127.0.0.1", "localhost", "::1"}


class ControlApiError(RuntimeError):
    """Sanitized control-API failure (never contains the token or key values)."""


def validate_control_url(url: str) -> str:
    parts = urlsplit(url.strip())
    if parts.scheme not in {"http", "https"} or not parts.hostname:
        raise ValueError("control API URL must be http(s)")
    if parts.hostname not in _LOOPBACK:
        raise ValueError("control API URL must use a loopback host")
    if parts.username or parts.password or parts.query or parts.fragment:
        raise ValueError("control API URL must not include credentials or query data")
    return url.strip().rstrip("/")


@dataclass(frozen=True)
class ControlTarget:
    project: ProjectId
    base_url: str
    token: str = field(repr=False)

    @property
    def configured(self) -> bool:
        return len(self.token) >= 16


def load_target(project: ProjectId, env: dict[str, str] | None = None) -> ControlTarget:
    source = os.environ if env is None else env
    meta = PROJECTS[project]
    url = validate_control_url(source.get(meta["url_env"]) or meta["default_url"])
    return ControlTarget(project, url, source.get(meta["token_env"], ""))


class ControlClient:
    def __init__(
        self,
        target: ControlTarget,
        *,
        timeout_seconds: float = 5.0,
        transport: httpx.BaseTransport | None = None,
        operator: str = "dashboard",
    ) -> None:
        self._target = target
        self._timeout = timeout_seconds
        self._transport = transport
        self._operator = operator

    def __repr__(self) -> str:
        return f"ControlClient(project={self._target.project!r}, url={self._target.base_url!r})"

    def _request(self, method: str, path: str, **kwargs: Any) -> Any:
        headers = {
            "Authorization": f"Bearer {self._target.token}",
            "X-Operator": self._operator,
        }
        try:
            with httpx.Client(
                timeout=self._timeout, follow_redirects=False, transport=self._transport
            ) as client:
                response = client.request(
                    method, f"{self._target.base_url}{path}", headers=headers, **kwargs
                )
        except httpx.HTTPError as error:
            raise ControlApiError(
                f"{PROJECTS[self._target.project]['title']} control API unreachable"
            ) from error
        if response.status_code >= 400:
            detail = ""
            try:
                body = response.json()
                detail = str(body.get("detail", ""))[:200] if isinstance(body, dict) else ""
            except ValueError:
                pass
            raise ControlApiError(f"control API returned {response.status_code} {detail}".strip())
        return response.json()

    # settings
    def get_settings(self) -> dict[str, bool]:
        return dict(self._request("GET", "/control/settings"))

    def update_settings(
        self, *, approval_mode: bool | None = None, auto_approve_low_risk: bool | None = None
    ) -> dict[str, bool]:
        body = {"approval_mode": approval_mode, "auto_approve_low_risk": auto_approve_low_risk}
        return dict(self._request("PUT", "/control/settings", json=body))

    # runs
    def start_run(self, params: dict[str, Any]) -> dict[str, Any]:
        return dict(self._request("POST", "/control/runs", json={"params": params}))

    def list_runs(self) -> list[dict[str, Any]]:
        return list(self._request("GET", "/control/runs"))

    def get_run(self, run_id: str) -> dict[str, Any]:
        return dict(self._request("GET", f"/control/runs/{run_id}"))

    def lifecycle(self, run_id: str, action: Literal["pause", "resume", "stop"]) -> dict[str, Any]:
        return dict(self._request("POST", f"/control/runs/{run_id}/{action}"))

    def approve(
        self,
        run_id: str,
        step_id: str,
        *,
        note: str | None = None,
        inputs: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        body = {"note": note, "inputs": inputs}
        return dict(
            self._request("POST", f"/control/runs/{run_id}/steps/{step_id}/approve", json=body)
        )

    def reject(self, run_id: str, step_id: str, *, note: str | None = None) -> dict[str, Any]:
        return dict(
            self._request(
                "POST", f"/control/runs/{run_id}/steps/{step_id}/reject", json={"note": note}
            )
        )

    def retry(
        self, run_id: str, step_id: str, *, inputs: dict[str, Any] | None = None
    ) -> dict[str, Any]:
        return dict(
            self._request(
                "POST",
                f"/control/runs/{run_id}/steps/{step_id}/retry",
                json={"inputs": inputs},
                timeout=120.0,
            )
        )

    def logs(self, run_id: str, after: int = 0) -> dict[str, Any]:
        return dict(self._request("GET", f"/control/runs/{run_id}/logs", params={"after": after}))

    def approvals(self, run_id: str | None = None, limit: int = 100) -> list[dict[str, Any]]:
        params: dict[str, Any] = {"limit": limit}
        if run_id:
            params["run_id"] = run_id
        return list(self._request("GET", "/control/approvals", params=params))

    # keys (masked read, write-only update)
    def keys(self) -> dict[str, Any]:
        return dict(self._request("GET", "/control/keys"))

    def set_key(self, name: str, value: str) -> dict[str, Any]:
        return dict(self._request("PUT", f"/control/keys/{name}", json={"value": value}))


# --- presentation helpers (pure, testable) -------------------------------------------

DECISION_BADGES: dict[str, tuple[str, str, str]] = {
    # decision: (label, css colour, icon)
    "auto": ("AUTO", "#5b8def", "\U0001f916"),
    "manual": ("MANUAL", "#2ea043", "\u2705"),
    "rejected": ("REJECTED", "#da3633", "\u26d4"),
    "stopped": ("STOPPED", "#8b949e", "\u23f9"),
    "not_required": ("NO GATE", "#6e7681", "\u2796"),
}
RISK_BADGES: dict[str, tuple[str, str]] = {
    "low": ("LOW", "#3fb950"),
    "high": ("HIGH", "#f85149"),
}


def badge_html(label: str, colour: str, icon: str = "") -> str:
    from html import escape

    text = f"{icon} {label}".strip()
    return (
        f"<span style='background:{escape(colour)};color:#fff;border-radius:4px;"
        f"padding:1px 6px;font-size:0.75rem;font-weight:700'>{escape(text)}</span>"
    )


def decision_badge(decision: str | None) -> str:
    label, colour, icon = DECISION_BADGES.get(decision or "", ("PENDING", "#d29922", "\u23f3"))
    return badge_html(label, colour, icon)


def risk_badge(risk: str | None) -> str:
    label, colour = RISK_BADGES.get(risk or "", ("HIGH", "#f85149"))
    return badge_html(label, colour)
