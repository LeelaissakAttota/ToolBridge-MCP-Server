# ToolBridge MCP Server Demo

This sequence presents the released v1.1.0 system in about 5 minutes without paid provider calls or repository changes. `sql_query` uses PostgreSQL only. There is no SQLite backend. Non-SQL tools still run without a database.

## Five-minute clock

| Minute | Show | Say |
| --- | --- | --- |
| 0:00 | Start API and dashboard | "One loopback process hosts MCP. The dashboard only reads a safe snapshot." |
| 0:30 | `GET /` and `/health` | "Version 1.1.0. Health means the process is alive. It does not call providers." |
| 1:00 | `GET /ready` | "Ready means seven tools are registered. Still no external call." |
| 1:30 | MCP `tools/list` | "The client discovers the contracts. I do not hard-code seven endpoints." |
| 2:30 | `system_status` | "A real tool call, not a mock page." |
| 3:15 | `sql_query` `SELECT 1 AS value` | "Read-only SQL. Parameters stay out of the query text." |
| 4:00 | Unknown tool, then a `DELETE` | "Bad input is rejected before the database runs." |
| 4:30 | Dashboard Overview and Logs | "The log does not show the SQL, the result, or any key." |

If `TOOLBRIDGE_MCP_AUTH_TOKEN` is set in `.env`, every `/mcp/` call needs `Authorization: Bearer <token>`. A blank token means no auth, which is the credential-free path. Do not paste the token into slides or the chat transcript.

## Demo Goal

Show a recruiter or engineering interviewer that ToolBridge:

- starts as a local FastAPI/FastMCP service
- reports liveness and lifecycle readiness separately
- completes the MCP initialize, discovery, and execution lifecycle
- exposes exactly seven schema-validated tools
- executes a deterministic local tool and a read-only SQL query
- rejects unsafe or invalid requests without crashing
- publishes secret-safe operational state to a read-only Streamlit dashboard
- discovers provider plugins and supports ranking, health, budget, retry, and failover policy without requiring live credentials for the demonstration

For a static preview of the verified local UI and interfaces, see the [genuine screenshot gallery](../screenshots/README.md).

The gallery also retains point-in-time NVIDIA LLM, Yahoo Finance AAPL, and Frankfurter currency-validation evidence. Those captures are separate from this credential-free demo and do not imply permanent provider availability or a production SLA.

## Prerequisites

- Windows PowerShell from the repository root
- Python 3.12
- the existing `.venv` with `requirements-dev.txt` installed
- local ports `8000` and `8501` available
- two terminal windows

No provider credential or Docker daemon is required for the core demo. If this machine's `.env` enables an LLM provider, startup may call that provider's model list. That is local configuration, not a demo requirement. For a credential-free walkthrough, leave provider `ENABLED` values false. For a fresh machine, complete [INSTALLATION.md](INSTALLATION.md) first. The one-page speaking card is [INTERVIEW_CHEATSHEET.md](INTERVIEW_CHEATSHEET.md).

## Startup

In terminal 1, start the API and MCP endpoint with the project interpreter:

```powershell
.\.venv\Scripts\python.exe -m uvicorn toolbridge.main:app --host 127.0.0.1 --port 8000
```

In terminal 2, start the dashboard:

```powershell
.\.venv\Scripts\python.exe -m streamlit run toolbridge/dashboard/app.py --server.address 127.0.0.1 --server.port 8501
```

Keep both processes on loopback. If port `8501` is already in use, start the dashboard on another loopback port, for example `8502`, and keep the API on `127.0.0.1:8000`. Stop them with `Ctrl+C` when the demo is complete.

## Demo Sequence

### 1. Confirm service identity

```powershell
Invoke-RestMethod http://127.0.0.1:8000/
```

Point out version `1.1.0` and the links to health, readiness, operations, MCP, and OpenAPI.

Expected: `name` is `ToolBridge MCP Server`, `version` is `1.1.0`, `status` is `running`. The MCP `initialize` result can show server version `1.29.0`. That number is the MCP SDK, not the application version. Use `GET /` for the product version.

### 2. Separate liveness from readiness

```powershell
Invoke-RestMethod http://127.0.0.1:8000/health
Invoke-RestMethod http://127.0.0.1:8000/ready | ConvertTo-Json -Depth 6
```

`/health` proves that the process is alive. Expected: `status` is `ok` and `service` is `toolbridge-mcp`. `/ready` verifies lifecycle, registry composition, tool initialization, and provider-router initialization without making external provider calls. Expected: `ready` is `true` and the registry check says `7 tools registered`.

### 3. Initialize MCP

```powershell
$mcpHeaders = @{ Accept = 'application/json, text/event-stream' }
$initialize = Invoke-RestMethod -Method Post `
  -Uri http://127.0.0.1:8000/mcp/ `
  -Headers $mcpHeaders `
  -ContentType 'application/json' `
  -InFile examples/mcp_initialize_request.json
$initialize | ConvertTo-Json -Depth 10
```

Highlight the negotiated protocol version and advertised tool capability.

### 4. Discover all seven tools

```powershell
$tools = Invoke-RestMethod -Method Post `
  -Uri http://127.0.0.1:8000/mcp/ `
  -Headers $mcpHeaders `
  -ContentType 'application/json' `
  -InFile examples/mcp_tools_list_request.json
$tools.result.tools | Select-Object name, description
```

Show that discovery returns exactly:

1. `csv_analysis`
2. `currency_converter`
3. `llm_analysis`
4. `sql_query`
5. `stock_price`
6. `system_status`
7. `website_reader`

The returned input and output schemas—not this document—are the authoritative contracts.

### 5. Execute `system_status`

```powershell
$status = Invoke-RestMethod -Method Post `
  -Uri http://127.0.0.1:8000/mcp/ `
  -Headers $mcpHeaders `
  -ContentType 'application/json' `
  -InFile examples/mcp_system_status_request.json
$status.result.structuredContent | ConvertTo-Json
```

The structured result contains `service` = `toolbridge-mcp`, `status` = `ok`, and a runtime-generated ISO 8601 `timestamp`. `result.isError` is false.

### 6. Execute a safe SQL read

```powershell
$sql = Invoke-RestMethod -Method Post `
  -Uri http://127.0.0.1:8000/mcp/ `
  -Headers $mcpHeaders `
  -ContentType 'application/json' `
  -InFile examples/mcp_sql_query_request.json
$sql.result.structuredContent | ConvertTo-Json -Depth 6
```

The request file runs `SELECT 1 AS value` with an empty parameter object. Expected structured result, when PostgreSQL is running and the read-only role can connect: column `value`, one row with numeric `1`, `row_count` 1, `truncated` false, and a runtime `execution_ms`. If PostgreSQL is not running, the call fails with a safe database error and does not fall back to SQLite.

`sql_query` always uses `TOOLBRIDGE_PHASE5__SQL_QUERY__BACKEND=postgres`. Set `POSTGRES_DSN` or host, database, and user. Use a `SELECT`-only role. Do not put the password in the demo transcript.

### 7. Show normalized rejection

```powershell
$invalid = Invoke-RestMethod -Method Post `
  -Uri http://127.0.0.1:8000/mcp/ `
  -Headers $mcpHeaders `
  -ContentType 'application/json' `
  -InFile examples/mcp_invalid_tool_request.json
$invalid.result | ConvertTo-Json -Depth 6
```

The MCP response sets `isError` and does not crash the service or reveal configuration. Expected: a normalized tool error for `no_such_tool`, not a stack trace. For the application-level SQL error envelope, replace the query with a non-read operation such as `DELETE FROM example`; validation rejects it before database execution. Say: "The write never reaches SQLite or PostgreSQL."

### 8. Open the operations dashboard

Open `http://127.0.0.1:8501` and briefly visit:

- **Overview:** version, uptime, lifecycle, health, and readiness
- **Providers:** Cerebras, NVIDIA, and OpenRouter status/capabilities and failover state
- **MCP Tools:** registration, health, execution counts, and timing
- **Metrics & Cost:** request outcomes, normalized error categories, provider usage, and estimated process-local cost
- **Logs:** bounded allowlisted operational events

Emphasize that the dashboard reads one strict snapshot and never displays prompts, tool inputs/results, URLs, SQL, file paths, credentials, authorization headers, or raw provider bodies.

### 9. Explain the provider platform

Use the Mermaid diagrams in [ARCHITECTURE.md](../ARCHITECTURE.md):

1. adapter modules call `register_provider()`
2. package discovery populates `ProviderPluginRegistry`
3. the factory composes only enabled plugins
4. startup health-checks enabled providers and discovers model metadata
5. requests are filtered by required capability
6. `ModelRankingEngine` considers health, latency, configured cost/free status, context, and quality
7. `ProviderBudgetManager` can deprioritize or exclude providers
8. eligible transient failures can retry and fail over

Providers are disabled by default, so this explanation does not require a paid request.

### 10. Optional Docker discussion

If Docker is running:

```powershell
docker compose config --quiet
docker compose up --build --detach
.\.venv\Scripts\python.exe scripts/verify_release.py --timeout-seconds 90
```

Do not make Docker startup a prerequisite for a short recruiter demo. The verified deployment design is a non-root, loopback-published, single-host Compose stack.

## Talking Points

- **Why MCP:** one discoverable, schema-driven protocol lets compatible clients initialize, list tools, and call them without custom client endpoints for every capability.
- **Why Clean Architecture:** provider SDKs, HTTP, SQLite, files, FastAPI, FastMCP, and Streamlit remain outer adapters; domain and application policies are independently testable.
- **Provider abstraction:** application code depends on provider-neutral ports and normalized models, not vendor response shapes.
- **Plugin registration:** built-ins self-register and are discovered from the adapter package, avoiding a provider-name switch in the router/factory.
- **Dynamic routing:** hard capability/availability/budget filters run before scoring health, latency, cost, context, and quality.
- **Budget controls:** daily, monthly, and per-request limits reduce accidental spend; they are process-local safeguards, not billing authority.
- **Security decisions:** loopback-only publication compensates for the intentionally absent inbound identity layer; all boundaries validate and bound untrusted data.
- **Test strategy:** 239 deterministic offline tests pass, and one live PostgreSQL test is skipped unless `TOOLBRIDGE_TEST_POSTGRES_DSN` is set. The offline suite uses fakes, temporary SQLite/CSV data, and mock HTTP transports with no warnings. Continuous Integration also performs startup and Compose smoke checks.
- **Docker:** the release uses a multi-stage image, fixed non-root identity, read-only roots, dropped capabilities, bounded `/tmp`, and health checks.
- **Known limitations:** no authentication, tenancy, persistent telemetry, distributed budget ledger, public deployment, or live-provider CI.

## Demo Limitations

- Live Cerebras, NVIDIA, and OpenRouter calls require separately configured credentials, model selection, network access, quota, cost approval, and provider terms.
- Stock, website, and currency demonstrations depend on external network/provider availability and were network-dependent during owner manual validation.
- Docker runtime validation requires a running Docker daemon.
- There is no inbound authentication; the supported deployment is loopback/local or behind a separately reviewed trusted boundary.
- Metrics, recent logs, health scores, caches, and provider budgets are process-local and reset when the API process restarts.
- Cost values are estimates based on configured rates and normalized usage, not authoritative billing records.
