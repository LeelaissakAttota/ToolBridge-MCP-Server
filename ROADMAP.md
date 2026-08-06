# Roadmap

This roadmap expresses outcomes, not committed dates. A future phase begins only after project-owner approval of its exact scope.

## Status summary

| Phase | Outcome | Status |
| --- | --- | --- |
| 1. Foundation | Runnable Python, FastAPI, and MCP baseline | Complete |
| 2. MCP Core | Contracts, registry, validation, execution, errors, logging | Complete |
| 3. Provider Router | Cerebras, NVIDIA, and OpenRouter routing | Complete and accepted |
| 4. Tool Framework and Stock Price | Reusable lifecycle and first provider-backed tool | Complete and accepted |
| 5. Remaining Core MCP Tools | Website, SQL, CSV, currency, and LLM analysis | Complete and synchronized |
| 6. Dashboard & Production Readiness | Read-only dashboard, health/readiness, metrics, lifecycle validation | Complete; awaiting owner acceptance |
| 7. Hardening | Identity, authorization, tenant controls, broader observability, security, and performance | Planned; not approved |
| 8. Deployment | Packaging, CI/CD, deployment, rollback, and runbooks | Planned; not approved |

The owner explicitly approved Phase 6 on 2026-08-06. That approved scope supersedes the earlier placeholder “Agent and dashboard”: Phase 6 contains the dashboard and operational-readiness layer only. No agent was implemented.

## Completed phases

### Phase 1 - Foundation

Python 3.12 environment, pinned dependencies, Git/GitHub synchronization, FastAPI endpoints, FastMCP Streamable HTTP, `system_status`, typed settings, and smoke tests.

### Phase 2 - MCP Core

Framework-independent contracts, deterministic registry/discovery, strict input/output validation, bounded execution, cancellation, safe errors, structured logging, and protocol tests.

### Phase 3 - Provider Router

Replaceable Cerebras, NVIDIA, and OpenRouter adapters; priority, retry, failover, lifecycle, health/status/latency, secret isolation, normalized streaming, and offline tests.

### Phase 4 - Tool Framework and Stock Price

Common `BaseTool`, automatic registration, health/metrics lifecycle, Yahoo primary and optional Alpha Vantage fallback, cache, retries, failover, and offline tests.

### Phase 5 - Remaining Core MCP Tools

Website Reader, safe SQLite Query, CSV Analysis, Currency Converter, and HCL Curie / LLM Analysis were added through the existing framework. All seven tools share the same MCP Core lifecycle and preserve Clean Architecture boundaries.

## Phase 6 - Dashboard & Production Readiness

Implemented:

- professional Streamlit dashboard with System, Provider, MCP Tool, Metrics, Cost, and Log sections
- safe read-only `/operations/snapshot` endpoint and local dashboard client
- `/health` liveness preservation and new `/ready` readiness endpoint
- startup composition validation and lifecycle-aware graceful shutdown reporting
- cached tool lifecycle monitoring without dashboard-triggered external probes
- provider status, active/failover state, timing, request, token, and configured cost-estimate monitoring
- total/success/failed request metrics, error categories, tool usage, provider usage, and response timing
- bounded in-memory allowlisted recent logs with warning/error filtering
- typed local-only dashboard, log capacity, readiness policy, and provider-price configuration
- unit, API, provider, component, security, and configuration tests

Exit criteria achieved:

- the dashboard displays every requested section and all three providers/seven tools
- the dashboard and operational endpoint are read-only and contain no prompts, arguments, results, URLs, SQL, paths, content, or credentials
- readiness uses local state and never causes paid/network health probes
- startup validates registry/version composition before traffic readiness
- shutdown moves readiness out of service before resources close and reports categorized lifecycle failures
- existing Phase 1-5 HTTP, MCP, routing, and tool behavior remains compatible
- all 112 tests pass offline; dependency integrity succeeds

Acceptance constraints:

- the dashboard and API remain localhost-only because Phase 6 explicitly excludes authentication
- monitoring is bounded and process-local; it is not a persistent audit log or external telemetry system
- token cost is an estimate from configured rates, not a billing authority
- provider and stock scheduled probing, alert delivery, tracing, and a metrics backend remain deferred

## Later phases - not approved

Phase 7 may address authentication, authorization, tenants, inbound limits, persistent audit/telemetry, tracing, scheduled probes, and broader hardening only after separate approval. Phase 8 may address packaging, CI/CD, deployment, rollback, and runbooks.

No Phase 7 or later capability is implemented.
