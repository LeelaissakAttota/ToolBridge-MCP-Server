# Roadmap

This roadmap expresses outcomes, not committed dates. A phase begins only after the prior phase is accepted and the project owner approves an exact scope.

## Status summary

| Phase | Outcome | Status |
| --- | --- | --- |
| 1. Foundation | Runnable Python, FastAPI, and MCP baseline | Complete |
| 2. MCP Core | Contracts, registry, validation, execution, errors, logging | Complete |
| 3. Provider Router | Cerebras, NVIDIA, and OpenRouter routing | Complete and accepted |
| 4. Tool Framework and Stock Price | Reusable lifecycle and first provider-backed tool | Complete and accepted |
| 5. Remaining Core MCP Tools | Website, SQL, CSV, currency, and LLM analysis | Complete - awaiting owner acceptance |
| 6. Agent and dashboard | Optional orchestration and interface | Planned; not approved |
| 7. Hardening | Identity, broader observability, security, and performance | Planned; not approved |
| 8. Deployment | Packaging, CI/CD, runbooks, and release | Planned; not approved |

The project owner explicitly approved the Phase 5 Core MCP Tools scope on 2026-08-06. This approval supersedes the earlier placeholder that called Phase 5 “Agent and dashboard”; those capabilities move to Phase 6 without implementation.

## Completed phases

### Phase 1 - Foundation

Python 3.12 setup, pinned dependencies, Git/GitHub synchronization, FastAPI endpoints, FastMCP Streamable HTTP, `system_status`, typed settings, and smoke tests.

### Phase 2 - MCP Core

Framework-independent contracts, deterministic registry and discovery, strict request/response validation, bounded execution, safe errors, cancellation, structured logging, and protocol tests.

### Phase 3 - Provider Router

Replaceable Cerebras, NVIDIA, and OpenRouter adapters; configured priority, retry, failover, health, status, latency, lifecycle, secret handling, normalized streaming, and offline tests.

### Phase 4 - Tool Framework and Stock Price

Common `BaseTool`, automatic managed registration, health, metrics, Yahoo primary and optional Alpha Vantage fallback, safe routing, cache, retries, response normalization, and offline tests.

## Phase 5 - Remaining Core MCP Tools

Implemented:

- Website Reader with public-destination validation, bounded streaming, boilerplate removal, and structured text
- SQL Query Tool with SQLite, a PostgreSQL-ready port, conservative read-only validation, named parameters, row bounds, and progress timeout
- CSV Analysis Tool with confined paths, column detection, inferred types, statistics, missing-value analysis, and preview
- Currency Converter with configurable Frankfurter integration, multi-target conversion, retries, cache, and coalescing
- HCL Curie / LLM Analysis Tool with analyze/summarize modes and existing Provider Router integration
- Automatic registration, shared validation/execution/logging/metrics lifecycle, typed configuration, normalized errors, and offline unit/protocol tests

Exit criteria achieved:

- All five tools register automatically and appear in deterministic MCP discovery.
- Every tool uses the existing Phase 4 lifecycle and Phase 2 executor.
- Domain and application layers remain independent of FastAPI and FastMCP.
- External work is behind project-owned ports and bounded by configuration.
- Default startup and tests require no network or credentials.
- All 98 automated tests pass.

Acceptance constraints:

- Production website access requires an outbound allowlist/firewall and a decision on content privacy and licensing.
- Production SQL/CSV access requires identity, tenant authorization, least-privileged files/databases, and data governance.
- PostgreSQL has an architectural port but no adapter.
- Exchange-rate production use requires provider terms, availability, currency coverage, and freshness review.
- LLM output remains untrusted; provider credentials, cost controls, and data-processing terms must be approved.
- The server remains local-development only.

## Later phases - not approved

Phase 6 may evaluate agent orchestration and a dashboard only after Phase 5 acceptance. Phase 7 may add authentication, authorization, inbound limits, readiness, scheduled health, audit, broader observability, and performance work. Phase 8 may add packaging, CI/CD, deployment, rollback, and runbooks.

No Phase 6 or later capability is implemented.
