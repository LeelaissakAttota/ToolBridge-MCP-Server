"""The opt-in live smoke script must target a configurable endpoint."""

import importlib.util
from pathlib import Path

SCRIPT = Path(__file__).resolve().parents[1] / "live" / "mcp_live_smoke.py"


def _load():
    spec = importlib.util.spec_from_file_location("mcp_live_smoke", SCRIPT)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_smoke_defaults_to_local_port_8000() -> None:
    arguments = _load().parse_args([], environ={})

    assert arguments.url == "http://127.0.0.1:8000/mcp/"
    assert arguments.token is None
    assert arguments.analysis is False


def test_smoke_port_and_host_flags_build_url() -> None:
    arguments = _load().parse_args(["--port", "8765", "--host", "localhost"], environ={})

    assert arguments.url == "http://localhost:8765/mcp/"


def test_smoke_reads_environment_and_url_override() -> None:
    module = _load()

    from_env = module.parse_args(
        [], environ={"TOOLBRIDGE_SMOKE_PORT": "9001", "TOOLBRIDGE_MCP_AUTH_TOKEN": "t"}
    )
    explicit = module.parse_args(
        ["--url", "http://10.0.0.2:7000/mcp/"], environ={"TOOLBRIDGE_SMOKE_PORT": "9001"}
    )

    assert from_env.url == "http://127.0.0.1:9001/mcp/"
    assert from_env.token == "t"
    assert explicit.url == "http://10.0.0.2:7000/mcp/"
