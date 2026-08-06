# Task Register

This file tracks executable work. It does not authorize work by itself; phase changes require project-owner approval.

Status key: `[x]` complete, `[ ]` not started, `[-]` intentionally deferred.

## Phase 1 - Foundation

- [x] Create Python 3.12 environment, dependencies, FastAPI/FastMCP baseline, `system_status`, tests, Git, and GitHub synchronization

## Phase 2 - MCP Core

- [x] Implement contracts, registry, discovery, strict validation, bounded execution, safe errors, cancellation, logging, FastMCP adaptation, and tests

## Phase 3 - Provider Router

- [x] Implement provider-neutral models and ports
- [x] Implement Cerebras, NVIDIA, and OpenRouter adapters
- [x] Implement configuration, priority, retries, failover, streaming boundary, health, lifecycle, safe logging, and tests
- [x] Receive project-owner acceptance

## Phase 4 - Tool Framework and Stock Price

- [x] Implement `BaseTool`, `ToolManager`, automatic registration, health, and metrics
- [x] Reuse the Phase 2 validation, execution, response, error, timeout, logging, and cancellation pipeline
- [x] Implement Yahoo Finance primary and optional Alpha Vantage fallback
- [x] Implement bounded stock cache, retries, failover, configuration, security controls, and tests
- [x] Commit and synchronize Phase 4 with `origin/main`
- [x] Receive Phase 5 scope approval, which constitutes acceptance to proceed beyond Phase 4

## Phase 5 - Remaining Core MCP Tools

### Website Reader

- [x] Read credential-free public HTTPS pages
- [x] Block private/local destinations, redirects, unsupported content, and oversized bodies
- [x] Remove common HTML boilerplate and return structured clean text

### SQL Query Tool

- [x] Define a database-neutral read-only query port
- [x] Implement SQLite query-only and URI read-only execution
- [x] Validate one conservative `SELECT` or `WITH` statement with named parameters
- [x] Bound rows and interrupt long queries with a progress deadline
- [x] Keep a PostgreSQL adapter deferred without changing the application contract

### CSV Analysis Tool

- [x] Confine relative CSV paths beneath a configured root
- [x] Detect columns and delimiter
- [x] Return inferred types, numeric summary statistics, missing and unique counts, row counts, and preview
- [x] Bound file bytes, scan rows, columns, fields, preview, and execution time

### Currency Converter

- [x] Implement configurable Frankfurter exchange-rate integration
- [x] Validate finite amounts and ISO currency codes
- [x] Support multiple destination currencies
- [x] Add bounded retries, successful-response cache, and request coalescing

### HCL Curie / LLM Analysis

- [x] Implement analyze and summarize operations
- [x] Integrate only through the existing Provider Router
- [x] Return provider-neutral structured output and token usage
- [x] Treat supplied text and model output as untrusted

### Framework, tests, and documentation

- [x] Register all tools automatically with deterministic MCP discovery
- [x] Reuse lifecycle, validation, error handling, structured logs, metrics, and health
- [x] Add unit tests for every tool covering success, invalid input, errors, and response contracts
- [x] Preserve API, MCP, Core, Provider Router, framework, and Stock Price behavior
- [x] Run the complete suite: 98 of 98 passing
- [x] Verify dependency integrity and compilation
- [x] Update all required project documentation
- [ ] Project-owner acceptance of Phase 5

## Phase 6 and later - not approved

- [ ] Approve an exact Phase 6 scope before any implementation
- [ ] Evaluate agent orchestration and dashboard only after approval
- [ ] Design authentication, authorization, tenant controls, and inbound limits
- [ ] Add broader hardening, observability, packaging, CI/CD, deployment, and recovery only in approved later phases
- [ ] Choose a software license and production trust boundary

## Open owner decisions

- [ ] Accept or request revisions to Phase 5
- [ ] Approve production outbound website policy, data privacy, and content licensing
- [ ] Approve production database and CSV authorization/data-governance model
- [ ] Approve exchange-rate provider terms, coverage, and fallback policy
- [ ] Approve LLM data-processing, model, credential, and cost policy
- [ ] Resolve supported production stock-data contract and license
- [ ] Choose a software license and initial deployment environment
