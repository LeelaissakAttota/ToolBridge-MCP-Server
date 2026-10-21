"""Interactive Tool Playground and provider-key helpers for the dashboard.

Secrets (MCP token, API keys) are read from env/.env only and never rendered.
"""

from __future__ import annotations

import json
import os
import re
import time
from pathlib import Path
from typing import Any

import httpx
import streamlit as st

from toolbridge.config import get_settings

PROJECT_ROOT = Path(__file__).resolve().parents[2]
ENV_PATH = PROJECT_ROOT / ".env"
REQUESTS_DIR = PROJECT_ROOT / "examples" / "demo-data" / "requests"

EXAMPLE_LABELS = {
    "03_system_status": "System status",
    "04_csv_cafe_orders": "Cafe orders CSV",
    "05_csv_training_scores": "Training scores CSV",
    "06_sql_books_by_genre": "Library: books by genre",
    "07_sql_open_loans": "Library: open loans",
    "08_stock_price": "AAPL stock price",
    "09_currency_usd_to_inr_eur": "100 USD -> INR/EUR",
    "10_website_reader": "Read example.com",
    "11_llm_analyze_feedback": "Analyze customer feedback",
    "12_llm_summarize_notes": "Summarize meeting notes",
}


# ---------------------------------------------------------------- MCP client
def _mcp_url() -> str:
    base = str(get_settings().operations.dashboard_api_url).rstrip("/")
    return f"{base}/mcp/"


def _auth_token() -> str | None:
    token = os.environ.get("TOOLBRIDGE_MCP_AUTH_TOKEN", "").strip()
    if token:
        return token
    value = getattr(get_settings(), "mcp_auth_token_value", None)
    if callable(value):
        value = value()
    return value or None


def _headers() -> dict[str, str]:
    headers = {
        "Accept": "application/json, text/event-stream",
        "Content-Type": "application/json",
    }
    token = _auth_token()
    if token:
        headers["Authorization"] = f"Bearer {token}"
    return headers


def _parse_body(text: str) -> dict[str, Any]:
    if text.lstrip().startswith(("event:", "data:")):
        text = "".join(line[5:] for line in text.splitlines() if line.startswith("data:"))
    return json.loads(text)


def mcp_request(method: str, params: dict[str, Any], timeout: float = 60.0) -> dict[str, Any]:
    payload = {"jsonrpc": "2.0", "id": int(time.time() * 1000), "method": method, "params": params}
    with httpx.Client(timeout=timeout, follow_redirects=False) as client:
        response = client.post(_mcp_url(), headers=_headers(), json=payload)
    if response.status_code == 401:
        raise RuntimeError(
            "Unauthorized (401): MCP auth token mismatch between dashboard and API."
        )
    response.raise_for_status()
    return _parse_body(response.text)


@st.cache_data(ttl=30, show_spinner=False)
def list_tools() -> list[dict[str, Any]]:
    return mcp_request("tools/list", {}, timeout=15).get("result", {}).get("tools", [])


def load_examples() -> dict[str, list[tuple[str, dict[str, Any]]]]:
    examples: dict[str, list[tuple[str, dict[str, Any]]]] = {}
    if not REQUESTS_DIR.is_dir():
        return examples
    for path in sorted(REQUESTS_DIR.glob("[01]*.json")):
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            continue
        if data.get("method") != "tools/call":
            continue
        params = data.get("params", {})
        label = EXAMPLE_LABELS.get(path.stem, path.stem)
        examples.setdefault(params.get("name", ""), []).append(
            (label, params.get("arguments", {}))
        )
    return examples


# ---------------------------------------------------------------- form
def _field_type(spec: dict[str, Any]) -> str:
    kind = spec.get("type")
    if kind is None and "anyOf" in spec:
        kinds = [s.get("type") for s in spec["anyOf"] if s.get("type") != "null"]
        kind = kinds[0] if len(kinds) == 1 else None
        if kind and "enum" not in spec:
            for s in spec["anyOf"]:
                if "enum" in s:
                    spec = {**spec, "enum": s["enum"]}
    if "enum" in spec:
        return "enum"
    return kind if isinstance(kind, str) else "json"


def _render_field(tool: str, name: str, spec: dict[str, Any], required: bool) -> Any:
    key = f"pg_{tool}_{name}"
    label = name + (" *" if required else "")
    help_text = spec.get("description")
    kind = _field_type(spec)
    if kind == "enum":
        options = list(
            spec.get("enum") or next((s["enum"] for s in spec.get("anyOf", []) if "enum" in s), [])
        )
        if not required:
            options = [""] + options
        if st.session_state.get(key) not in options:
            st.session_state[key] = options[0] if options else ""
        value = st.selectbox(label, options, key=key, help=help_text)
        return value if value != "" else None
    if kind == "boolean":
        st.session_state.setdefault(key, bool(spec.get("default", False)))
        return st.checkbox(label, key=key, help=help_text)
    if kind in ("integer", "number"):
        st.session_state.setdefault(
            key, "" if spec.get("default") is None else str(spec["default"])
        )
        raw = st.text_input(label, key=key, help=help_text).strip()
        if not raw:
            return None
        return int(raw) if kind == "integer" else float(raw)
    if kind == "string":
        st.session_state.setdefault(key, spec.get("default") or "")
        long = name in ("text", "query", "instructions", "prompt")
        widget = st.text_area if long else st.text_input
        value = widget(label, key=key, help=help_text)
        return value if value != "" else None
    # arrays / objects / unions -> JSON
    default = spec.get("default")
    st.session_state.setdefault(key, "" if default is None else json.dumps(default))
    raw = st.text_area(f"{label} (JSON)", key=key, help=help_text, height=80).strip()
    if not raw:
        return None
    try:
        return json.loads(raw)
    except ValueError:
        if kind == "array":
            return [part.strip() for part in raw.split(",") if part.strip()]
        raise ValueError(f"Field '{name}' must be valid JSON.")


def _apply_example(tool: str, args: dict[str, Any], schema: dict[str, Any]) -> None:
    for name, spec in schema.get("properties", {}).items():
        key = f"pg_{tool}_{name}"
        value = args.get(name)
        kind = _field_type(spec)
        if kind == "boolean":
            st.session_state[key] = bool(value)
        elif kind in ("integer", "number"):
            st.session_state[key] = "" if value is None else str(value)
        elif kind in ("string", "enum"):
            st.session_state[key] = "" if value is None else str(value)
        else:
            st.session_state[key] = "" if value is None else json.dumps(value)


# ---------------------------------------------------------------- results
def _show_tabular(obj: Any, depth: int = 0) -> None:
    if depth > 2 or not isinstance(obj, dict):
        return
    for name, value in obj.items():
        if isinstance(value, list) and value and all(isinstance(r, dict) for r in value):
            st.markdown(f"**{name}**")
            st.dataframe(value, width="stretch", hide_index=True)
        elif isinstance(value, list) and value and all(isinstance(r, list) for r in value):
            columns = obj.get("columns")
            st.markdown(f"**{name}**")
            if isinstance(columns, list) and all(len(r) == len(columns) for r in value):
                st.dataframe(
                    [dict(zip(columns, r)) for r in value], width="stretch", hide_index=True
                )
            else:
                st.dataframe(value, width="stretch")
        elif isinstance(value, dict):
            _show_tabular(value, depth + 1)


def _show_result(response: dict[str, Any], seconds: float) -> None:
    if "error" in response:
        err = response["error"]
        st.error(f"Request rejected: {err.get('message', err)}")
        st.caption(f"Duration: {seconds * 1000:,.0f} ms")
        with st.expander("Raw JSON-RPC response"):
            st.json(response)
        return
    result = response.get("result", {})
    structured = result.get("structuredContent")
    texts = [c.get("text", "") for c in result.get("content", []) if c.get("type") == "text"]
    if structured is None and len(texts) == 1:
        try:
            structured = json.loads(texts[0])
        except ValueError:
            pass
    if result.get("isError"):
        st.error("Tool error: " + (" ".join(texts)[:2000] or "unknown error"))
    else:
        st.success(f"Success in {seconds * 1000:,.0f} ms")
        if isinstance(structured, dict):
            scalars = {
                k: v
                for k, v in structured.items()
                if isinstance(v, (int, float, bool)) or (isinstance(v, str) and len(v) < 60)
            }
            if scalars:
                cols = st.columns(min(4, len(scalars)))
                for i, (k, v) in enumerate(list(scalars.items())[:8]):
                    cols[i % len(cols)].metric(k, str(v))
            _show_tabular(structured)
            for k, v in structured.items():
                if isinstance(v, str) and len(v) >= 60:
                    st.markdown(f"**{k}**")
                    st.markdown(v)
        elif texts:
            st.markdown("\n\n".join(texts))
    st.caption(f"Duration: {seconds * 1000:,.0f} ms")
    with st.expander("Raw JSON result"):
        st.json(structured if structured is not None else result)


# ---------------------------------------------------------------- page
def render_playground() -> None:
    st.title("Tool Playground")
    st.caption(
        f"Run any ToolBridge tool through the MCP endpoint `{_mcp_url()}` "
        "(JSON-RPC tools/call). Runs appear in History and Logs."
    )
    try:
        tools = list_tools()
    except Exception as error:  # noqa: BLE001
        st.error(f"Cannot load tools from the MCP API: {error}")
        st.info("Start the ToolBridge API, then press Refresh in the sidebar.")
        return
    if not tools:
        st.warning("The MCP server returned no tools.")
        return

    by_name = {t["name"]: t for t in tools}
    tool_name = st.selectbox("Tool", list(by_name), key="pg_tool")
    tool = by_name[tool_name]
    schema = tool.get("inputSchema", {}) or {}
    if tool.get("description"):
        st.caption(tool["description"])

    examples = load_examples().get(tool_name, [])
    if examples:
        st.markdown("**Examples (demo data)**")
        cols = st.columns(min(4, len(examples)))
        for i, (label, args) in enumerate(examples):
            if cols[i % len(cols)].button(label, key=f"pg_ex_{tool_name}_{i}", width="stretch"):
                _apply_example(tool_name, args, schema)
                st.session_state["pg_autorun"] = tool_name
                st.rerun()

    required = set(schema.get("required", []))
    arguments: dict[str, Any] = {}
    form_error = None
    with st.container(border=True):
        props = schema.get("properties", {})
        if not props:
            st.caption("This tool takes no arguments.")
        for name, spec in props.items():
            try:
                value = _render_field(tool_name, name, spec, name in required)
            except ValueError as error:
                form_error = str(error)
                continue
            if value is not None:
                arguments[name] = value
        run = st.button("Run tool", type="primary", key=f"pg_run_{tool_name}")

    autorun = st.session_state.pop("pg_autorun", None) == tool_name
    if run or autorun:
        if form_error:
            st.error(form_error)
            return
        with st.expander("Request arguments"):
            st.json(arguments)
        start = time.perf_counter()
        with st.spinner(f"Running {tool_name}..."):
            try:
                response = mcp_request("tools/call", {"name": tool_name, "arguments": arguments})
            except Exception as error:  # noqa: BLE001
                st.error(f"Call failed: {error}")
                return
        _show_result(response, time.perf_counter() - start)


# ---------------------------------------------------------------- .env keys
def provider_key_vars() -> dict[str, str]:
    settings = get_settings()
    found = {}
    for name in type(settings).model_fields:
        sub = getattr(settings, name, None)
        if hasattr(sub, "api_key"):
            found[name] = f"TOOLBRIDGE_{name.upper()}__API_KEY"
        for inner in getattr(type(sub), "model_fields", {}) if sub is not None else {}:
            if hasattr(getattr(sub, inner, None), "api_key"):
                found[f"{name}.{inner}"] = f"TOOLBRIDGE_{name.upper()}__{inner.upper()}__API_KEY"
    return found


def env_var_is_set(var: str) -> bool:
    if os.environ.get(var, "").strip():
        return True
    if ENV_PATH.is_file():
        for line in ENV_PATH.read_text(encoding="utf-8").splitlines():
            key, sep, value = line.partition("=")
            if sep and key.strip() == var and value.strip().strip("'\""):
                return True
    return False


def write_env_var(var: str, value: str) -> None:
    if not re.fullmatch(r"[A-Z][A-Z0-9_]*", var):
        raise ValueError("Invalid variable name.")
    if "\n" in value or "\r" in value:
        raise ValueError("Value must be a single line.")
    lines = ENV_PATH.read_text(encoding="utf-8").splitlines() if ENV_PATH.is_file() else []
    new_line = f"{var}={value}"
    for i, line in enumerate(lines):
        if line.partition("=")[0].strip() == var and not line.lstrip().startswith("#"):
            lines[i] = new_line
            break
    else:
        lines.append(new_line)
    tmp = ENV_PATH.parent / ".env.tmp"
    tmp.write_text("\n".join(lines) + "\n", encoding="utf-8")
    os.replace(tmp, ENV_PATH)


def render_key_manager() -> None:
    with st.container(border=True):
        st.subheader("Add / update provider API key")
        st.caption("Keys are saved to the project .env file and never displayed.")
        known = provider_key_vars()
        rows = [
            {"Provider": p, "Variable": v, "Key": "set" if env_var_is_set(v) else "not set"}
            for p, v in known.items()
        ]
        if rows:
            st.dataframe(rows, width="stretch", hide_index=True)
        custom = "Custom (new provider)..."
        choice = st.selectbox("Provider", list(known) + [custom], key="km_provider")
        if choice == custom:
            raw = st.text_input("Custom provider name (e.g. groq)", key="km_custom").strip()
            var = (
                f"TOOLBRIDGE_{re.sub(r'[^A-Za-z0-9]+', '_', raw).upper()}__API_KEY" if raw else ""
            )
            st.caption("Custom keys are stored, but only built-in providers are used by the API.")
        else:
            var = known[choice]
        if var:
            st.caption(f"Variable: `{var}`")
        with st.form("km_form", clear_on_submit=True):
            secret = st.text_input("API key", type="password")
            saved = st.form_submit_button("Save key", type="primary")
        if saved:
            if not var or not secret.strip():
                st.error("Choose a provider and enter a key.")
            else:
                try:
                    write_env_var(var, secret.strip())
                except (OSError, ValueError) as error:
                    st.error(f"Could not save: {error}")
                else:
                    st.success(f"Saved {var}. Restart the ToolBridge API to apply it.")
