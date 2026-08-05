# Roadmap

This roadmap expresses intended outcomes, not committed dates. A phase begins only after the prior phase is accepted and the project owner approves the next scope.

## Status summary

| Phase | Outcome | Status |
| --- | --- | --- |
| 1. Foundation | Runnable Python, FastAPI, and MCP service baseline | Complete |
| 2. MCP Core | Validated contracts, registry, discovery, execution, errors, and logging | Complete - awaiting owner acceptance |
| 3. Core tools | Safe implementations of approved data-processing tools | Awaiting approval |
| 4. Provider routing | Provider-neutral LLM interface, health checks, and failover | Planned |
| 5. Agent and dashboard | Optional orchestration and operator/user interface | Planned |
| 6. Hardening | Broader security controls, observability, and performance | Planned |
| 7. Deployment | Reproducible packaging, CI/CD, runbooks, and release | Planned |

## Phase 1 - Foundation (complete)

Delivered Python 3.12 setup, pinned dependencies, Git initialization, FastAPI service endpoints, FastMCP Streamable HTTP, the `system_status` tool, typed environment settings, smoke tests, and local protocol verification.

## Phase 2 - MCP Core (complete; awaiting owner acceptance)

Delivered:

- Framework-independent tool input, output, metadata, request, response, and error contracts
- Immutable tool definitions with validated names, schemas, handler, and timeout
- Unique registry with deterministic lookup and discovery
- Strict request, JSON, input-schema, and size validation
- Strict response-schema, JSON encoding, and size validation
- Async execution boundary with correlation identifiers and per-tool timeouts
- Cooperative cancellation propagation and safe failure normalization
- FastMCP adapter for discovery and structured tool execution
- Strict transport schemas that forbid and hide unknown input values
- Structured JSON execution logs with an allowlist that excludes arguments and results
- Typed settings for timeout and request/response limits
- Unit coverage for registration, discovery, validation, success, unknown tool, timeout, cancellation, internal failure, invalid response, and logging
- Automated MCP initialize, list-tools, and call-tool protocol path

Exit criteria achieved:

- Contracts are documented and typed.
- The diagnostic tool registers, validates, executes, and fails through the core.
- All required success and failure cases have automated coverage.
- The suite runs offline without provider credentials.

Phase 2 does not add production tools, providers, agents, storage, UI, authentication, or deployment infrastructure.

## Phase 3 - Core tools (awaiting approval)

Goal: implement only owner-approved, threat-reviewed tools through the Phase 2 contracts.

Before implementation, decide:

- The first production tool and its authoritative data source
- Read-only versus side-effecting behavior
- Input, output, timeout, and size limits
- Network, filesystem, database, or provider permissions
- Data licensing, privacy, retention, and error expectations
- Tool-specific unit, component, and protocol acceptance tests

Likely candidates from the original concept include website retrieval, CSV analysis, SQL query boundaries, currency conversion, market-data adapters, and text summarization adapters. This list is illustrative and is not approval to implement any tool.

## Later-phase direction

### Phase 4 - Provider routing

Introduce project-owned provider interfaces, configuration, health status, fallback policy, budget controls, and failure classification. Provider choices require availability, licensing, cost, and security review.

### Phase 5 - Agent and dashboard

Evaluate agent orchestration only after deterministic tools and routing stabilize. Keep orchestration optional and independently testable.

### Phase 6 - Hardening

Add authentication, authorization, rate limits, audit events, broader metrics and traces, concurrency and load tests, dependency scanning, and recovery exercises.

### Phase 7 - Deployment

Add approved packaging, CI/CD, environment promotion, secret management, rollback procedures, monitoring, and release documentation.

## Change control

Phase 3 remains blocked until the project owner accepts Phase 2 and approves a specific tool scope. Scope or ordering changes require an entry in `DECISIONS.md`.
