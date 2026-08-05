# ToolBridge MCP Server

ToolBridge is a Model Context Protocol (MCP) service that exposes typed, validated, observable tools through a single transport. Version `0.2.0` completes Phase 2: the original FastAPI/FastMCP foundation now runs through a framework-independent MCP Core.

Phase 3 has not started. Production data tools, provider routing, agent orchestration, persistence, authentication, the dashboard, and deployment packaging remain planned work.

## Current capabilities

- FastAPI control plane and generated OpenAPI documentation
- Stateless MCP Streamable HTTP transport using JSON responses
- Clean Architecture separation between core services and framework adapters
- Immutable typed tool definitions and deterministic registry discovery
- Strict request and per-tool argument validation
- Validated, size-bounded structured responses
- Tool execution with per-tool timeouts and cancellation propagation
- Stable error categories with safe client messages and correlation identifiers
- JSON execution lifecycle logs that exclude arguments, results, and exception messages
- One MCP diagnostic tool: `system_status`
- Automated unit, API, and MCP protocol tests

## Prerequisites

- Python 3.12
- Windows PowerShell commands are shown below
- Internet access for the initial dependency installation

## Setup

```powershell
py -3.12 -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
Copy-Item .env.example .env
python -m pytest
```

The `.env` copy is optional because development defaults are built in. Local `.env` files are ignored by Git.

## Run locally

```powershell
.\.venv\Scripts\Activate.ps1
python -m uvicorn toolbridge.main:app --host 127.0.0.1 --port 8000
```

| Purpose | URL |
| --- | --- |
| Service metadata | <http://127.0.0.1:8000/> |
| Health check | <http://127.0.0.1:8000/health> |
| OpenAPI documentation | <http://127.0.0.1:8000/docs> |
| MCP Streamable HTTP | `http://127.0.0.1:8000/mcp/` |

The trailing slash on the MCP URL is intentional.

## MCP Core flow

1. FastMCP implements the Streamable HTTP protocol and discovers registered tools.
2. The MCP adapter enforces strict generated input schemas and delegates calls.
3. The executor validates the common request and resolves the tool through the registry.
4. The selected Pydantic input model validates all arguments and forbids extras.
5. The handler runs within its timeout and cancellation boundary.
6. The declared output model validates the result and enforces the response-size limit.
7. The adapter returns structured MCP content or a safe normalized error.
8. Structured lifecycle events record tool name, correlation ID, duration, and outcome only.

## Configuration

| Variable | Default | Purpose |
| --- | --- | --- |
| `TOOLBRIDGE_APP_NAME` | `ToolBridge MCP Server` | Displayed service and MCP name |
| `TOOLBRIDGE_ENVIRONMENT` | `development` | Runtime environment label |
| `TOOLBRIDGE_HOST` | `127.0.0.1` | Intended bind host |
| `TOOLBRIDGE_PORT` | `8000` | Intended bind port |
| `TOOLBRIDGE_LOG_LEVEL` | `INFO` | MCP Core execution log level |
| `TOOLBRIDGE_TOOL_TIMEOUT_SECONDS` | `30` | Default per-tool timeout, maximum 300 seconds |
| `TOOLBRIDGE_MAX_REQUEST_BYTES` | `65536` | Maximum encoded core execution request size |
| `TOOLBRIDGE_MAX_RESPONSE_BYTES` | `262144` | Maximum encoded structured result size |

Host and port are modeled in settings, but the current launch command still passes them directly to Uvicorn.

## Project layout

```text
ToolBridge MCP Server/
├── toolbridge/
│   ├── adapters/
│   │   ├── logging.py       Safe structured logging adapter
│   │   └── mcp.py           FastMCP discovery/execution adapter
│   ├── core/
│   │   ├── contracts.py     Tool, request, response, metadata, and error contracts
│   │   ├── errors.py        Normalized core exceptions
│   │   ├── executor.py      Timeout-aware validated execution service
│   │   ├── ports.py         Infrastructure-facing protocols
│   │   ├── registry.py      Registration, lookup, and discovery
│   │   └── validation.py    Request, argument, and response validation
│   ├── tools/
│   │   ├── definitions.py   `system_status` core contract
│   │   └── system.py        Original diagnostic implementation
│   ├── bootstrap.py         MCP Core composition
│   ├── config.py            Typed environment settings
│   └── main.py              FastAPI/FastMCP composition root and Phase 1 routes
├── tests/
│   ├── unit/                MCP Core and adapter unit tests
│   └── test_api.py          HTTP and full MCP protocol tests
├── .env.example             Safe configuration example
├── .python-version          Python 3.12 selection
└── requirements.txt         Pinned direct dependencies
```

## Tests

```powershell
python -m pytest -q -p no:cacheprovider
python -m pip check
```

The Phase 2 suite currently contains 28 passing tests. A third-party deprecation warning is emitted by FastAPI/Starlette's current `TestClient` integration.

## Documentation

- [Project status dashboard](PROJECT_STATUS.md)
- [Project rules](PROJECT_RULES.md)
- [Roadmap](ROADMAP.md)
- [Architecture](ARCHITECTURE.md)
- [Task register](TASKS.md)
- [Changelog](CHANGELOG.md)
- [Coding standards](CODING_STANDARDS.md)
- [Testing strategy](TESTING_STRATEGY.md)
- [Git workflow](GIT_WORKFLOW.md)
- [Deployment plan](DEPLOYMENT_PLAN.md)
- [Security guidelines](SECURITY_GUIDELINES.md)
- [Decision log](DECISIONS.md)

## Project status

Phases 1 and 2 are complete and locally verified. Phase 3 remains blocked on explicit owner approval. See [PROJECT_STATUS.md](PROJECT_STATUS.md) for the current snapshot and [TASKS.md](TASKS.md) for remaining work.

## License

No license has been selected. Until one is added, no permission to copy, modify, or redistribute the project is granted by default.
