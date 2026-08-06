# ToolBridge MCP Server

ToolBridge is a Model Context Protocol service with typed, validated, observable, read-only tools. Version `0.5.0` completes the approved Phase 5 implementation by adding the five remaining Core MCP Tools to the reusable framework delivered in Phase 4.

Phase 5 is implemented and tested but remains uncommitted pending project-owner approval. Dashboard, agents, authentication, CI/CD, deployment, and later-phase work are not implemented.

## Current capabilities

- FastAPI control plane and stateless FastMCP Streamable HTTP transport
- Framework-independent registry, discovery, strict validation, bounded execution, safe errors, structured logs, and aggregate metrics
- Configuration-driven LLM Provider Router for Cerebras, NVIDIA, and OpenRouter
- Common `BaseTool` and `ToolManager` lifecycle with automatic MCP registration
- Seven discoverable tools: `system_status`, `stock_price`, `website_reader`, `sql_query`, `csv_analysis`, `currency_converter`, and `hcl_curie_analysis`
- Offline test suite using fakes, temporary fixtures, and `httpx.MockTransport`

## Setup and local run

Requirements: Python 3.12 and internet access only for installation or explicitly invoked live provider tools.

```powershell
py -3.12 -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
Copy-Item .env.example .env
python -m pytest -q -p no:cacheprovider
python -m uvicorn toolbridge.main:app --host 127.0.0.1 --port 8000
```

The `.env` copy is optional. Startup and default tests make no external provider request. Keep the service bound to localhost; authentication and inbound rate limiting are not implemented.

| Purpose | URL |
| --- | --- |
| Service metadata | <http://127.0.0.1:8000/> |
| Liveness | <http://127.0.0.1:8000/health> |
| OpenAPI | <http://127.0.0.1:8000/docs> |
| MCP Streamable HTTP | `http://127.0.0.1:8000/mcp/` |

## MCP tools

### `system_status`

Returns the local service status and timestamp without external I/O.

### `stock_price`

Accepts a stock symbol and returns a normalized quote through Yahoo Finance with optional Alpha Vantage fallback. Provider timeouts, retries, cache, priority, response size, and health probe are configured under `TOOLBRIDGE_STOCK_PRICE__`.

### `website_reader`

Accepts a credential-free HTTPS URL and returns the final URL, title, clean visible text, content type, word count, timestamp, and truncation state. It removes common scripts and boilerplate, refuses redirects, blocks non-public destinations, streams within a response-size limit, and supports an exact host allowlist.

Configuration prefix: `TOOLBRIDGE_PHASE5__WEBSITE_READER__`.

### `sql_query`

Executes one parameterized `SELECT` or read-only `WITH` query against the configured SQLite database. Statement separators, comments, and mutating keywords are rejected. SQLite runs in query-only mode with a progress-handler timeout and bounded rows. The application depends on a database-neutral port so a future PostgreSQL adapter can be added without changing the tool contract.

Configuration prefix: `TOOLBRIDGE_PHASE5__SQL_QUERY__`. The default `:memory:` database supports safe diagnostic queries; configure a relative database file beneath `DATABASE_ROOT` for application data.

### `csv_analysis`

Reads a `.csv` file beneath the configured root and returns detected columns, inferred types, numeric summary statistics, missing and unique counts, a bounded preview, row counts, delimiter, and truncation state. Paths, file bytes, rows, columns, fields, preview size, and execution time are bounded.

Configuration prefix: `TOOLBRIDGE_PHASE5__CSV_ANALYSIS__`.

### `currency_converter`

Converts one positive finite amount into multiple distinct ISO currencies through the configured Frankfurter-compatible provider. It uses bounded streaming responses, normalized failures, safe retries, successful-response caching, and request coalescing.

Configuration prefix: `TOOLBRIDGE_PHASE5__CURRENCY_CONVERTER__`.

### `hcl_curie_analysis`

Analyzes or summarizes bounded text through the existing LLM Provider Router and returns provider-neutral content, provider, model, request identifier, and token usage. Text is wrapped as untrusted document data. The tool is discoverable when no LLM provider is enabled but reports unavailable until at least one configured provider can route requests.

Configuration prefix: `TOOLBRIDGE_PHASE5__LLM_ANALYSIS__`. Provider credentials and models remain under the Phase 3 provider settings shown in `.env.example`.

## Architecture

```text
MCP client
   -> FastMCP adapter
   -> ToolRegistry
   -> request validation
   -> ToolExecutor timeout boundary
   -> BaseTool application service
   -> project-owned port
   -> HTTP / SQLite / filesystem / Provider Router adapter
   -> response validation
   -> structured logs and aggregate metrics
```

Domain and application modules do not import FastAPI or FastMCP. External details stay in adapters; configuration and object composition stay in infrastructure. See `ARCHITECTURE.md` for boundaries and data flows.

## Tests

```powershell
python -m pytest -q -p no:cacheprovider
python -m pip check
```

Current result: **98 passed** on 2026-08-06. One third-party `StarletteDeprecationWarning` remains. No line-coverage dependency is installed, so no numerical coverage percentage is claimed.

## Current limitations

- The service is local-development only; no inbound identity, authorization, rate limiting, or production hardening exists.
- Website DNS validation has a residual time-of-check/time-of-use rebinding risk; production deployments also need outbound firewall policy and an explicit host allowlist.
- SQL is SQLite-only at runtime; PostgreSQL has a replaceable port but no adapter.
- CSV and SQL data are local and process-scoped; no tenant authorization model exists.
- Frankfurter availability, supported currencies, terms, and rate freshness remain external dependencies.
- LLM output is untrusted and can be incomplete or incorrect; no tool chaining or agent autonomy is implemented.
- Yahoo Finance remains an undocumented stock-data contract requiring licensing review.
- Caches and metrics are process-local and reset on restart.

## Documentation

See `PROJECT_STATUS.md`, `PROJECT_RULES.md`, `ROADMAP.md`, `ARCHITECTURE.md`, `TASKS.md`, `CHANGELOG.md`, `CODING_STANDARDS.md`, `TESTING_STRATEGY.md`, `GIT_WORKFLOW.md`, `DEPLOYMENT_PLAN.md`, `SECURITY_GUIDELINES.md`, and `DECISIONS.md`.

## License

No software license has been selected. Until one is added, no permission to copy, modify, or redistribute the project is granted by default.
