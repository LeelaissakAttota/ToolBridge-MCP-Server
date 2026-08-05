# Task Register

This file tracks executable work. It does not authorize work by itself; phase changes require project-owner approval.

Status key: `[x]` complete, `[ ]` not started, `[-]` intentionally deferred.

## Phase 1 - Foundation (complete)

- [x] Create Python 3.12 virtual environment
- [x] Install and pin direct dependencies
- [x] Add environment-backed settings and safe example configuration
- [x] Create FastAPI service metadata and health endpoints
- [x] Mount FastMCP Streamable HTTP transport
- [x] Add the `system_status` diagnostic MCP tool
- [x] Add service endpoint smoke tests
- [x] Verify imports, dependency integrity, live startup, health, and MCP discovery
- [x] Initialize Git on `main`
- [x] Create the initial repository commit
- [x] Configure the GitHub `origin` remote
- [x] Synchronize local `main` with `origin/main`

## Documentation foundation

- [x] Add project governance and engineering documents
- [x] Add the `PROJECT_STATUS.md` text dashboard
- [x] Receive owner approval to begin Phase 2

## Phase 2 - MCP Core (complete)

- [x] Define typed tool, request, response, metadata, and error contracts
- [x] Implement deterministic registration, lookup, and discovery
- [x] Enforce strict request, argument, response, and size validation
- [x] Implement timeout-aware execution and cancellation propagation
- [x] Normalize failures without leaking internal exceptions
- [x] Implement safe structured execution logging
- [x] Project registry definitions into FastMCP
- [x] Add unit, adapter, API, and full MCP protocol tests
- [x] Verify the suite without provider credentials
- [x] Receive owner approval to begin the revised Phase 3 scope

## Phase 3 - Provider Router (complete; awaiting owner acceptance)

### Domain and application

- [x] Define normalized generation, streaming, model, usage, health, and status contracts
- [x] Define stable provider error categories and safe messages
- [x] Define the replaceable `BaseProvider` lifecycle interface
- [x] Implement configured priority and active-provider selection
- [x] Implement bounded retries and capped exponential backoff
- [x] Implement category-aware failover
- [x] Prevent retry and failover for invalid requests
- [x] Prevent streaming failover after the first emitted chunk

### Provider adapters

- [x] Implement Cerebras adapter
- [x] Implement NVIDIA adapter
- [x] Implement OpenRouter adapter
- [x] Normalize model discovery, generation, streaming, usage, and errors
- [x] Isolate provider HTTP behavior behind project-owned contracts
- [x] Use injectable HTTP transports for offline tests

### Health, configuration, security, and lifecycle

- [x] Implement concurrent on-demand provider health checks
- [x] Track status, latency, last success, last failure, and error category
- [x] Move provider keys, URLs, models, timeouts, retries, tokens, temperature, paths, and priority into typed settings
- [x] Require HTTPS and validate enabled-provider credentials and models
- [x] Keep every provider disabled by default
- [x] Add allowlisted JSON provider logging
- [x] Exclude API keys, prompts, responses, and vendor error bodies from logs
- [x] Initialize and close provider resources through application lifespan

### Phase 3 tests and documentation

- [x] Test provider selection, active state, failover, retries, and exhaustion
- [x] Test health checks and status history
- [x] Test nested configuration, bounds, HTTPS, and secret masking
- [x] Test all three provider adapters offline
- [x] Test HTTP error mapping, malformed responses, token limits, and prompt limits
- [x] Test streaming normalization and failover boundary
- [x] Test provider logging redaction
- [x] Preserve the full Phase 1 and Phase 2 test suite
- [x] Update architecture, roadmap, status, changelog, decisions, testing, security, and README documentation
- [ ] Project-owner acceptance of Phase 3

## Phase 4 - Core tools (not started)

Do not begin until owner approval identifies the exact tool scope.

- [ ] Select the first production tool and authoritative data or model source
- [ ] Complete tool-specific threat, privacy, licensing, and cost review
- [ ] Define typed input/output contract and operational limits
- [ ] Implement the tool behind the Phase 2 definition interface
- [ ] Use the Phase 3 provider router only when the approved tool requires it
- [ ] Add unit, failure, security, provider, and MCP protocol tests
- [ ] Update documentation and status

## Later backlog (unapproved)

- [ ] Evaluate agent orchestration after tools and routing stabilize
- [ ] Define persistence requirements from actual use cases
- [ ] Design authentication and authorization
- [ ] Add inbound rate limiting and security audit events
- [ ] Add provider concurrency, budgets, scheduled health, and readiness
- [ ] Add broader metrics, traces, alerts, and dashboards
- [ ] Add packaging, CI/CD, deployment, rollback, and recovery workflows

## Open owner decisions

- [ ] Accept Phase 3 and approve or revise Phase 4 scope
- [ ] Identify the first approved production tool and source
- [x] Repository hosting and review platform selected: GitHub
- [ ] Choose a license
- [ ] Decide initial deployment environment and trust boundary
