# Roadmap

This roadmap expresses intended outcomes, not committed dates. A phase begins only after the prior phase is accepted and the project owner approves the next scope.

## Status summary

| Phase | Outcome | Status |
| --- | --- | --- |
| 1. Foundation | Runnable Python, FastAPI, and MCP baseline | Complete |
| 2. MCP Core | Contracts, registry, validation, execution, errors, logging | Complete |
| 3. Provider Router | Cerebras, NVIDIA, and OpenRouter routing | Complete and accepted |
| 4. Core tools | Reusable framework and Stock Price Tool | Complete - awaiting owner acceptance |
| 5. Agent and dashboard | Optional orchestration and interface | Planned |
| 6. Hardening | Broader security, observability, and performance | Planned |
| 7. Deployment | Packaging, CI/CD, runbooks, and release | Planned |

The owner promoted Provider Routing to Phase 3 on 2026-08-06. Core Tools became Phase 4. This ordering remains in force.

## Phase 1 - Foundation (complete)

Delivered Python 3.12 setup, pinned dependencies, Git and GitHub synchronization, FastAPI endpoints, FastMCP Streamable HTTP, `system_status`, typed settings, smoke tests, and protocol verification.

## Phase 2 - MCP Core (complete)

Delivered framework-independent contracts, deterministic registry and discovery, strict request and response validation, bounded execution, safe normalized errors, cancellation, structured logging, FastMCP adaptation, and offline protocol tests.

## Phase 3 - Provider Router (complete and accepted)

Delivered replaceable provider ports and adapters for Cerebras, NVIDIA, and OpenRouter; configuration-driven priority; bounded retry and failover; normalized generation and streaming; health and latency state; secret-aware configuration; safe logs; lifespan management; and offline tests.

## Phase 4 - Core tools (complete; awaiting owner acceptance)

Approved scope: implement the reusable Core Tool Framework and only the Stock Price Tool, with Yahoo Finance primary and optional Alpha Vantage fallback.

Delivered:

- Common `BaseTool` definition, initialize, health-check, and close lifecycle
- Automatic `ToolManager` integration with the existing MCP registry
- Existing Phase 2 request, argument, response, timeout, cancellation, error, and logging pipeline reused for every tool
- In-process aggregate metrics and typed tool health snapshots
- Provider-neutral stock quote port and normalized output contract
- Yahoo Finance adapter and optional Alpha Vantage `GLOBAL_QUOTE` adapter
- Configuration-driven timeouts, retries, cache duration, cache size, priority, backoff, endpoints, paths, and health symbol
- Successful-response-only per-symbol caching with request coalescing
- Category-aware retries and failover
- HTTPS origin, path, symbol, response-size, and redirect controls
- Allowlisted logs that exclude symbols, credentials, URLs, payloads, and exception messages
- Offline tests for registration, discovery, execution, invalid symbols, network failures, timeouts, response validation, retries, failover, caching, health, metrics, adapters, configuration, and log redaction

Exit criteria achieved:

- `stock_price` registers automatically and appears in MCP discovery.
- The tool domain and application layers do not depend on FastAPI or FastMCP.
- Yahoo and Alpha Vantage are replaceable behind a project-owned port.
- Startup and default tests require no credential or network access.
- Phase 1 through Phase 3 interfaces remain compatible.
- All 75 automated tests pass.

Acceptance constraints:

- Yahoo's chart endpoint is undocumented; approve a supported contract or data license before production/commercial use.
- Alpha Vantage standard quote freshness depends on entitlement and omits some metadata.
- The service remains local-development only without inbound security controls.

## Phase 5 - Agent and dashboard (planned; not approved)

Possible direction: evaluate agent orchestration and an operator/user interface after deterministic tools stabilize. Any scope must preserve explicit tool authorization, independent testing, and untrusted model-output handling.

No Phase 5 implementation is authorized by this roadmap entry.

## Phase 6 - Hardening (planned)

Potential work includes authentication, authorization, inbound rate limits, concurrency and cost controls, readiness, scheduled health, audit events, broader metrics and traces, load testing, recovery exercises, and approved market-data governance.

## Phase 7 - Deployment (planned)

Potential work includes reproducible packaging, CI/CD, environment promotion, secret management, rollback, monitoring, incident runbooks, and releases.

## Change control

Phase 5 remains blocked until the owner accepts Phase 4 and approves an exact scope. Changes to ordering, public schemas, provider contracts, or trust boundaries require a decision-log entry.
