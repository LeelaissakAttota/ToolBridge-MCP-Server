# Task Register

This file tracks executable work. It does not authorize future phases; phase changes require project-owner approval.

Status key: `[x]` complete, `[ ]` not started, `[-]` intentionally deferred.

## Phases 1-5

- [x] Phase 1: Python/FastAPI/FastMCP foundation, configuration, diagnostic tool, tests, Git, and GitHub synchronization
- [x] Phase 2: MCP contracts, registry, discovery, strict validation, bounded execution, safe errors, cancellation, logging, and tests
- [x] Phase 3: Cerebras/NVIDIA/OpenRouter adapters, priority, retries, failover, streaming, health, lifecycle, safe logging, and tests
- [x] Phase 4: reusable tool framework, automatic registration, health/metrics, Stock Price Tool, cache/failover, and tests
- [x] Phase 5: Website Reader, SQL Query, CSV Analysis, Currency Converter, HCL Curie / LLM Analysis, documentation, commit, and origin synchronization

## Phase 6 - Dashboard & Production Readiness

### Dashboard

- [x] Build professional read-only Streamlit application
- [x] Display version, uptime, environment, phase, health, and readiness
- [x] Display Cerebras, NVIDIA, and OpenRouter configuration, health, active/failover state, latency, and timestamps
- [x] Display registration, lifecycle health, executions, average response time, and last execution for all seven tools
- [x] Display total/success/failed requests, errors, average response time, provider usage, and tool usage
- [x] Display token usage, configured estimated API cost, requests per provider, and cost per provider
- [x] Display recent INFO/WARNING/ERROR logs from a bounded safe-field buffer
- [x] Keep dashboard local-only and mutation-free

### Operational readiness

- [x] Preserve cheap `/health` liveness behavior
- [x] Add `/ready` with 200/503 lifecycle-aware readiness
- [x] Add safe read-only `/operations/snapshot`
- [x] Validate registry and version composition at startup
- [x] Mark readiness false before graceful resource shutdown
- [x] Categorize lifecycle and shutdown failures without logging exception text
- [x] Add process-local provider/tool/request/timing/error/token/cost metrics
- [x] Ensure dashboard/readiness reads never invoke external health probes
- [x] Add bounded typed configuration and safe environment examples

### Verification and documentation

- [x] Test dashboard components and local HTTP client
- [x] Test metrics, cost estimates, safe log bounds, readiness, provider usage, tool monitoring, and operations endpoint
- [x] Preserve seven-tool MCP discovery and all Phase 1-5 regression behavior
- [x] Run complete suite: 112 of 112 passing
- [x] Run dependency integrity and compilation checks
- [x] Update all required Phase 6 documentation
- [ ] Project-owner acceptance of Phase 6

## Phase 7 and later - not approved

- [ ] Approve an exact Phase 7 scope before implementation
- [ ] Design authentication, authorization, tenant controls, and inbound rate/concurrency/cost limits
- [ ] Decide on persistent audit, metrics backend, tracing, scheduled health probes, and alert delivery
- [ ] Add packaging, CI/CD, deployment, rollback, and recovery only in an approved later phase
- [ ] Choose a software license and production trust boundary

## Open owner decisions

- [ ] Accept or request revisions to Phase 6
- [ ] Select production identity, authorization, tenancy, and inbound-limit model
- [ ] Select persistent telemetry, audit, tracing, retention, and alerting model
- [ ] Approve production website, database, CSV, currency, stock, and LLM policies/contracts
- [ ] Choose a software license and initial deployment environment
