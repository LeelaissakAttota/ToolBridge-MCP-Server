# Task Register

This file tracks executable work. It does not authorize work by itself; phase changes require project-owner approval.

Status key: `[x]` complete, `[ ]` not started, `[-]` intentionally deferred.

## Phase 1 - Foundation

- [x] Create Python 3.12 virtual environment
- [x] Install and pin direct dependencies
- [x] Add environment-backed settings and safe example configuration
- [x] Create FastAPI service metadata and health endpoints
- [x] Mount FastMCP Streamable HTTP transport
- [x] Add the `system_status` diagnostic MCP tool
- [x] Add service endpoint smoke tests
- [x] Verify imports, dependency integrity, live startup, health, and MCP discovery
- [x] Initialize Git on `main`
- [-] Create initial commit (left to the project owner)

## Documentation foundation

- [x] Add the requested project governance and engineering documents
- [x] Add the `PROJECT_STATUS.md` text dashboard
- [x] Receive owner approval to begin Phase 2

## Phase 2 - MCP Core

### Contracts and registry

- [x] Define stable tool name and metadata conventions
- [x] Define typed input, output, request, response, and error contracts
- [x] Create a project-owned tool definition independent of FastMCP
- [x] Implement deterministic registration, lookup, and discovery
- [x] Reject duplicate tool names with a clear startup error
- [x] Project registry definitions into MCP discovery

### Validation and execution

- [x] Enforce strict execution-envelope and JSON validation
- [x] Enforce request and response byte limits
- [x] Enforce tool-specific input and output models
- [x] Forbid unknown arguments and hide rejected values in transport errors
- [x] Generate and return safe correlation identifiers
- [x] Implement per-tool timeout boundaries
- [x] Propagate cancellation and log it safely
- [x] Normalize unknown, validation, timeout, internal, and response failures
- [x] Prevent raw internal exceptions from reaching clients

### Logging and configuration

- [x] Define the execution logging port
- [x] Implement structured JSON start, success, and failure events
- [x] Exclude arguments, results, and exception messages from logs
- [x] Apply `TOOLBRIDGE_LOG_LEVEL` to execution logs
- [x] Add typed timeout and request/response-size settings
- [-] Add readiness endpoint (deferred until required external dependencies exist)

### Phase 2 tests and acceptance

- [x] Test registration, lookup, discovery ordering, duplicates, and metadata
- [x] Test valid, malformed, unknown, extra, non-JSON, and oversized input
- [x] Test success, timeout, cancellation, and internal failure
- [x] Test invalid and oversized output
- [x] Test logging allowlist and secret-value exclusion
- [x] Test MCP discovery schema and adapter execution
- [x] Automate the full MCP initialize, list-tools, and call-tool path
- [x] Verify the suite without provider credentials
- [x] Verify dependency integrity
- [x] Update architecture, changelog, status, testing, security, and decisions
- [ ] Project-owner acceptance of Phase 2

## Phase 3 - Core tools (not started)

Do not begin until owner approval identifies the exact tool scope.

- [ ] Select the first production tool and authoritative data source
- [ ] Complete tool-specific threat and privacy review
- [ ] Define typed input/output contract and operational limits
- [ ] Implement the tool behind the Phase 2 definition interface
- [ ] Add unit, failure, security, and MCP protocol tests
- [ ] Update documentation and status

## Later backlog (unapproved)

- [ ] Define provider interface and routing policy
- [ ] Evaluate live LLM providers and licensing
- [ ] Evaluate agent orchestration after deterministic tools and routing
- [ ] Define persistence requirements from actual use cases
- [ ] Design authentication and authorization
- [ ] Add rate limiting and security audit events
- [ ] Add broader metrics, traces, alerts, and dashboards
- [ ] Add packaging, CI/CD, deployment, rollback, and recovery workflows

## Open owner decisions

- [ ] Accept Phase 2 and approve or revise Phase 3 scope
- [ ] Identify the first approved production tool and data source
- [ ] Choose repository hosting and review platform
- [ ] Choose a license
- [ ] Decide initial deployment environment and trust boundary
