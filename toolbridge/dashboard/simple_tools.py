"""Simplified Playground panels for CSV, LLM analysis (text/audio) and SQL (plain language)."""

from __future__ import annotations

import re
import sqlite3
import tempfile
from pathlib import Path
from typing import Any

import streamlit as st

from toolbridge.config import get_settings

PROJECT_ROOT = Path(__file__).resolve().parents[2]
DEMO_CSV = PROJECT_ROOT / "examples" / "demo-data" / "csv"
DEMO_DB = PROJECT_ROOT / "examples" / "demo-data" / "sql" / "demo_library.db"
AUDIO_TYPES = ["mp3", "wav", "m4a", "ogg"]
SQL_EXAMPLES = (
    "How many books per genre?",
    "Show open loans with borrower and due date",
    "Which books were borrowed most?",
)
_FORBIDDEN = re.compile(
    r"\b(insert|update|delete|drop|alter|create|replace|attach|detach|pragma|vacuum|"
    r"reindex|truncate|grant|revoke)\b",
    re.IGNORECASE,
)


def _phase5(name: str) -> Any:
    return getattr(getattr(get_settings(), "phase5", None), name, None)


def _resolve(value: Any) -> Path | None:
    if not value:
        return None
    path = Path(str(value))
    return path if path.is_absolute() else PROJECT_ROOT / path


# ------------------------------------------------------------------ CSV
def csv_root_candidates() -> list[Path]:
    roots = [_resolve(getattr(_phase5("csv_analysis"), "root_directory", None)), DEMO_CSV]
    seen, out = set(), []
    for r in roots:
        if r and r.is_dir() and r.resolve() not in seen:
            seen.add(r.resolve())
            out.append(r)
    # The configured root comes first so the dashboard matches the API by default;
    # the bundled demo folder is only offered as a fallback.
    return out


def safe_filename(name: str) -> str:
    stem = re.sub(r"[^A-Za-z0-9_.-]+", "_", Path(name).stem).strip("._") or "upload"
    return f"{stem[:80]}.csv"


def save_upload(root: Path, name: str, data: bytes) -> Path:
    """Save into root without overwriting: adds _1, _2... unless identical content."""
    target = root / safe_filename(name)
    n = 1
    while target.exists():
        if target.read_bytes() == data:
            return target
        target = root / f"{Path(safe_filename(name)).stem}_{n}.csv"
        n += 1
    target.write_bytes(data)
    return target


def render_csv(call) -> None:
    roots = csv_root_candidates()
    if not roots:
        st.error("No CSV folder found. Check TOOLBRIDGE_PHASE5__CSV_ANALYSIS__ROOT_DIRECTORY.")
        return
    root = roots[0]
    if len(roots) > 1:
        root = Path(
            st.selectbox(
                "CSV folder (must match the API's CSV root)",
                [str(r) for r in roots],
                key="csv_root",
            )
        )
    if (root / "cafe_orders.csv").exists() and st.button("Example: Cafe orders CSV", key="csv_ex"):
        st.session_state["csv_file"] = "cafe_orders.csv"
        st.session_state["csv_autorun"] = True
    files = sorted(p.name for p in root.glob("*.csv"))
    st.markdown("**Select / upload CSV file**")
    c1, c2 = st.columns(2)
    if st.session_state.get("csv_file") not in files:
        st.session_state["csv_file"] = files[0] if files else None
    chosen = c1.selectbox("Existing file", files, key="csv_file")
    upload = c2.file_uploader("Upload a CSV", type=["csv"], key="csv_upload")
    with st.expander("Advanced"):
        preview = st.number_input("Preview rows", 1, 100, 5, key="csv_preview")
    run_name = None
    if upload is not None and st.session_state.get("csv_last_upload") != upload.file_id:
        saved = save_upload(root, upload.name, upload.getvalue())
        st.session_state["csv_last_upload"] = upload.file_id
        st.success(f"Saved as `{saved.name}` in the CSV folder.")
        run_name = saved.name
    if st.button("Analyze CSV", type="primary", key="csv_run") or st.session_state.pop(
        "csv_autorun", False
    ):
        run_name = chosen
    if not run_name:
        return
    result, seconds = call(
        "csv_analysis", {"relative_path": run_name, "preview_rows": int(preview)}
    )
    if result is None:
        return
    m = st.columns(4)
    m[0].metric("File", result.get("file_name", run_name))
    m[1].metric("Rows", result.get("row_count", 0))
    m[2].metric("Columns", len(result.get("columns", [])))
    m[3].metric("Time", f"{seconds * 1000:,.0f} ms")
    summaries = result.get("summaries", [])
    if summaries:
        st.markdown("**Schema**")
        st.dataframe(
            [
                {
                    "column": s["name"],
                    "type": s["inferred_type"],
                    "non-null": s["non_null_count"],
                    "unique": s["unique_count"],
                    "min": s.get("minimum"),
                    "max": s.get("maximum"),
                    "mean": s.get("mean"),
                }
                for s in summaries
            ],
            width="stretch",
            hide_index=True,
        )
        missing = [
            {"column": s["name"], "missing": s["missing_count"]}
            for s in summaries
            if s["missing_count"]
        ]
        st.markdown("**Missing values**")
        if missing:
            st.dataframe(missing, width="stretch", hide_index=True)
        else:
            st.caption("No missing values.")
    if result.get("preview"):
        st.markdown("**Preview**")
        st.dataframe(result["preview"], width="stretch", hide_index=True)
    with st.expander("Raw JSON"):
        st.json(result)


# ------------------------------------------------------------------ audio
@st.cache_resource(show_spinner="Loading the local speech-to-text model (first time only)...")
def _whisper():
    from faster_whisper import WhisperModel  # local, free, CPU

    return WhisperModel("base", device="cpu", compute_type="int8")


def transcribe(data: bytes, suffix: str) -> str:
    with tempfile.NamedTemporaryFile(suffix=f".{suffix}", delete=False) as tmp:
        tmp.write(data)
        path = tmp.name
    try:
        segments, _info = _whisper().transcribe(path, vad_filter=True)
        return " ".join(s.text.strip() for s in segments).strip()
    finally:
        Path(path).unlink(missing_ok=True)


def render_llm(call) -> None:
    examples = {
        "Example: Analyze customer feedback": (
            "analyze",
            "customer_feedback.txt",
            "List the top 3 complaints and top 2 compliments.",
        ),
        "Example: Summarize meeting notes": ("summarize", "meeting_notes.txt", ""),
    }
    cols = st.columns(len(examples))
    for i, (label, (op, fname, instr)) in enumerate(examples.items()):
        if cols[i].button(label, key=f"llm_ex_{i}", width="stretch"):
            path = PROJECT_ROOT / "examples" / "demo-data" / "text" / fname
            st.session_state["llm_text"] = path.read_text(encoding="utf-8")
            st.session_state["llm_op"] = op
            st.session_state["llm_instr"] = instr
            st.session_state["llm_src"] = "Type text"
    source = st.radio("Input", ["Type text", "Upload file"], horizontal=True, key="llm_src")
    if source == "Upload file":
        up = st.file_uploader(
            "Text (.txt, .md) or audio (.mp3, .wav, .m4a, .ogg)",
            type=["txt", "md", *AUDIO_TYPES],
            key="llm_upload",
        )
        if up is not None and st.session_state.get("llm_last_upload") != up.file_id:
            suffix = up.name.rsplit(".", 1)[-1].lower()
            if suffix in AUDIO_TYPES:
                try:
                    with st.spinner("Transcribing audio locally..."):
                        st.session_state["llm_text"] = transcribe(up.getvalue(), suffix)
                    st.success("Transcribed with local faster-whisper (base).")
                except Exception as error:  # noqa: BLE001
                    st.error(f"Transcription failed: {type(error).__name__}: {error}")
            else:
                st.session_state["llm_text"] = up.getvalue().decode("utf-8", errors="replace")
            st.session_state["llm_last_upload"] = up.file_id
    st.session_state.setdefault("llm_text", "")
    text = st.text_area("Text / transcript", key="llm_text", height=200)
    c1, c2 = st.columns([1, 3])
    op = c1.selectbox("Operation", ["analyze", "summarize"], key="llm_op")
    instructions = c2.text_input("Instructions (optional)", key="llm_instr")
    if not st.button("Run analysis", type="primary", key="llm_run"):
        return
    if not text.strip():
        st.error("Type some text or upload a file first.")
        return
    args: dict[str, Any] = {"operation": op, "text": text}
    if instructions.strip():
        args["instructions"] = instructions.strip()
    result, seconds = call("llm_analysis", args)
    if result is None:
        return
    st.markdown(result.get("content", ""))
    st.caption(
        f"Model: {result.get('model')} ({result.get('provider')}) | "
        f"{result.get('total_tokens', 0)} tokens | {seconds * 1000:,.0f} ms"
        + (
            f" | {result['model_selection_reason']}"
            if result.get("model_selection_reason")
            else ""
        )
    )
    with st.expander("Raw JSON"):
        st.json(result)


# ------------------------------------------------------------------ SQL
def db_candidates() -> list[Path]:
    cfg = _phase5("sql_query")
    if str(getattr(cfg, "backend", "sqlite") or "sqlite") == "postgres":
        return []
    root = _resolve(getattr(cfg, "database_root", None))
    configured = getattr(cfg, "database_path", None)
    paths = []
    if configured:
        p = Path(str(configured))
        paths.append(p if p.is_absolute() else (root or PROJECT_ROOT) / p)
    # Configured database first (what the API queries); bundled demo DB as fallback.
    paths.append(DEMO_DB)
    seen, out = set(), []
    for p in paths:
        if p.is_file() and p.resolve() not in seen:
            seen.add(p.resolve())
            out.append(p)
    return out


def read_schema(db: Path) -> str:
    con = sqlite3.connect(f"file:{db.as_posix()}?mode=ro", uri=True)
    try:
        lines = []
        for (table,) in con.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%'"
        ):
            cols = ", ".join(
                f"{r[1]} {r[2]}" for r in con.execute(f'PRAGMA table_info("{table}")')
            )
            lines.append(f"{table}({cols})")
        return "\n".join(lines)
    finally:
        con.close()


def extract_sql(text: str) -> str:
    block = re.search(r"```(?:sql)?\s*(.+?)```", text, re.IGNORECASE | re.DOTALL)
    candidate = block.group(1) if block else text
    match = re.search(r"\b(SELECT|WITH)\b.+", candidate, re.IGNORECASE | re.DOTALL)
    sql = (match.group(0) if match else candidate).strip()
    return sql.split(";")[0].strip()


def validate_select(sql: str) -> str | None:
    s = sql.strip().rstrip(";").strip()
    if not s:
        return "SQL is empty."
    if ";" in s:
        return "Only one statement is allowed."
    if not re.match(r"^(SELECT|WITH)\b", s, re.IGNORECASE):
        return "Only SELECT queries are allowed."
    if _FORBIDDEN.search(s):
        return "The query contains a write/admin keyword; only read-only SELECT is allowed."
    return None


def render_sql(call) -> None:
    cfg = _phase5("sql_query")
    backend = str(getattr(cfg, "backend", "sqlite") or "sqlite")
    dbs = db_candidates()
    schema = ""
    if backend == "postgres":
        st.caption(
            "Queries run on the configured PostgreSQL read-only role. "
            "Local schema preview is available for SQLite only."
        )
    elif dbs:
        db = dbs[0]
        if len(dbs) > 1:
            db = Path(
                st.selectbox(
                    "Database (must match the API's database)", [str(d) for d in dbs], key="sql_db"
                )
            )
        try:
            schema = read_schema(db)
        except sqlite3.Error as error:
            st.warning(f"Could not read schema: {error}")
        with st.expander("Database schema"):
            st.code(schema or "(unknown)")
    st.session_state.setdefault("sql_question", "")
    question = st.text_input("Ask in plain language", key="sql_question")
    examples = SQL_EXAMPLES if "CREATE TABLE books" in schema else ()
    cols = st.columns(len(examples)) if examples else []
    for i, ex in enumerate(examples):
        if cols[i].button(ex, key=f"sql_ex_{i}", width="stretch"):
            st.session_state["sql_question"] = ex
            st.rerun()
    if st.button("Generate SQL", type="primary", key="sql_gen") and question.strip():
        prompt = (
            f"{'PostgreSQL' if backend == 'postgres' else 'SQLite'} schema:\n{schema}\n\n"
            f"Question: {question.strip()}\n"
            "Write ONE read-only SELECT query answering the question."
        )
        result, _ = call(
            "llm_analysis",
            {
                "operation": "analyze",
                "text": prompt,
                "instructions": "Reply with only the SQL in a ```sql code block. No explanation. "
                "Use only the tables and columns in the schema.",
            },
            quiet=True,
        )
        if result is not None:
            st.session_state["sql_generated"] = extract_sql(result.get("content", ""))
            st.session_state["sql_model"] = result.get("model")
    if st.session_state.get("sql_generated") is not None:
        st.session_state.setdefault("sql_edit", "")
        if st.session_state.get("sql_generated_shown") != st.session_state["sql_generated"]:
            st.session_state["sql_edit"] = st.session_state["sql_generated"]
            st.session_state["sql_generated_shown"] = st.session_state["sql_generated"]
        st.caption(f"Generated by {st.session_state.get('sql_model')} - you can edit it.")
        sql = st.text_area("Generated SQL", key="sql_edit", height=110)
        if st.button("Run query", key="sql_run_gen"):
            _run_sql(call, sql)
    with st.expander("Write SQL manually"):
        manual = st.text_area("SQL (SELECT only)", key="sql_manual", height=110)
        if st.button("Run manual SQL", key="sql_run_manual"):
            _run_sql(call, manual)


def _run_sql(call, sql: str) -> None:
    problem = validate_select(sql)
    if problem:
        st.error(problem)
        return
    result, seconds = call("sql_query", {"query": sql.strip().rstrip(";"), "parameters": {}})
    if result is None:
        return
    columns, rows = result.get("columns", []), result.get("rows", [])
    st.success(f"{result.get('row_count', len(rows))} rows in {seconds * 1000:,.0f} ms")
    if rows and isinstance(rows[0], list):
        rows = [dict(zip(columns, r, strict=False)) for r in rows]
    st.dataframe(rows, width="stretch", hide_index=True)
    with st.expander("Raw JSON"):
        st.json(result)


SIMPLE_RENDERERS = {
    "csv_analysis": render_csv,
    "llm_analysis": render_llm,
    "sql_query": render_sql,
}
