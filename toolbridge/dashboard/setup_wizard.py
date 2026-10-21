"""Guided LLM provider setup for the Settings page. Keys are never displayed."""

from __future__ import annotations

from dataclasses import dataclass, field

import httpx
import streamlit as st

from toolbridge.dashboard.playground import ENV_PATH, env_var_is_set, write_env_var

AUTO = "Auto (cheapest)"


@dataclass(frozen=True)
class Preset:
    label: str
    name: str
    base_url: str
    key_help: str
    cheap_models: tuple[str, ...]  # cheapest first; used as fallback list
    legacy_prefix: str | None = None  # built-in providers use TOOLBRIDGE_<NAME>__
    extras: dict[str, str] = field(default_factory=dict)  # env suffix -> label


PRESETS = (
    Preset(
        "OpenRouter",
        "openrouter",
        "https://openrouter.ai/api/v1",
        "Get a key at https://openrouter.ai/keys",
        ("meta-llama/llama-3.1-8b-instruct", "google/gemini-2.5-flash-lite", "openai/gpt-4o-mini"),
        legacy_prefix="TOOLBRIDGE_OPENROUTER__",
        extras={"APP_TITLE": "App name (optional)", "HTTP_REFERER": "Site URL (optional)"},
    ),
    Preset(
        "OpenAI",
        "openai",
        "https://api.openai.com/v1",
        "Get a key at https://platform.openai.com/api-keys",
        ("gpt-4.1-nano", "gpt-4o-mini", "gpt-4.1-mini"),
    ),
    Preset(
        "Anthropic",
        "anthropic",
        "https://api.anthropic.com/v1",
        "Get a key at https://console.anthropic.com/settings/keys",
        ("claude-3-5-haiku-latest", "claude-haiku-4-5"),
    ),
    Preset(
        "Google Gemini",
        "gemini",
        "https://generativelanguage.googleapis.com/v1beta/openai",
        "Get a key at https://aistudio.google.com/apikey",
        ("gemini-2.5-flash-lite", "gemini-2.0-flash-lite", "gemini-2.5-flash"),
    ),
    Preset(
        "Groq",
        "groq",
        "https://api.groq.com/openai/v1",
        "Get a key at https://console.groq.com/keys",
        ("llama-3.1-8b-instant", "llama-3.3-70b-versatile"),
    ),
    Preset(
        "Cerebras",
        "cerebras",
        "https://api.cerebras.ai/v1",
        "Get a key at https://cloud.cerebras.ai",
        ("llama3.1-8b",),
        legacy_prefix="TOOLBRIDGE_CEREBRAS__",
    ),
    Preset(
        "NVIDIA",
        "nvidia",
        "https://integrate.api.nvidia.com/v1",
        "Get a key at https://build.nvidia.com",
        ("meta/llama-3.1-8b-instruct",),
        legacy_prefix="TOOLBRIDGE_NVIDIA__",
    ),
    Preset(
        "Custom OpenAI-compatible",
        "custom",
        "https://",
        "Any server exposing /chat/completions over HTTPS",
        (),
    ),
)


def _prefix(p: Preset) -> str:
    return p.legacy_prefix or f"TOOLBRIDGE_PROVIDERS__{p.name.upper()}__"


def _env_value(var: str) -> str | None:
    """Read a NON-secret value from .env (never used for API keys in the UI)."""
    if ENV_PATH.is_file():
        for line in ENV_PATH.read_text(encoding="utf-8").splitlines():
            k, sep, v = line.partition("=")
            if sep and k.strip() == var:
                return v.strip().strip("'\"") or None
    return None


def _read_key(var: str) -> str | None:
    return _env_value(var)  # used only server-side for Test connection


@st.cache_data(ttl=3600, show_spinner=False)
def openrouter_prices() -> dict[str, float]:
    """Public OpenRouter /models pricing: model id -> USD per 1M (input+output)."""
    try:
        data = httpx.get("https://openrouter.ai/api/v1/models", timeout=15).json()["data"]
    except Exception:  # noqa: BLE001
        return {}
    prices = {}
    for item in data:
        try:
            p = item.get("pricing") or {}
            total = (float(p.get("prompt", 0)) + float(p.get("completion", 0))) * 1_000_000
        except (TypeError, ValueError):
            continue
        if total >= 0:
            prices[item["id"]] = total
    return prices


def auto_candidates(p: Preset) -> list[str]:
    """Cheapest-first candidate list for Auto mode."""
    models = list(p.cheap_models)
    if p.name == "openrouter":
        prices = openrouter_prices()
        if prices:
            known = [m for m in models if m in prices]
            known.sort(key=lambda m: prices[m])
            models = known + [m for m in models if m not in known]
    return models


def test_connection(
    base_url: str, key: str, model: str, extra: dict[str, str]
) -> tuple[bool, str]:
    headers = {"Authorization": f"Bearer {key}", "Content-Type": "application/json"}
    if extra.get("APP_TITLE"):
        headers["X-OpenRouter-Title"] = extra["APP_TITLE"]
    body = {"model": model, "messages": [{"role": "user", "content": "ping"}], "max_tokens": 5}
    try:
        r = httpx.post(
            base_url.rstrip("/") + "/chat/completions", headers=headers, json=body, timeout=30
        )
    except httpx.HTTPError as error:
        return False, f"network error ({type(error).__name__})"
    if r.status_code == 200:
        return True, "OK"
    msg = ""
    try:
        err = r.json().get("error", {})
        msg = err.get("message", "") if isinstance(err, dict) else str(err)
    except ValueError:
        pass
    msg = msg.replace(key, "***")[:200]
    return False, f"HTTP {r.status_code} {msg}".strip()


def _pick_working(
    p: Preset, base: str, key: str, models: list[str], extra: dict[str, str]
) -> tuple[str | None, list[str]]:
    notes = []
    for m in models:
        ok, msg = test_connection(base, key, m, extra)
        notes.append(f"{m}: {msg}")
        if ok:
            return m, notes
        if msg.startswith("HTTP 401") or msg.startswith("HTTP 403"):
            break
    return None, notes


def render_provider_setup() -> None:
    with st.container(border=True):
        st.subheader("LLM provider setup (guided)")
        st.caption(
            "Keys are saved to the project .env and never shown again. "
            "Status below shows only set / not set."
        )
        rows = []
        priority = (_env_value("TOOLBRIDGE_PROVIDER_PRIORITY") or "").split(",")
        for p in PRESETS:
            pre = _prefix(p)
            rows.append(
                {
                    "Provider": p.label,
                    "Key": "set" if env_var_is_set(pre + "API_KEY") else "not set",
                    "Enabled": _env_value(pre + "ENABLED") or "false",
                    "Model": _env_value(pre + "DEFAULT_MODEL") or "-",
                    "Active for llm_analysis": "yes" if priority[:1] == [p.name] else "",
                }
            )
        st.dataframe(rows, width="stretch", hide_index=True)

        labels = [p.label for p in PRESETS]
        p = PRESETS[labels.index(st.selectbox("Provider", labels, key="ps_provider"))]
        pre = _prefix(p)
        st.info(p.key_help)
        key_set = env_var_is_set(pre + "API_KEY")
        new_key = st.text_input(
            "API key" + (" (already set - leave empty to keep)" if key_set else ""),
            type="password",
            key=f"ps_key_{p.name}",
        )
        base = st.text_input(
            "Base URL", value=_env_value(pre + "BASE_URL") or p.base_url, key=f"ps_base_{p.name}"
        )
        cands = auto_candidates(p)
        mode_opts = ([AUTO] if cands else []) + ["Manual"]
        mode = st.radio("Model selection", mode_opts, horizontal=True, key=f"ps_mode_{p.name}")
        if mode == AUTO:
            st.caption("Auto picks the cheapest working model, in order: " + ", ".join(cands))
            manual = None
        else:
            manual = st.text_input(
                "Model id",
                value=_env_value(pre + "DEFAULT_MODEL") or (cands[0] if cands else ""),
                key=f"ps_model_{p.name}",
            ).strip()
        extra = {}
        for suffix, label in p.extras.items():
            extra[suffix] = st.text_input(
                label, value=_env_value(pre + suffix) or "", key=f"ps_{suffix}_{p.name}"
            ).strip()
        make_active = st.checkbox(
            "Use this provider for llm_analysis (make active/default)",
            value=True,
            key=f"ps_active_{p.name}",
        )

        c1, c2 = st.columns(2)
        do_test = c1.button("Test connection", key=f"ps_test_{p.name}", width="stretch")
        do_save = c2.button(
            "Save & enable", type="primary", key=f"ps_save_{p.name}", width="stretch"
        )
        if not (do_test or do_save):
            return
        key = new_key.strip() or (_read_key(pre + "API_KEY") or "")
        if not key:
            st.error("Enter an API key first.")
            return
        if not base.startswith("https://") or base == "https://":
            st.error("Base URL must be a full HTTPS URL.")
            return
        models = [manual] if manual else cands
        if not models:
            st.error("Enter a model id.")
            return
        with st.spinner("Testing with a tiny request..."):
            chosen, notes = _pick_working(p, base, key, models, extra)
        if chosen:
            st.success(f"Connection OK - model `{chosen}`")
        else:
            st.error("Connection failed")
        with st.expander("Test details"):
            for n in notes:
                st.text(n)
        if do_save:
            if not chosen:
                st.warning("Not saved because the test failed. Fix the key/model and retry.")
                return
            if new_key.strip():
                write_env_var(pre + "API_KEY", new_key.strip())
            write_env_var(pre + "BASE_URL", base.strip())
            write_env_var(pre + "DEFAULT_MODEL", chosen)
            write_env_var(pre + "ENABLED", "true")
            for suffix, value in extra.items():
                if value:
                    write_env_var(pre + suffix, value)
            if make_active:
                rest = [x for x in priority if x and x != p.name]
                write_env_var("TOOLBRIDGE_PROVIDER_PRIORITY", ",".join([p.name, *rest]))
            st.success(
                f"Saved {p.label} (model {chosen}). RESTART the ToolBridge API "
                "(Ctrl+C in its window, then start it again) so llm_analysis uses it."
            )
