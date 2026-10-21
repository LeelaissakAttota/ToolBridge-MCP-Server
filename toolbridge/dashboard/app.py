"""Streamlit dashboard: read-only ToolBridge monitoring."""

from datetime import datetime
from html import escape
from typing import Literal
from urllib.parse import urlsplit

import streamlit as st

from toolbridge.config import Settings, get_settings
from toolbridge.dashboard.client import DashboardClient, DashboardUnavailableError
from toolbridge.dashboard.playground import render_playground
from toolbridge.dashboard.setup_wizard import render_provider_setup
from toolbridge.operations.domain.models import (
    OperationsSnapshot,
    ProviderMonitor,
    SafeLogEntry,
    ToolMonitor,
)

PageName = Literal[
    "Overview",
    "Tools",
    "Tool Playground",
    "Providers",
    "History",
    "Logs",
    "Settings",
    "System Health",
    "Costs",
]


# ─── Visual Design System ──────────────────────────────────────────────
def _inject_custom_css() -> None:
    """Inject custom CSS to match reference dark-theme three-column layout."""
    st.markdown(
        """
<style>
/* ── Design Tokens ────────────────────────────────────────────── */
:root {
  --bg-primary: #0e1117;
  --bg-secondary: #161b22;
  --bg-tertiary: #21262d;
  --border-color: #30363d;
  --text-primary: #f0f6fc;
  --text-secondary: #8b949e;
  --text-muted: #6e7681;
  --accent-blue: #58a6ff;
  --accent-green: #3fb950;
  --accent-red: #f85149;
  --accent-yellow: #d29922;
  --sidebar-width: 260px;
  --header-height: 56px;
  --card-radius: 8px;
  --card-shadow: 0 1px 3px rgba(0,0,0,0.3), 0 1px 2px rgba(0,0,0,0.2);
}

/* ── Global Overrides ────────────────────────────────────────── */
.stApp {
  background-color: var(--bg-primary) !important;
  color: var(--text-primary) !important;
}

/* Hide Streamlit default chrome */
#MainMenu { visibility: hidden; }
header[data-testid="stHeader"] { display: none; }
footer { display: none; }
.stDeployButton { display: none; }

/* ── Sidebar (Left Navigation) ───────────────────────────────── */
section[data-testid="stSidebar"] {
  background-color: var(--bg-secondary) !important;
  border-right: 1px solid var(--border-color) !important;
  width: var(--sidebar-width) !important;
  min-width: var(--sidebar-width) !important;
  max-width: var(--sidebar-width) !important;
  padding-top: 1rem !important;
}

section[data-testid="stSidebar"] .stMarkdown,
section[data-testid="stSidebar"] .stCaption,
section[data-testid="stSidebar"] label,
section[data-testid="stSidebar"] .stRadio label {
  color: var(--text-primary) !important;
}

section[data-testid="stSidebar"] .stButton > button {
  background-color: var(--bg-tertiary) !important;
  border: 1px solid var(--border-color) !important;
  color: var(--text-primary) !important;
  border-radius: var(--card-radius) !important;
  width: 100% !important;
  justify-content: flex-start !important;
  padding: 0.5rem 0.75rem !important;
  font-weight: 500 !important;
}

section[data-testid="stSidebar"] .stButton > button:hover {
  background-color: var(--accent-blue) !important;
  border-color: var(--accent-blue) !important;
  color: var(--bg-primary) !important;
}

/* Navigation radio buttons */
section[data-testid="stSidebar"] .stRadio > div {
  flex-direction: column !important;
  gap: 0.25rem !important;
}

section[data-testid="stSidebar"] .stRadio label {
  background-color: transparent !important;
  border: none !important;
  padding: 0.5rem 0.75rem !important;
  border-radius: var(--card-radius) !important;
  color: var(--text-secondary) !important;
  font-weight: 500 !important;
  transition: all 0.15s ease !important;
  cursor: pointer !important;
}

section[data-testid="stSidebar"] .stRadio label:hover {
  background-color: var(--bg-tertiary) !important;
  color: var(--text-primary) !important;
}

section[data-testid="stSidebar"] .stRadio input:checked + div label,
section[data-testid="stSidebar"] .stRadio label[data-selected="true"] {
  background-color: var(--accent-blue) !important;
  color: var(--bg-primary) !important;
  font-weight: 600 !important;
}

/* ── Main Content Area ───────────────────────────────────────── */
.main .block-container {
  padding: 1.5rem 2rem !important;
  max-width: 100% !important;
  background-color: var(--bg-primary) !important;
}

/* ── Cards ───────────────────────────────────────────────────── */
.stContainer[data-testid="stContainer"] > div[style*="border"] {
  background-color: var(--bg-secondary) !important;
  border: 1px solid var(--border-color) !important;
  border-radius: var(--card-radius) !important;
  box-shadow: var(--card-shadow) !important;
}

div[data-testid="stMetric"] {
  background-color: var(--bg-secondary) !important;
  border: 1px solid var(--border-color) !important;
  border-radius: var(--card-radius) !important;
  padding: 1rem !important;
  box-shadow: var(--card-shadow) !important;
}

div[data-testid="stMetric"] label {
  color: var(--text-secondary) !important;
  font-size: 0.75rem !important;
  font-weight: 600 !important;
  text-transform: uppercase !important;
  letter-spacing: 0.05em !important;
}

div[data-testid="stMetric"] div[data-testid="stMetricValue"] {
  color: var(--text-primary) !important;
  font-size: 1.5rem !important;
  font-weight: 700 !important;
}

/* ── Tables ──────────────────────────────────────────────────── */
/* st.dataframe renders on a canvas (glide-data-grid); colours come from these vars */
div[data-testid="stDataFrame"], .stDataFrame {
  background-color: var(--bg-secondary) !important;
  border: 1px solid var(--border-color) !important;
  border-radius: var(--card-radius) !important;
  --gdg-bg-cell: #161b22;
  --gdg-bg-cell-medium: #1c2128;
  --gdg-bg-header: #21262d;
  --gdg-bg-header-has-focus: #30363d;
  --gdg-bg-header-hovered: #30363d;
  --gdg-bg-bubble: #21262d;
  --gdg-text-dark: #f0f6fc;
  --gdg-text-medium: #c9d1d9;
  --gdg-text-light: #8b949e;
  --gdg-text-header: #c9d1d9;
  --gdg-text-group-header: #c9d1d9;
  --gdg-border-color: #30363d;
  --gdg-horizontal-border-color: #30363d;
  --gdg-accent-color: #58a6ff;
  --gdg-accent-light: rgba(88,166,255,0.15);
}
div[data-testid="stTable"] table, .stTable table {
  background-color: var(--bg-secondary) !important;
  color: var(--text-primary) !important;
}
div[data-testid="stTable"] th, div[data-testid="stTable"] td {
  color: var(--text-primary) !important;
  border-color: var(--border-color) !important;
}

/* ── Status cards row (provider / tool status) ───────────────── */
.status-row {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(170px, 1fr));
  gap: 1rem;
  margin: 0 0 1rem 0;
}
.status-row.compact { grid-template-columns: repeat(auto-fit, minmax(140px, 1fr)); gap: 0.6rem; }
.status-card {
  background-color: var(--bg-secondary);
  border: 1px solid var(--border-color);
  border-radius: var(--card-radius);
  padding: 1rem;
  box-shadow: var(--card-shadow);
}
.status-row.compact .status-card { padding: 0.55rem 0.75rem; }
.status-card .sc-label {
  color: var(--text-secondary);
  font-size: 0.75rem;
  font-weight: 600;
  text-transform: uppercase;
  letter-spacing: 0.05em;
  margin-bottom: 0.35rem;
}
.status-card .sc-value { color: var(--text-primary); font-size: 1.35rem; font-weight: 700; }
.status-row.compact .sc-value { font-size: 0.9rem; font-weight: 600; }
.status-card .sc-sub { color: var(--text-secondary); font-size: 0.8rem; margin-top: 0.2rem; }
.status-dot { display: inline-block; width: 9px; height: 9px; border-radius: 50%; margin-right: 6px; vertical-align: middle; }
.status-dot.healthy { background-color: var(--accent-green); }
.status-dot.warning { background-color: var(--accent-yellow); }
.status-dot.error { background-color: var(--accent-red); }
.status-dot.standby { background-color: var(--text-muted); }
.status-row-title {
  color: var(--text-muted); font-size: 0.75rem; font-weight: 600;
  text-transform: uppercase; letter-spacing: 0.05em; margin: 0.25rem 0 0.5rem 0;
}

/* ── Tabs ────────────────────────────────────────────────────── */
.stTabs [data-baseweb="tab-list"] {
  gap: 0.5rem !important;
  background-color: transparent !important;
  border-bottom: 1px solid var(--border-color) !important;
  padding-bottom: 0 !important;
}

.stTabs [data-baseweb="tab"] {
  background-color: transparent !important;
  color: var(--text-secondary) !important;
  font-weight: 500 !important;
  padding: 0.75rem 1rem !important;
  border-radius: var(--card-radius) var(--card-radius) 0 0 !important;
  border: none !important;
}

.stTabs [data-baseweb="tab"]:hover {
  color: var(--text-primary) !important;
  background-color: var(--bg-tertiary) !important;
}

.stTabs [aria-selected="true"] {
  color: var(--accent-blue) !important;
  background-color: var(--bg-secondary) !important;
  border-bottom: 2px solid var(--accent-blue) !important;
}

/* ── Selectbox / Inputs ──────────────────────────────────────── */
.stSelectbox > div > div {
  background-color: var(--bg-tertiary) !important;
  border: 1px solid var(--border-color) !important;
  color: var(--text-primary) !important;
}

.stSelectbox label {
  color: var(--text-secondary) !important;
  font-weight: 500 !important;
}

/* ── Alerts / Info / Success / Warning ───────────────────────── */
.stAlert {
  background-color: var(--bg-tertiary) !important;
  border: 1px solid var(--border-color) !important;
  border-radius: var(--card-radius) !important;
  color: var(--text-primary) !important;
}

.stAlert[data-baseweb="notification"][kind="success"] {
  border-left-color: var(--accent-green) !important;
}

.stAlert[data-baseweb="notification"][kind="warning"] {
  border-left-color: var(--accent-yellow) !important;
}

.stAlert[data-baseweb="notification"][kind="error"] {
  border-left-color: var(--accent-red) !important;
}

/* ── Captions / Small text ───────────────────────────────────── */
.stCaption, .stMarkdown small {
  color: var(--text-muted) !important;
  font-size: 0.75rem !important;
}

/* ── Headings ────────────────────────────────────────────────── */
h1 { color: var(--text-primary) !important; font-weight: 700 !important; font-size: 1.5rem !important; }
h2 { color: var(--text-primary) !important; font-weight: 600 !important; font-size: 1.125rem !important; }
h3 { color: var(--text-primary) !important; font-weight: 600 !important; font-size: 1rem !important; }

/* ── Dividers ────────────────────────────────────────────────── */
hr {
  border-color: var(--border-color) !important;
  opacity: 0.5 !important;
}

/* ── Status Badges (inline) ──────────────────────────────────── */
.status-healthy { color: var(--accent-green) !important; }
.status-warning { color: var(--accent-yellow) !important; }
.status-error { color: var(--accent-red) !important; }
.status-neutral { color: var(--text-muted) !important; }

/* ── Footer ──────────────────────────────────────────────────── */
.footer-bar {
  background-color: var(--bg-secondary) !important;
  border-top: 1px solid var(--border-color) !important;
  padding: 0.75rem 2rem !important;
  margin-top: 2rem !important;
  display: flex !important;
  justify-content: space-between !important;
  color: var(--text-muted) !important;
  font-size: 0.75rem !important;
}

/* ── KPI Row ─────────────────────────────────────────────────── */
.kpi-row {
  display: grid !important;
  grid-template-columns: repeat(5, 1fr) !important;
  gap: 1rem !important;
  margin-bottom: 1.5rem !important;
}

.kpi-card {
  background-color: var(--bg-secondary) !important;
  border: 1px solid var(--border-color) !important;
  border-radius: var(--card-radius) !important;
  padding: 1rem 1.25rem !important;
  box-shadow: var(--card-shadow) !important;
}

.kpi-card .kpi-label {
  font-size: 0.7rem !important;
  font-weight: 600 !important;
  text-transform: uppercase !important;
  letter-spacing: 0.05em !important;
  color: var(--text-muted) !important;
  margin-bottom: 0.5rem !important;
}

.kpi-card .kpi-value {
  font-size: 1.5rem !important;
  font-weight: 700 !important;
  color: var(--text-primary) !important;
}

/* kpi-delta CSS removed — no historical data available, delta indicators not used */

/* ── Scrollbar ───────────────────────────────────────────────── */
::-webkit-scrollbar { width: 8px; height: 8px; }
::-webkit-scrollbar-track { background: var(--bg-primary); }
::-webkit-scrollbar-thumb { background: var(--border-color); border-radius: 4px; }
::-webkit-scrollbar-thumb:hover { background: var(--text-muted); }
</style>
""",
        unsafe_allow_html=True,
    )


def _format_timestamp(value: datetime | None) -> str:
    """Format an optional timestamp consistently for compact tables."""

    return value.isoformat(timespec="seconds") if value is not None else "Never"


def _status_icon(status: str) -> str:
    """Map safe health states to visual indicators."""

    if status in {"healthy", "ready", "ok"}:
        return "\U0001f7e2"
    if status in {"degraded", "starting", "uninitialized", "not_ready"}:
        return "\U0001f7e0"
    if status == "disabled":
        return "\u26aa"
    return "\U0001f534"


def _status_class(status: str) -> str:
    """Return CSS class for status styling."""
    if status in {"healthy", "ready", "ok"}:
        return "status-healthy"
    if status in {"degraded", "starting", "uninitialized", "not_ready"}:
        return "status-warning"
    if status == "disabled":
        return "status-neutral"
    return "status-error"


def _log_rows(entries: tuple[SafeLogEntry, ...]) -> list[dict[str, object]]:
    """Project safe log models into a display-only table."""

    return [
        {
            "Time": entry.timestamp.isoformat(timespec="seconds"),
            "Level": entry.level.value,
            "Source": entry.source,
            "Event": entry.event,
            "Component": entry.component or "-",
            "Status": entry.status or "-",
            "Latency (ms)": entry.latency_ms,
            "Error Category": entry.error_category or "-",
            "Request ID": entry.request_id or "-",
        }
        for entry in entries
    ]


def _render_sidebar(snapshot: OperationsSnapshot | None) -> PageName:
    """Render the sidebar navigation and return the selected page."""

    # Inject CSS first
    _inject_custom_css()

    st.sidebar.markdown("### \U0001f517 ToolBridge Operations")
    st.sidebar.caption("Monitoring + Tool Playground")

    if snapshot is not None:
        system = snapshot.system
        st.sidebar.markdown("---")
        st.sidebar.caption(f"Version: {system.version}")
        st.sidebar.caption(f"Environment: {system.environment}")
        st.sidebar.caption(
            f"Health: <span class='{_status_class(system.health_status)}'>"
            f"{_status_icon(system.health_status)} {escape(system.health_status)}</span>",
            unsafe_allow_html=True,
        )
        st.sidebar.caption(f"Uptime: {system.uptime_seconds:,.1f}s")

    if st.sidebar.button("Refresh", width="stretch"):
        st.rerun()

    st.sidebar.markdown("---")

    navigation_items: list[PageName] = [
        "Overview",
        "Tools",
        "Tool Playground",
        "Providers",
        "History",
        "Logs",
        "Settings",
        "System Health",
        "Costs",
    ]

    # Use session state to persist selection
    if "selected_page" not in st.session_state:
        st.session_state.selected_page = "Overview"

    selected = st.sidebar.radio(
        "Navigation",
        navigation_items,
        index=navigation_items.index(st.session_state.selected_page),
        key="nav_radio",
        label_visibility="collapsed",
    )
    st.session_state.selected_page = selected
    return selected


def _render_footer(snapshot: OperationsSnapshot | None) -> None:
    """Render a compact footer with real values."""

    system = snapshot.system if snapshot is not None else None

    version_text = system.version if system else "—"
    uptime_text = f"{system.uptime_seconds:,.1f}s" if system else "N/A"
    environment_text = system.environment if system else "N/A"
    st.markdown(
        '<div class="footer-bar">'
        f"<span>\U0001f517 ToolBridge v{escape(version_text)}</span>"
        f"<span>\U0001f4c5 Uptime: {escape(uptime_text)}</span>"
        f"<span>\U0001f310 Environment: {escape(environment_text)}</span>"
        "</div>",
        unsafe_allow_html=True,
    )


def _dot_class(status: str) -> str:
    if status in {"healthy", "ready", "ok"}:
        return "healthy"
    if status in {"degraded", "starting", "uninitialized", "not_ready"}:
        return "warning"
    if status == "disabled":
        return "standby"
    return "error"


def _provider_item_html(provider: ProviderMonitor) -> str:
    """Render one provider as a metric-style status card."""

    role_text = (
        "Active" if provider.active else ("Failover" if provider.failover_active else "Standby")
    )
    return (
        '<div class="status-card">'
        f'<div class="sc-label">{escape(provider.provider.title())}</div>'
        f'<div class="sc-value"><span class="status-dot {_dot_class(provider.status)}"></span>'
        f"{escape(provider.status.title())}</div>"
        f'<div class="sc-sub">{escape(role_text)}</div>'
        "</div>"
    )


def _tool_item_html(item: ToolMonitor) -> str:
    """Render one tool as a compact status card."""

    enabled_text = "Enabled" if item.registered else "Disabled"
    return (
        '<div class="status-card">'
        f'<div class="sc-label">{escape(item.display_name)}</div>'
        f'<div class="sc-value"><span class="status-dot {_dot_class(item.health)}"></span>'
        f"{escape(item.health.title())}</div>"
        f'<div class="sc-sub">{enabled_text}</div>'
        "</div>"
    )


def _render_status_bar(snapshot: OperationsSnapshot | None) -> None:
    """Render provider and tool status as rows of cards at the top of the page."""

    if snapshot is None:
        st.markdown(
            '<div class="status-row"><div class="status-card">'
            '<div class="sc-label">Provider Status</div>'
            '<div class="sc-value"><span class="status-dot standby"></span>Unavailable</div>'
            '<div class="sc-sub">No snapshot</div></div></div>',
            unsafe_allow_html=True,
        )
        return

    provider_cards = "".join(_provider_item_html(provider) for provider in snapshot.providers)
    tool_cards = "".join(_tool_item_html(item) for item in snapshot.tools)
    st.markdown(
        '<div class="status-row-title">Provider Status</div>'
        f'<div class="status-row">{provider_cards}</div>'
        f'<div class="status-row-title">Tools ({len(snapshot.tools)})</div>'
        f'<div class="status-row compact">{tool_cards}</div>',
        unsafe_allow_html=True,
    )


def _render_history(snapshot: OperationsSnapshot) -> None:
    """Render recent tool activity from in-memory metrics and safe logs."""

    st.title("History")
    st.caption(
        "Recent activity for this server process (in-memory; resets on restart). "
        "Tool arguments and results are never stored."
    )

    tools = sorted(snapshot.tools, key=lambda item: item.execution_count, reverse=True)
    used = [item for item in tools if item.execution_count > 0]
    summary = st.columns(3)
    summary[0].metric("Tool Calls", f"{sum(item.execution_count for item in tools):,}")
    summary[1].metric("Tools Used", f"{len(used)} / {len(tools)}")
    last_times = [item.last_execution for item in tools if item.last_execution is not None]
    summary[2].metric(
        "Last Call",
        max(last_times).strftime("%H:%M:%S UTC") if last_times else "None yet",
    )

    st.subheader("Tool Usage")
    if used:
        st.dataframe(
            [
                {
                    "Tool": item.display_name,
                    "Calls": item.execution_count,
                    "Avg (ms)": round(item.average_response_time_ms, 1),
                    "Last Call (UTC)": (
                        item.last_execution.strftime("%Y-%m-%d %H:%M:%S")
                        if item.last_execution
                        else "—"
                    ),
                    "Health": item.health,
                }
                for item in used
            ],
            hide_index=True,
            width="stretch",
        )
    else:
        st.info("No tool calls yet. Call a tool through the MCP endpoint, then refresh.")

    st.subheader("Recent Events")
    events = sorted(
        (entry for entry in snapshot.logs if entry.request_id or entry.component),
        key=lambda entry: entry.timestamp,
        reverse=True,
    )
    if events:
        st.dataframe(
            [
                {
                    "Time (UTC)": entry.timestamp.strftime("%H:%M:%S"),
                    "Level": entry.level.value,
                    "Event": entry.event,
                    "Component": entry.component or "—",
                    "Status": entry.status or "—",
                    "Latency (ms)": (
                        round(entry.latency_ms, 1) if entry.latency_ms is not None else None
                    ),
                    "Error": entry.error_category or "",
                }
                for entry in events[:50]
            ],
            hide_index=True,
            width="stretch",
        )
    else:
        st.info("No recorded events yet.")


def _render_overview(snapshot: OperationsSnapshot) -> None:
    """Render the Overview page with KPI cards and readiness."""

    metrics = snapshot.metrics
    costs = snapshot.costs

    # Page header
    st.title("ToolBridge MCP Operations")
    st.caption(
        "Read-only process monitoring. Prompts, tool inputs, outputs, URLs, "
        "queries, paths, and credentials are never included."
    )

    # KPI Cards row (custom HTML to match reference design)
    total_requests = metrics.total_requests
    total_tokens = costs.estimated_token_usage
    total_cost = costs.estimated_api_cost_usd

    if metrics.total_requests > 0 and metrics.average_response_time_ms > 0:
        avg_ms = metrics.average_response_time_ms
        if avg_ms >= 1000:
            latency_str = f"{avg_ms / 1000:.2f} s"
        else:
            latency_str = f"{avg_ms:,.1f} ms"
    else:
        latency_str = "N/A"

    if metrics.total_requests > 0:
        success_rate = metrics.successful_requests / metrics.total_requests
        success_str = f"{success_rate:.1%}"
    else:
        success_str = "No requests"

    st.markdown(
        f"""
<div class="kpi-row">
    <div class="kpi-card">
        <div class="kpi-label">Total Requests</div>
        <div class="kpi-value">{total_requests:,}</div>
    </div>
    <div class="kpi-card">
        <div class="kpi-label">Estimated Token Usage</div>
        <div class="kpi-value">{total_tokens:,}</div>
    </div>
    <div class="kpi-card">
        <div class="kpi-label">Total Cost</div>
        <div class="kpi-value">${total_cost:,.6f}</div>
    </div>
    <div class="kpi-card">
        <div class="kpi-label">Avg Latency</div>
        <div class="kpi-value">{escape(latency_str)}</div>
    </div>
    <div class="kpi-card">
        <div class="kpi-label">Success Rate</div>
        <div class="kpi-value">{escape(success_str)}</div>
    </div>
</div>
""",
        unsafe_allow_html=True,
    )

    st.markdown("---")

    # Provider Status Section
    st.subheader("Provider Status")
    provider_cols = st.columns(len(snapshot.providers))
    for idx, provider in enumerate(snapshot.providers):
        with provider_cols[idx]:
            status_icon = _status_icon(provider.status)
            st.metric(
                label=provider.provider.title(),
                value=f"{status_icon} {provider.status}",
            )
            if provider.health_score:
                st.caption(f"Health: {provider.health_score:.0%}")
            if provider.active:
                st.caption("🟢 Active Provider")
            elif provider.failover_active:
                st.caption("🟡 Failover Active")
            else:
                st.caption("⚪ Standby")

            st.caption(f"Models: {provider.model_count}")

            if provider.response_latency_ms and provider.response_latency_ms > 0:
                lat_ms = provider.response_latency_ms
                if lat_ms >= 1000:
                    st.caption(f"Latency: {lat_ms / 1000:.2f} s")
                else:
                    st.caption(f"Latency: {lat_ms:.0f} ms")

            if provider.requests > 0 or provider.errors > 0:
                st.caption(f"Requests: {provider.requests} | Errors: {provider.errors}")

    st.markdown("---")

    # Readiness Checks
    st.subheader("Readiness Checks")
    readiness_rows = [
        {
            "Check": item.name,
            "Ready": "✅" if item.ready else "❌",
            "Status": item.status,
        }
        for item in snapshot.readiness.checks
    ]
    st.dataframe(readiness_rows, width="stretch", hide_index=True)


def _render_providers(snapshot: OperationsSnapshot) -> None:
    """Render the Providers page with clean card layout for provider health and models."""

    st.title("Providers")
    st.caption("Provider routing, health, and discovered models.")

    # Provider status cards
    for idx, provider in enumerate(snapshot.providers):
        with st.container(border=True):
            st.subheader(f"{provider.provider.title()} Provider")

            # Status row
            status_cols = st.columns(4)
            status_icon = _status_icon(provider.status)
            status_cols[0].metric("Status", f"{status_icon} {provider.status}")

            if provider.active:
                status_cols[1].metric("Role", "🟢 Active")
            elif provider.failover_active:
                status_cols[1].metric("Role", "🟡 Failover")
            else:
                status_cols[1].metric("Role", "⚪ Standby")

            status_cols[2].metric(
                "Health Score", f"{provider.health_score:.0%}" if provider.health_score else "N/A"
            )
            status_cols[3].metric("Models Discovered", provider.model_count)

            # Detail row
            detail_cols = st.columns(4)
            if provider.response_latency_ms and provider.response_latency_ms > 0:
                lat_ms = provider.response_latency_ms
                if lat_ms >= 1000:
                    detail_cols[0].metric("Latency", f"{lat_ms / 1000:.2f} s")
                else:
                    detail_cols[0].metric("Latency", f"{lat_ms:.0f} ms")
            else:
                detail_cols[0].metric("Latency", "N/A")

            detail_cols[1].metric("Requests", f"{provider.requests:,}")
            detail_cols[2].metric("Errors", f"{provider.errors:,}")
            detail_cols[3].metric(
                "Success Rate",
                f"{provider.success_rate:.1%}" if provider.requests > 0 else "No requests",
            )

            # Configuration info
            config_cols = st.columns(3)
            config_cols[0].caption(f"Priority: {provider.priority}")
            config_cols[1].caption(f"Configured: {'Yes' if provider.configured else 'No'}")
            config_cols[2].caption(f"Available: {'Yes' if provider.available else 'No'}")

            if provider.capabilities:
                st.caption(f"Capabilities: {', '.join(provider.capabilities)}")

            if provider.requests > 0 or provider.errors > 0:
                cost_cols = st.columns(2)
                cost_cols[0].caption(f"Daily Cost: ${provider.daily_cost_usd:,.6f}")
                cost_cols[1].caption(f"Monthly Cost: ${provider.monthly_cost_usd:,.6f}")

            if provider.active_model:
                st.caption(f"Active Model: {provider.active_model}")

            if provider.selection_reason:
                st.caption(f"Selection Reason: {provider.selection_reason}")

        if idx < len(snapshot.providers) - 1:
            st.markdown("---")

    st.markdown("---")

    # Discovered Models
    st.subheader("Discovered Models")
    model_rows = [
        {
            "Provider": item.provider,
            "Model": item.model,
            "Available": "✅" if item.available else "❌",
            "Free": "✅" if item.is_free else "❌",
            "Capabilities": ", ".join(item.capabilities) or "—",
            "Context Window": item.context_window if item.context_window else "—",
            "Input $/1M": f"${item.input_cost_per_million_tokens_usd:,.4f}",
            "Output $/1M": f"${item.output_cost_per_million_tokens_usd:,.4f}",
            "Latency (ms)": f"{item.latency_ms:.0f}" if item.latency_ms else "—",
            "Health Score": f"{item.health_score:.0%}" if item.health_score else "—",
            "Reasoning Quality": f"{item.reasoning_quality:.0%}"
            if item.reasoning_quality
            else "—",
            "Discovered": _format_timestamp(item.discovered_at),
        }
        for item in snapshot.models
    ]
    if model_rows:
        st.dataframe(model_rows, width="stretch", hide_index=True)
    else:
        st.info("No enabled provider models are currently cached.")

    st.caption("Data source: /operations/snapshot — read-only, no credentials exposed.")


def _render_tools(snapshot: OperationsSnapshot) -> None:
    """Render the Tools page with clean card layout for MCP tools."""

    st.title("Tools")
    st.caption("MCP tool registry and execution status.")

    # Header metrics
    total_tools = len(snapshot.tools)
    registered_count = sum(1 for t in snapshot.tools if t.registered)
    healthy_count = sum(1 for t in snapshot.tools if t.health == "healthy")
    total_executions = sum(t.execution_count for t in snapshot.tools)

    header_cols = st.columns(4)
    header_cols[0].metric("Total Tools", total_tools)
    header_cols[1].metric("Registered", f"{registered_count}/{total_tools}")
    header_cols[2].metric("Healthy", f"{healthy_count}/{total_tools}")
    header_cols[3].metric("Total Executions", f"{total_executions:,}")

    st.markdown("---")

    # Tool cards - one per tool with status and metrics
    for item in snapshot.tools:
        with st.container(border=True):
            col1, col2, col3, col4 = st.columns([3, 1, 2, 2])

            with col1:
                status_icon = _status_icon(item.health)
                reg_badge = "🟢 Registered" if item.registered else "🔴 Missing"
                st.markdown(f"**{item.display_name}** `{item.tool_name}`")
                st.caption(f"{status_icon} {item.health} • {reg_badge}")

            with col2:
                st.metric("Executions", f"{item.execution_count:,}")

            with col3:
                avg_ms = item.average_response_time_ms
                if avg_ms > 0:
                    if avg_ms >= 1000:
                        st.metric("Avg Latency", f"{avg_ms / 1000:.2f} s")
                    else:
                        st.metric("Avg Latency", f"{avg_ms:,.1f} ms")
                else:
                    st.metric("Avg Latency", "N/A")

            with col4:
                last_exec = _format_timestamp(item.last_execution)
                st.metric("Last Run", last_exec)

    st.markdown("---")
    st.caption("Data source: /operations/snapshot — read-only, no credentials exposed.")


def _render_logs(snapshot: OperationsSnapshot) -> None:
    """Render the Logs page with improved readability."""

    st.title("Logs")
    st.caption("Operational log entries (read-only, sanitized).")

    # Log summary metrics
    total_logs = len(snapshot.logs)
    info_count = sum(1 for entry in snapshot.logs if entry.level.value == "INFO")
    warning_count = sum(1 for entry in snapshot.logs if entry.level.value == "WARNING")
    error_count = sum(1 for entry in snapshot.logs if entry.level.value == "ERROR")

    summary_cols = st.columns(4)
    summary_cols[0].metric("Total Entries", total_logs)
    summary_cols[1].metric("INFO", info_count)
    summary_cols[2].metric("WARNING", warning_count)
    summary_cols[3].metric("ERROR", error_count)

    st.markdown("---")

    # Level filter
    level = st.selectbox("Filter by Level", ("All", "INFO", "WARNING", "ERROR"))
    visible = tuple(item for item in snapshot.logs if level == "All" or item.level.value == level)

    if visible:
        # Display as cards for better readability
        for entry in visible:
            level_icon = {"INFO": "ℹ️", "WARNING": "⚠️", "ERROR": "❌"}.get(entry.level.value, "📝")
            with st.container(border=True):
                # Header row
                header_cols = st.columns([3, 2, 2])
                header_cols[0].markdown(f"**{level_icon} {entry.event}**")
                header_cols[1].caption(f"Source: {entry.source}")
                header_cols[2].caption(f"Level: {entry.level.value}")

                # Detail row
                detail_cols = st.columns([2, 2, 2])
                detail_cols[0].caption(f"Time: {entry.timestamp.isoformat(timespec='seconds')}")
                if entry.component:
                    detail_cols[1].caption(f"Component: {entry.component}")
                if entry.status:
                    detail_cols[2].caption(f"Status: {entry.status}")

                # Metadata row
                meta_cols = st.columns([2, 2, 2])
                if entry.latency_ms is not None:
                    lat = entry.latency_ms
                    if lat >= 1000:
                        meta_cols[0].caption(f"Latency: {lat / 1000:.2f} s")
                    else:
                        meta_cols[0].caption(f"Latency: {lat:.1f} ms")
                if entry.error_category:
                    meta_cols[1].caption(f"Error Category: {entry.error_category}")
                if entry.request_id:
                    meta_cols[2].caption(f"Request ID: {entry.request_id[:8]}...")

    else:
        st.info(f"No logs match the selected level: {level}")

    st.markdown("---")
    st.caption("Data source: /operations/snapshot — read-only, no credentials exposed.")


def _render_costs(snapshot: OperationsSnapshot) -> None:
    """Render the Costs page with real cost/metrics data and honest zero-state handling."""

    st.title("Costs")
    st.caption("Request metrics, tool usage, provider usage, and cost estimates (all estimated).")

    metrics = snapshot.metrics
    costs = snapshot.costs

    # Request Metrics
    st.subheader("Request Metrics")
    metric_columns = st.columns(4)
    metric_columns[0].metric("Total Requests", f"{metrics.total_requests:,}")
    metric_columns[1].metric("Successful", f"{metrics.successful_requests:,}")
    metric_columns[2].metric("Failed", f"{metrics.failed_requests:,}")

    if metrics.total_requests > 0 and metrics.average_response_time_ms > 0:
        avg_ms = metrics.average_response_time_ms
        if avg_ms >= 1000:
            metric_columns[3].metric("Avg Response", f"{avg_ms / 1000:.2f} s")
        else:
            metric_columns[3].metric("Avg Response", f"{avg_ms:,.1f} ms")
    else:
        metric_columns[3].metric("Avg Response", "N/A")

    st.markdown("---")

    # Usage Charts
    st.subheader("Usage Breakdown")
    charts = st.columns(2)
    with charts[0]:
        st.markdown("#### Tool Usage")
        if metrics.tool_usage:
            st.bar_chart(metrics.tool_usage)
        else:
            st.info("No tool usage recorded.")
    with charts[1]:
        st.markdown("#### Provider Usage")
        if metrics.provider_usage:
            st.bar_chart(metrics.provider_usage)
        else:
            st.info("No provider usage recorded.")

    st.markdown("#### Error Categories")
    if metrics.error_categories:
        st.bar_chart(metrics.error_categories)
    else:
        st.info("No tool execution errors recorded in this process.")

    st.markdown("---")

    # Cost Dashboard - clearly labeled as estimates
    st.subheader("Cost Estimates")
    cost_columns = st.columns(2)
    cost_columns[0].metric(
        "Estimated Token Usage",
        f"{costs.estimated_token_usage:,}",
    )
    cost_columns[1].metric(
        "Estimated API Cost (USD)",
        f"${costs.estimated_api_cost_usd:,.6f}",
    )
    cost_rows = [
        {
            "Provider": provider,
            "Requests": costs.requests_per_provider.get(provider, 0),
            "Estimated Cost (USD)": cost,
        }
        for provider, cost in costs.cost_per_provider.items()
    ]
    st.dataframe(cost_rows, width="stretch", hide_index=True)
    st.caption(
        "All cost values are estimates calculated from configured per-million-token "
        "rates. Zero rates produce a $0 estimate. These are not actual billing figures."
    )

    st.caption("Data source: /operations/snapshot — read-only, no credentials exposed.")


def _mcp_host_port(settings: Settings) -> tuple[str, int]:
    """Return the host/port of the server the dashboard actually talks to."""

    parsed = urlsplit(str(settings.operations.dashboard_api_url))
    return parsed.hostname or settings.host, parsed.port or settings.port


def _render_settings(snapshot: OperationsSnapshot | None) -> None:
    """Render the Settings page (sanitized read-only config with clean layout)."""

    st.title("Settings")
    st.caption("Read-only configuration view. Secrets are never displayed.")

    settings = get_settings()

    # Operations section
    with st.container(border=True):
        st.subheader("📋 Operations Configuration")
        ops_cols = st.columns(2)
        ops_cols[0].markdown(f"**Dashboard API URL:** `{settings.operations.dashboard_api_url}`")
        ops_cols[1].markdown(f"**Timeout:** {settings.operations.dashboard_timeout_seconds}s")

    # Providers section
    with st.container(border=True):
        st.subheader("🔌 Providers (configured, secrets hidden)")
        for provider_name in ("cerebras", "nvidia", "openrouter"):
            provider_config = getattr(settings, provider_name)
            st.markdown(f"### {provider_name.title()}")
            prov_cols = st.columns(3)
            prov_cols[0].markdown(f"**Enabled:** {'✅' if provider_config.enabled else '❌'}")
            prov_cols[1].markdown(
                f"**API Key Configured:** {'✅' if provider_config.api_key else '❌'}"
            )
            prov_cols[2].markdown(f"**Default Model:** {provider_config.default_model or '—'}")

            if provider_config.base_url:
                st.markdown(f"**Base URL:** `{provider_config.base_url}`")

    # Tools section
    with st.container(border=True):
        st.subheader("🛠️ Tools Configuration")
        if snapshot is not None:
            registered_tools = [item.tool_name for item in snapshot.tools if item.registered]
            tools_cols = st.columns(2)
            tools_cols[0].markdown(
                f"**Registered:** {len(registered_tools)}/{len(snapshot.tools)}"
            )
            tools_cols[1].markdown(f"**Tool Count:** {len(snapshot.tools)}")

            if registered_tools:
                with st.expander("Registered Tools"):
                    for tool in registered_tools:
                        st.markdown(f"- `{tool}`")
        else:
            st.info("Tool registry unavailable — no operations snapshot.")

    render_provider_setup()

    # MCP section
    with st.container(border=True):
        st.subheader("🔗 MCP Configuration")
        mcp_cols = st.columns(3)
        mcp_cols[0].markdown("**Transport:** Streamable HTTP")
        mcp_host, mcp_port = _mcp_host_port(settings)
        mcp_cols[1].markdown(f"**Host:** `{mcp_host}`")
        mcp_cols[2].markdown(f"**Port:** {mcp_port}")
        st.markdown("**Mount Path:** `/mcp`")

    st.markdown("---")
    st.caption("Data source: ToolBridge configuration — secrets masked, read-only view.")


def _render_system_health(snapshot: OperationsSnapshot) -> None:
    """Render the System Health page with clear health and readiness diagnostics."""

    st.title("System Health")
    st.caption("Deep health and readiness diagnostics.")

    system = snapshot.system

    # System Overview - KPI cards
    st.subheader("System Overview")
    sys_cols = st.columns(4)
    sys_cols[0].metric("Version", system.version)
    sys_cols[1].metric("Uptime", f"{system.uptime_seconds:,.1f}s")
    sys_cols[2].metric("Environment", system.environment)
    sys_cols[3].metric(
        "Health",
        f"{_status_icon(system.health_status)} {system.health_status}",
    )

    st.markdown("---")

    # Lifecycle Information
    st.subheader("Lifecycle")
    lifecycle_cols = st.columns(3)
    lifecycle_cols[0].markdown(f"**Current Phase:** {system.current_phase}")
    lifecycle_cols[1].markdown(f"**Lifecycle State:** {system.lifecycle.value}")
    lifecycle_cols[2].markdown(f"**Started At:** {system.started_at.isoformat()}")

    st.markdown("---")

    # Readiness Checks
    st.subheader("Readiness Checks")
    readiness_rows = [
        {
            "Check": item.name,
            "Ready": "✅" if item.ready else "❌",
            "Status": item.status,
        }
        for item in snapshot.readiness.checks
    ]
    st.dataframe(readiness_rows, width="stretch", hide_index=True)

    # Readiness summary
    all_ready = all(item.ready for item in snapshot.readiness.checks)
    if all_ready:
        st.success("All readiness checks passing — system is ready to serve traffic.")
    else:
        st.warning("Some readiness checks are not passing — system may not be fully operational.")

    st.markdown("---")

    # Provider Health Summary
    st.subheader("Provider Health Summary")
    for provider in snapshot.providers:
        with st.container(border=True):
            st.markdown(f"### {provider.provider.title()} Provider")

            health_cols = st.columns(4)
            status_icon = _status_icon(provider.status)
            health_cols[0].metric("Status", f"{status_icon} {provider.status}")

            if provider.active:
                health_cols[1].metric("Role", "🟢 Active")
            elif provider.failover_active:
                health_cols[1].metric("Role", "🟡 Failover")
            else:
                health_cols[1].metric("Role", "⚪ Standby")

            health_cols[2].metric(
                "Health Score", f"{provider.health_score:.1%}" if provider.health_score else "N/A"
            )
            health_cols[3].metric("Models", provider.model_count)

            detail_cols = st.columns(4)
            if provider.response_latency_ms and provider.response_latency_ms > 0:
                lat = provider.response_latency_ms
                if lat >= 1000:
                    detail_cols[0].caption(f"Latency: {lat / 1000:.2f} s")
                else:
                    detail_cols[0].caption(f"Latency: {lat:.0f} ms")
            detail_cols[1].caption(f"Requests: {provider.requests:,}")
            detail_cols[2].caption(f"Errors: {provider.errors:,}")
            detail_cols[3].caption(
                f"Success: {provider.success_rate:.1%}"
                if provider.requests > 0
                else "Success: No requests"
            )

            config_cols = st.columns(3)
            config_cols[0].caption(f"Priority: {provider.priority}")
            config_cols[1].caption(f"Configured: {'Yes' if provider.configured else 'No'}")
            config_cols[2].caption(f"Available: {'Yes' if provider.available else 'No'}")

            if provider.capabilities:
                st.caption(f"Capabilities: {', '.join(provider.capabilities)}")

            if provider.active_model:
                st.caption(f"Active Model: {provider.active_model}")

            if provider.selection_reason:
                st.caption(f"Selection Reason: {provider.selection_reason}")

            if provider.requests > 0 or provider.errors > 0:
                cost_cols = st.columns(2)
                cost_cols[0].caption(f"Daily Cost: ${provider.daily_cost_usd:,.6f}")
                cost_cols[1].caption(f"Monthly Cost: ${provider.monthly_cost_usd:,.6f}")

    st.markdown("---")

    # Tool Registry Health
    st.subheader("MCP Tool Registry")
    tool_rows = [
        {
            "Tool": item.display_name,
            "Registered": "✅" if item.registered else "❌",
            "Health": f"{_status_icon(item.health)} {item.health}",
            "Executions": f"{item.execution_count:,}",
            "Avg Latency": f"{item.average_response_time_ms:,.1f} ms"
            if item.average_response_time_ms > 0
            else "N/A",
            "Last Run": _format_timestamp(item.last_execution),
        }
        for item in snapshot.tools
    ]
    st.dataframe(tool_rows, width="stretch", hide_index=True)

    st.caption("Data source: /operations/snapshot — read-only, no credentials exposed.")


def _render_page(page: PageName, snapshot: OperationsSnapshot | None) -> None:
    """Dispatch to the appropriate page renderer."""

    if page == "Tool Playground":
        render_playground()
        return

    if snapshot is None:
        st.title(page)
        st.error("Dashboard unavailable — cannot fetch operations snapshot.")
        st.info("Start the ToolBridge API locally, then refresh this page.")
        return

    page_renderers = {
        "Overview": _render_overview,
        "Tools": _render_tools,
        "Providers": _render_providers,
        "History": _render_history,
        "Logs": _render_logs,
        "Settings": _render_settings,
        "System Health": _render_system_health,
        "Costs": _render_costs,
    }

    renderer = page_renderers.get(page)
    if renderer:
        renderer(snapshot)
    else:
        st.title(page)
        st.warning(f"No renderer implemented for page: {page}")


def render_dashboard(snapshot: OperationsSnapshot) -> None:
    """
    Compatibility renderer for tests.
    Renders all original sections using the legacy tab-based layout.
    """
    system = snapshot.system
    st.title("ToolBridge MCP Operations")
    st.caption(
        "Read-only process monitoring. Prompts, tool inputs, outputs, URLs, "
        "queries, paths, and credentials are never included."
    )

    overview, providers_tab, tools_tab, metrics_tab, logs_tab = st.tabs(
        ["Overview", "Providers", "MCP Tools", "Metrics & Cost", "Logs"]
    )

    with overview:
        st.subheader("System Overview")
        columns = st.columns(5)
        columns[0].metric("Version", system.version)
        columns[1].metric("Uptime", f"{system.uptime_seconds:,.1f}s")
        columns[2].metric("Environment", system.environment)
        columns[3].metric("Current Phase", system.current_phase)
        columns[4].metric(
            "Health",
            f"{_status_icon(system.health_status)} {system.health_status}",
        )
        st.markdown("#### Readiness Checks")
        readiness_rows = [
            {
                "Check": item.name,
                "Ready": item.ready,
                "Status": item.status,
            }
            for item in snapshot.readiness.checks
        ]
        st.dataframe(readiness_rows, width="stretch", hide_index=True)

    with providers_tab:
        st.subheader("Provider Dashboard")
        active = next((item.provider for item in snapshot.providers if item.active), "None")
        failover = any(item.failover_active for item in snapshot.providers)
        provider_headline = st.columns(2)
        provider_headline[0].metric("Active Provider", active)
        provider_headline[1].metric(
            "Failover Status",
            "Active" if failover else "Standby",
        )
        provider_rows = [
            {
                "Priority": item.priority,
                "Provider": item.provider,
                "Configured": item.configured,
                "Available": item.available,
                "Active": item.active,
                "Active Model": item.active_model or "-",
                "Health": f"{_status_icon(item.status)} {item.status}",
                "Health Score": item.health_score,
                "Capabilities": ", ".join(item.capabilities) or "-",
                "Models": item.model_count,
                "Latency (ms)": item.response_latency_ms,
                "Requests": item.requests,
                "Errors": item.errors,
                "Retries": item.retries,
                "Success Rate": f"{item.success_rate:.1%}",
                "Daily Cost": item.daily_cost_usd,
                "Monthly Cost": item.monthly_cost_usd,
                "Daily Budget": item.daily_budget_usd,
                "Monthly Budget": item.monthly_budget_usd,
                "Cache Age (s)": item.model_cache_age_seconds,
                "Discovery (ms)": item.model_discovery_time_ms,
                "Selection Reason": item.selection_reason or "-",
                "Last Success": _format_timestamp(item.last_successful_request),
                "Last Failure": _format_timestamp(item.last_failed_request),
                "Error Category": item.error_category or "-",
            }
            for item in snapshot.providers
        ]
        st.dataframe(provider_rows, width="stretch", hide_index=True)
        st.markdown("#### Discovered Models")
        model_rows = [
            {
                "Provider": item.provider,
                "Model": item.model,
                "Available": item.available,
                "Free": item.is_free,
                "Capabilities": ", ".join(item.capabilities) or "-",
                "Context Window": item.context_window,
                "Input $/1M": item.input_cost_per_million_tokens_usd,
                "Output $/1M": item.output_cost_per_million_tokens_usd,
                "Latency (ms)": item.latency_ms,
                "Health Score": item.health_score,
                "Reasoning Quality": item.reasoning_quality,
                "Discovered": _format_timestamp(item.discovered_at),
            }
            for item in snapshot.models
        ]
        if model_rows:
            st.dataframe(model_rows, width="stretch", hide_index=True)
        else:
            st.info("No enabled provider models are currently cached.")

    with tools_tab:
        st.subheader("MCP Tool Dashboard")
        tool_rows = [
            {
                "Tool": item.display_name,
                "Registration": "Registered" if item.registered else "Missing",
                "Health": f"{_status_icon(item.health)} {item.health}",
                "Execution Count": item.execution_count,
                "Average Response (ms)": item.average_response_time_ms,
                "Last Execution": _format_timestamp(item.last_execution),
            }
            for item in snapshot.tools
        ]
        st.dataframe(tool_rows, width="stretch", hide_index=True)

    with metrics_tab:
        st.subheader("Metrics Dashboard")
        metrics = snapshot.metrics
        metric_columns = st.columns(4)
        metric_columns[0].metric("Total Requests", metrics.total_requests)
        metric_columns[1].metric("Successful", metrics.successful_requests)
        metric_columns[2].metric("Failed", metrics.failed_requests)
        metric_columns[3].metric(
            "Average Response",
            f"{metrics.average_response_time_ms:,.2f} ms",
        )
        charts = st.columns(2)
        with charts[0]:
            st.markdown("#### Tool Usage")
            st.bar_chart(metrics.tool_usage)
        with charts[1]:
            st.markdown("#### Provider Usage")
            st.bar_chart(metrics.provider_usage)
        st.markdown("#### Error Categories")
        if metrics.error_categories:
            st.bar_chart(metrics.error_categories)
        else:
            st.info("No tool execution errors recorded in this process.")

        st.subheader("Cost Dashboard")
        costs = snapshot.costs
        cost_columns = st.columns(2)
        cost_columns[0].metric(
            "Estimated Token Usage",
            f"{costs.estimated_token_usage:,}",
        )
        cost_columns[1].metric(
            "Estimated API Cost",
            f"${costs.estimated_api_cost_usd:,.6f}",
        )
        cost_rows = [
            {
                "Provider": provider,
                "Requests": costs.requests_per_provider.get(provider, 0),
                "Estimated Cost (USD)": cost,
            }
            for provider, cost in costs.cost_per_provider.items()
        ]
        st.dataframe(cost_rows, width="stretch", hide_index=True)
        st.caption(
            "Cost values are estimates calculated from configured per-million-token "
            "rates; zero rates produce a $0 estimate."
        )

    with logs_tab:
        st.subheader("Log Viewer")
        level = st.selectbox("Level", ("All", "INFO", "WARNING", "ERROR"))
        visible = tuple(
            item for item in snapshot.logs if level == "All" or item.level.value == level
        )
        if visible:
            st.dataframe(
                _log_rows(visible),
                width="stretch",
                hide_index=True,
            )
        else:
            st.info("No logs match the selected level.")


def main() -> None:
    """Load one safe snapshot and render the read-only dashboard."""

    st.set_page_config(
        page_title="ToolBridge Operations",
        page_icon="\U0001f517",
        layout="wide",
        initial_sidebar_state="expanded",
    )

    # Inject custom CSS early
    _inject_custom_css()

    settings = get_settings()

    # Fetch snapshot once (shared across all pages)
    client = DashboardClient(
        str(settings.operations.dashboard_api_url),
        settings.operations.dashboard_timeout_seconds,
    )
    try:
        snapshot = client.fetch_snapshot()
    except DashboardUnavailableError:
        snapshot = None
        # We still render the sidebar and let page renderers handle the error

    # Render sidebar navigation
    selected_page = _render_sidebar(snapshot)

    # Render provider / tool status cards at the top of the page
    _render_status_bar(snapshot)

    # Render selected page
    _render_page(selected_page, snapshot)

    # Render footer
    _render_footer(snapshot)


if __name__ == "__main__":
    main()
