"""Professional read-only Streamlit dashboard for ToolBridge monitoring."""

from datetime import datetime

import streamlit as st

from toolbridge.config import get_settings
from toolbridge.dashboard.client import DashboardClient, DashboardUnavailableError
from toolbridge.operations.domain.models import OperationsSnapshot, SafeLogEntry


def _format_timestamp(value: datetime | None) -> str:
    """Format an optional timestamp consistently for compact tables."""

    return value.isoformat(timespec="seconds") if value is not None else "Never"


def _status_icon(status: str) -> str:
    """Map safe health states to visual indicators."""

    if status in {"healthy", "ready", "ok"}:
        return "🟢"
    if status in {"degraded", "starting", "uninitialized", "not_ready"}:
        return "🟠"
    if status == "disabled":
        return "⚪"
    return "🔴"


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


def render_dashboard(snapshot: OperationsSnapshot) -> None:
    """Render every required dashboard section from one immutable snapshot."""

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
        st.dataframe(readiness_rows, use_container_width=True, hide_index=True)

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
                "Active": item.active,
                "Health": f"{_status_icon(item.status)} {item.status}",
                "Response Latency (ms)": item.response_latency_ms,
                "Last Success": _format_timestamp(item.last_successful_request),
                "Last Failure": _format_timestamp(item.last_failed_request),
                "Error Category": item.error_category or "-",
            }
            for item in snapshot.providers
        ]
        st.dataframe(provider_rows, use_container_width=True, hide_index=True)

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
        st.dataframe(tool_rows, use_container_width=True, hide_index=True)

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
        st.dataframe(cost_rows, use_container_width=True, hide_index=True)
        st.caption(
            "Cost values are estimates calculated from configured per-million-token "
            "rates; zero rates produce a $0 estimate."
        )

    with logs_tab:
        st.subheader("Log Viewer")
        level = st.selectbox("Level", ("All", "INFO", "WARNING", "ERROR"))
        visible = tuple(
            item
            for item in snapshot.logs
            if level == "All" or item.level.value == level
        )
        if visible:
            st.dataframe(
                _log_rows(visible),
                use_container_width=True,
                hide_index=True,
            )
        else:
            st.info("No logs match the selected level.")


def main() -> None:
    """Load one safe snapshot and render the read-only dashboard."""

    st.set_page_config(
        page_title="ToolBridge Operations",
        page_icon="🔗",
        layout="wide",
    )
    settings = get_settings()
    st.sidebar.header("ToolBridge Operations")
    st.sidebar.caption("Local read-only monitoring")
    if st.sidebar.button("Refresh", use_container_width=True):
        st.rerun()
    client = DashboardClient(
        str(settings.operations.dashboard_api_url),
        settings.operations.dashboard_timeout_seconds,
    )
    try:
        snapshot = client.fetch_snapshot()
    except DashboardUnavailableError as error:
        st.title("ToolBridge MCP Operations")
        st.error(str(error))
        st.info("Start the ToolBridge API locally, then refresh this page.")
        return
    render_dashboard(snapshot)


if __name__ == "__main__":
    main()
