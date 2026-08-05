# Roadmap

This roadmap expresses intended outcomes, not committed dates. A phase begins only after the prior phase is accepted and the project owner approves the next scope.

## Status summary

| Phase | Outcome | Status |
| --- | --- | --- |
| 1. Foundation | Runnable Python, FastAPI, and MCP service baseline | Complete |
| 2. MCP Core | Validated contracts, registry, discovery, execution, errors, and logging | Complete |
| 3. Provider Router | Provider-neutral Cerebras, NVIDIA, and OpenRouter routing | Complete - awaiting owner acceptance |
| 4. Core tools | Safe implementations of approved production tools | Planned |
| 5. Agent and dashboard | Optional orchestration and operator/user interface | Planned |
| 6. Hardening | Broader security controls, observability, and performance | Planned |
| 7. Deployment | Reproducible packaging, CI/CD, runbooks, and release | Planned |

## Phase ordering decision

The project owner explicitly promoted Provider Routing from Phase 4 to Phase 3 on 2026-08-06. The previously planned Core Tools phase moves to Phase 4. No Core Tools or later-phase functionality was implemented as part of this change.

## Phase 1 - Foundation (complete)

Delivered Python 3.12 setup, pinned dependencies, Git initialization, FastAPI service endpoints, FastMCP Streamable HTTP, the `system_status` tool, typed environment settings, smoke tests, and local protocol verification.

## Phase 2 - MCP Core (complete)

Delivered framework-independent tool contracts, deterministic registry and discovery, strict request and response validation, timeout-aware execution, safe normalized errors, structured logging, FastMCP adaptation, and full offline protocol tests.

## Phase 3 - Provider Router (complete; awaiting owner acceptance)

Delivered:

- Provider-neutral domain models for generation, streaming, models, usage, health, status, and errors
- Replaceable `BaseProvider` lifecycle interface
- Cerebras, NVIDIA, and OpenRouter adapters
- Configuration-driven provider enablement and priority
- Active-provider selection, bounded retries, capped exponential backoff, and safe failover
- Normalized non-streaming and streaming responses
- Streaming failover only before the first emitted chunk
- On-demand concurrent health probes
- Latency, last-success, last-failure, and error-category status snapshots
- Typed secret, endpoint, timeout, retry, token, temperature, and payload settings
- Allowlisted JSON logs without keys, prompts, responses, or vendor error bodies
- Application lifespan initialization and shutdown
- Offline tests for selection, failover, retries, health, configuration, adapters, errors, streaming, and logging

Exit criteria achieved:

- The provider application layer does not import FastAPI or FastMCP.
- Each provider can be replaced behind the project-owned interface.
- Default startup and tests require no provider credentials or network access.
- Phase 1 and Phase 2 public interfaces remain compatible.

## Phase 4 - Core tools (planned; not approved)

Goal: implement only an owner-approved, threat-reviewed production tool through the Phase 2 MCP contracts and, when needed, the Phase 3 provider router.

Before implementation, decide:

- the exact tool and authoritative data or model source,
- read-only versus side-effecting behavior,
- input, output, timeout, token, and size limits,
- network, filesystem, database, or provider permissions,
- data licensing, privacy, retention, and cost expectations,
- unit, component, security, provider, and MCP acceptance tests.

No production tool is authorized by this roadmap entry.

## Later-phase direction

### Phase 5 - Agent and dashboard

Evaluate optional agent orchestration only after deterministic tools and provider routing stabilize. Keep orchestration independently testable and subject to explicit authorization boundaries.

### Phase 6 - Hardening

Add authentication, authorization, inbound rate limits, provider concurrency and budget controls, scheduled health monitoring, readiness, audit events, broader metrics and traces, load tests, and recovery exercises.

### Phase 7 - Deployment

Add approved packaging, CI/CD, environment promotion, secret management, rollback procedures, monitoring, and release documentation.

## Change control

Phase 4 remains blocked until the project owner accepts Phase 3 and approves one specific tool scope. Future scope or ordering changes require an entry in `DECISIONS.md`.
