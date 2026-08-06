# Architecture

## Purpose and current state

ToolBridge `0.6.0` is a local-only MCP service with seven read-only tools and a separate read-only Streamlit operations dashboard. One Python process hosts FastAPI, FastMCP, MCP Core, managed tools, the Provider Router, and process-local operational state. Streamlit runs as a second local process and reads one safe HTTP snapshot.

Existing `/`, `/health`, `/docs`, `/mcp/`, and all Phase 1-5 MCP tool contracts remain compatible. Phase 6 adds `/ready` and `/operations/snapshot`. Startup performs no provider, website, stock, exchange-rate, database, or file request.

```mermaid
flowchart LR
    Client["MCP client"] --> Transport["FastMCP Streamable HTTP"]
    Transport --> Adapter["MCP adapter"]
    Adapter --> Executor["ToolExecutor"]
    Executor --> Registry["ToolRegistry"]
    Manager["ToolManager"] --> Registry
    Registry --> Tools["Seven managed tools"]

    Tools --> Ports["Project-owned ports"]
    Ports --> Adapters["HTTP / SQLite / files / Provider Router"]
    Executor --> Observers["Safe logging and metrics observers"]
    Router["Provider Router"] --> Observers

    Dashboard["Streamlit dashboard"] --> ClientAdapter["Local read-only HTTP client"]
    ClientAdapter --> Snapshot["GET /operations/snapshot"]
    Snapshot --> Operations["OperationsService"]
    Operations --> Manager
    Operations --> Router
    Operations --> Observers
```

## Clean Architecture boundaries

### Domain

- `toolbridge/core/contracts.py`: stable MCP execution contracts and errors
- `toolbridge/tools/domain`: tool input/output, health, and metric models
- `toolbridge/providers/domain`: provider-neutral generation, status, usage, and error models
- `toolbridge/operations/domain`: immutable readiness, system, provider, tool, metric, cost, and safe-log snapshot models

Domain modules contain no FastAPI, FastMCP, Streamlit, HTTP client, database, or filesystem implementation.

### Application

- `ToolExecutor` owns request/response validation, timeouts, error normalization, cancellation, and execution observers.
- `ToolManager` owns registration and lifecycle. Phase 6 adds cached monitoring snapshots so dashboard reads do not trigger external tool health checks.
- `ProviderRouter` owns provider priority, retries, failover, lifecycle, status, and normalized generation. A provider-usage observer receives only provider identity and normalized token counts.
- `OperationsService` owns startup validation, lifecycle/readiness decisions, and aggregation into immutable safe snapshots.
- `InMemoryOperationalMetrics` is a bounded observer for tool/provider timing, provider usage/cost estimates, error categories, and recent allowlisted events.

Application code remains independent of FastAPI, FastMCP, and Streamlit.

### Adapters

- FastMCP projects registry definitions into MCP discovery/execution.
- Existing Yahoo/Alpha Vantage, website, SQLite, CSV, Frankfurter, and LLM HTTP adapters remain unchanged.
- FastAPI exposes liveness, readiness, and safe operational snapshot transport routes.
- `DashboardClient` performs a credential-free local `GET`, refuses redirects, and validates the JSON against strict domain models.
- Streamlit renders the immutable snapshot and exposes no server mutation operation.

### Infrastructure and composition

`config.py` owns typed provider, tool, operational, readiness, dashboard, and price settings. `bootstrap.py` composes console loggers with bounded operational observers, builds the Provider Router, builds/registers tools, and creates `OperationsService`. `main.py` coordinates startup validation and the MCP/provider/tool lifespan.

## Request and execution flow

```mermaid
sequenceDiagram
    participant C as MCP Client
    participant A as MCP Adapter
    participant E as ToolExecutor
    participant T as BaseTool
    participant P as Port/Router
    participant O as Safe Observers

    C->>A: tools/call
    A->>E: normalized execution request
    E->>E: validate size, JSON, and typed arguments
    E->>T: execute inside configured timeout
    T->>P: bounded read-only operation
    P-->>T: normalized result or categorized error
    T-->>E: typed output
    E->>E: validate schema and response bytes
    E->>O: allowlisted outcome and timing
    E-->>A: normalized response
    A-->>C: MCP result
```

## Operational flow

```mermaid
sequenceDiagram
    participant D as Streamlit Dashboard
    participant F as FastAPI
    participant O as OperationsService
    participant M as Metrics/Status Sources

    D->>F: GET /operations/snapshot
    F->>O: snapshot()
    O->>M: read locks and cached/local state only
    M-->>O: bounded immutable values
    O-->>F: OperationsSnapshot
    F-->>D: strict JSON
```

The operational read path performs no provider, stock, website, database, exchange-rate, or file probe. Provider status reflects lifecycle and prior routed operations. Tool health reflects cached lifecycle or an explicitly requested health probe elsewhere.

## Liveness, readiness, and lifecycle

- `/health` is cheap liveness and remains independent of optional external systems.
- `/ready` returns `200` only when the lifespan is ready, registry composition is valid, all configured tools initialized, and Provider Router initialization completed. It returns `503` otherwise.
- Optional settings may additionally require an active LLM provider or all cached tool states to be healthy.
- startup validation checks a non-empty version and one-to-one manager/registry composition before traffic readiness.
- readiness changes to stopping before provider/tool resources close.
- lifecycle failures are recorded by safe category without exception text.
- `ToolManager.close()` and Provider Router closure preserve existing idempotent resource ownership.

## Metrics, cost, and logs

Tool metrics count starts, successes, failures, average/last duration, last error category, and last completion time. Provider monitoring includes configured/enabled state, priority, active/failover state, status, last latency/timestamps/error, generation requests, and token counts.

Cost estimates are computed from configured input/output USD-per-million-token values. Defaults are zero. Streaming generations count as requests, but token counts remain zero when the normalized stream contract supplies no usage; the system never invents usage.

Recent logs use a bounded `deque` with a configured capacity. Stored fields are limited to timestamp, level, source, event, component, status, latency, safe request identifier, and error category. They are process-local and not an audit record.

## Configuration and trust boundaries

Phase 6 settings use `TOOLBRIDGE_OPERATIONS__...`. Provider cost rates remain alongside each provider’s typed settings. The dashboard API URL must be loopback and cannot contain credentials, query data, or fragments.

MCP arguments, provider responses, website content, SQL, database values, file paths, CSV data, model output, environment variables, and external errors remain untrusted. Operational output explicitly excludes API keys, authorization headers, prompts, tool arguments/results, URLs, queries, SQL, parameters, paths, filenames, cells, content, provider bodies, and exception messages.

## Current constraints

- local-only; no authentication, authorization, tenancy, inbound rate limits, or public dashboard exposure
- no persistent metrics/audit backend, distributed cache, tracing, scheduled health probes, or alert delivery
- process-local values reset on restart and do not aggregate across workers
- cost estimates depend on operator-configured prices and provider-reported usage
- existing external-contract, data-governance, licensing, and DNS-rebinding risks remain
- no agent, CI/CD, deployment pipeline, packaging, or Phase 7 implementation

## Phase boundary

Phase 6 is complete and awaits owner acceptance. Phase 7 must not begin without explicit approval.
