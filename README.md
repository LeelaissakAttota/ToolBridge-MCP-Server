# ToolBridge MCP Server

ToolBridge is a Python 3.12 Model Context Protocol service with typed, validated, observable, read-only tools. Version `0.6.0` completes the approved Phase 6 Dashboard & Production Readiness scope while preserving all Phase 1-5 application behavior.

Phase 6 is implemented and tested but is intentionally uncommitted and unpushed pending project-owner approval. Authentication, agents, CI/CD, deployment pipelines, and Phase 7 work are not implemented.

## Current capabilities

- FastAPI control plane and stateless FastMCP Streamable HTTP transport
- Framework-independent MCP contracts, registry, discovery, strict validation, bounded execution, safe errors, and structured logs
- Configuration-driven LLM Provider Router for Cerebras, NVIDIA, and OpenRouter
- Seven tools: `system_status`, `stock_price`, `website_reader`, `sql_query`, `csv_analysis`, `currency_converter`, and `hcl_curie_analysis`
- Common `BaseTool` and `ToolManager` lifecycle with automatic MCP registration
- Liveness, readiness, startup validation, graceful shutdown, and safe operational snapshots
- Process-local tool/provider timing, request outcomes, token usage, configured cost estimates, error categories, and bounded recent logs
- Read-only Streamlit dashboard for system, provider, tool, metrics, cost, and log views
- Offline automated suite with 112 tests

## Setup

```powershell
py -3.12 -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
Copy-Item .env.example .env
python -m pytest -q -p no:cacheprovider tests
python -m pip check
```

The `.env` copy is optional. Defaults keep LLM providers disabled and require no credentials. Startup and default tests perform no live stock, website, currency, or LLM request.

## Run the API and MCP server

```powershell
python -m uvicorn toolbridge.main:app --host 127.0.0.1 --port 8000
```

| Purpose | URL |
| --- | --- |
| Service metadata | <http://127.0.0.1:8000/> |
| Liveness | <http://127.0.0.1:8000/health> |
| Readiness | <http://127.0.0.1:8000/ready> |
| Safe operational snapshot | <http://127.0.0.1:8000/operations/snapshot> |
| OpenAPI | <http://127.0.0.1:8000/docs> |
| MCP Streamable HTTP | `http://127.0.0.1:8000/mcp/` |

`/health` is a cheap liveness response. `/ready` verifies local lifecycle, registry, managed tools, and Provider Router state without performing external probes. Optional provider and all-tool-health readiness requirements are configuration controlled.

## Run the dashboard

Start this in a second terminal after the API:

```powershell
.\.venv\Scripts\Activate.ps1
python -m streamlit run toolbridge/dashboard/app.py --server.address 127.0.0.1
```

Open <http://127.0.0.1:8501>. The dashboard makes only a local `GET` request to `/operations/snapshot`; it has no mutation controls and sends no credentials. Keep both services on localhost because inbound authentication and authorization are outside Phase 6.

## Tool summary

| Tool | Purpose | Primary boundary |
| --- | --- | --- |
| `system_status` | Local diagnostic status | No external I/O |
| `stock_price` | Normalized current quote | Yahoo primary, optional Alpha Vantage |
| `website_reader` | Clean public HTTPS page text | SSRF-aware bounded HTTP |
| `sql_query` | One safe read-only query | SQLite; PostgreSQL-ready port only |
| `csv_analysis` | Schema, statistics, missing values, preview | Confined local CSV root |
| `currency_converter` | Multi-currency conversion | Configured Frankfurter-compatible provider |
| `hcl_curie_analysis` | Analyze or summarize text | Existing LLM Provider Router |

All tools use the same registry, request validation, timeout, execution, response validation, safe logging, metrics, health, and lifecycle pipeline.

## Architecture

```text
MCP client
  -> FastMCP adapter
  -> ToolRegistry and ToolExecutor
  -> BaseTool application service
  -> project-owned port
  -> HTTP / SQLite / filesystem / Provider Router adapter

Streamlit dashboard
  -> local read-only HTTP client
  -> OperationsService
  -> immutable bounded snapshot
```

Domain and application code do not depend on FastAPI, FastMCP, or Streamlit. Transport and UI code depend inward. See `ARCHITECTURE.md`.

## Configuration

All settings use the `TOOLBRIDGE_` prefix and are documented in `.env.example`. Phase 6 settings are under `TOOLBRIDGE_OPERATIONS__...`. Provider token prices are optional per-provider settings; zero values produce a `$0` estimate rather than inventing a price.

## Verification

Verified on 2026-08-06:

- **112 passed**
- `python -m pip check`: no broken requirements
- application compilation/import and FastAPI lifespan startup succeed
- existing seven-tool MCP discovery remains unchanged
- one third-party `StarletteDeprecationWarning` remains

No numerical line-coverage claim is made because no coverage dependency is installed.

## Current limitations

- Local-only: no inbound authentication, authorization, tenancy, or rate limiting
- Metrics, uptime, logs, and caches are process-local and reset on restart
- Dashboard refresh is manual; no external telemetry backend, tracing, alert delivery, or persistence
- Cost values are estimates based on configured per-million-token rates; streaming responses report request count but cannot invent unavailable token totals
- Website DNS validation retains a documented rebinding risk and needs an outbound firewall/allowlist for production
- SQL is SQLite-only at runtime; CSV and SQL lack tenant authorization and production data governance
- External provider availability, terms, licenses, data processing, and cost controls require approval
- LLM output remains untrusted; no agent or tool chaining is implemented
- Yahoo Finance remains an undocumented contract requiring licensing review
- CI/CD, deployment automation, authentication, and Phase 7 capabilities are not implemented

## Documentation

See `PROJECT_STATUS.md`, `PROJECT_RULES.md`, `ROADMAP.md`, `ARCHITECTURE.md`, `TASKS.md`, `CHANGELOG.md`, `CODING_STANDARDS.md`, `TESTING_STRATEGY.md`, `GIT_WORKFLOW.md`, `DEPLOYMENT_PLAN.md`, `SECURITY_GUIDELINES.md`, and `DECISIONS.md`.

## License

No software license has been selected. Until one is added, no permission to copy, modify, or redistribute the project is granted by default.
