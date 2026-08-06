# Task Register

This file tracks executable work. It does not authorize work by itself; phase changes require project-owner approval.

Status key: `[x]` complete, `[ ]` not started, `[-]` intentionally deferred.

## Phase 1 - Foundation (complete)

- [x] Create and verify the Python 3.12 environment and pinned dependencies
- [x] Add typed settings, FastAPI endpoints, and FastMCP Streamable HTTP
- [x] Add `system_status` and smoke/protocol tests
- [x] Initialize Git on `main`, configure GitHub `origin`, and synchronize

## Phase 2 - MCP Core (complete)

- [x] Define typed tool, request, response, metadata, and error contracts
- [x] Implement deterministic registry, lookup, and discovery
- [x] Enforce strict request, argument, response, and size validation
- [x] Implement timeout-aware execution and cancellation propagation
- [x] Normalize failures and implement safe structured execution logging
- [x] Project registry definitions into FastMCP
- [x] Add unit, adapter, API, and MCP protocol tests

## Phase 3 - Provider Router (complete and accepted)

- [x] Define provider-neutral models, lifecycle port, and safe errors
- [x] Implement Cerebras, NVIDIA, and OpenRouter adapters
- [x] Implement configured priority, retries, failover, and streaming boundary
- [x] Implement provider health, latency, and last-success/failure state
- [x] Add typed secret configuration and allowlisted provider logging
- [x] Add offline routing, adapter, configuration, health, error, and log tests
- [x] Integrate provider lifecycle without changing Phase 1 or Phase 2 interfaces
- [x] Receive owner approval to implement Phase 4 Stock Price Tool scope

## Phase 4 - Core Tool Framework and Stock Price Tool (complete; awaiting acceptance)

### Framework

- [x] Define the common `BaseTool` lifecycle
- [x] Implement `ToolManager` automatic registration and lifecycle rollback
- [x] Reuse MCP Core validation, execution, response, errors, logging, and timeout behavior
- [x] Add typed tool metadata through immutable definitions
- [x] Add in-memory aggregate execution metrics
- [x] Add typed health snapshots and concurrent manager status inspection
- [x] Keep tool domain and application layers independent of FastAPI/FastMCP

### Stock Price Tool

- [x] Define strict symbol input and normalized quote output
- [x] Implement Yahoo Finance as configured primary
- [x] Implement Alpha Vantage as optional configured fallback
- [x] Return current price, company, currency, exchange, high, low, open, previous close, market status, and timestamp when supplied
- [x] Implement configured timeout, retries, backoff, cache duration, cache size, and provider priority
- [x] Implement successful-response-only per-symbol cache and request coalescing
- [x] Implement normalized invalid-symbol, timeout, network, authentication, rate-limit, unavailable, and invalid-response handling
- [x] Register `stock_price` automatically with MCP discovery
- [x] Add stock provider health checks
- [x] Add allowlisted stock provider logging without symbols, keys, URLs, or payloads
- [x] Validate HTTPS origins and prevent path authority overrides and traversal
- [x] Keep the Phase 3 LLM router independent and unchanged

### Tests and documentation

- [x] Test registration and MCP discovery
- [x] Test successful execution and normalized response
- [x] Test invalid syntax and unknown symbols
- [x] Test retries, priority, failover, and caching
- [x] Test network failure and timeout handling
- [x] Test response validation and response-size limits
- [x] Test health, lifecycle, and metrics
- [x] Test Yahoo Finance and Alpha Vantage adapters offline
- [x] Test configuration safety and secret masking
- [x] Test structured log redaction
- [x] Preserve all Phase 1 through Phase 3 tests
- [x] Run the complete suite: 75 of 75 passing
- [x] Run dependency integrity: no broken requirements
- [x] Update required project documentation
- [ ] Project-owner acceptance of Phase 4

## Phase 5 and later (not approved)

- [ ] Resolve Yahoo supported-data-contract and production licensing decision
- [ ] Approve an exact Phase 5 scope
- [ ] Evaluate agent orchestration and dashboard only after approval
- [ ] Design authentication, authorization, and inbound rate limiting
- [ ] Add persistence only from approved use cases
- [ ] Add readiness, scheduled health, concurrency, cost, and audit controls
- [ ] Add broader observability, packaging, CI/CD, deployment, and recovery
- [ ] Choose a software license and initial deployment trust boundary

## Open owner decisions

- [ ] Accept or request revisions to Phase 4
- [ ] Approve a supported stock-data source/license for production use
- [ ] Approve or revise Phase 5 scope
- [ ] Choose a software license
- [ ] Decide the initial deployment environment and trust boundary
