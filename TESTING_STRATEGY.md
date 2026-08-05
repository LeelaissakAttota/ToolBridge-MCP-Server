# Testing Strategy

## Objectives

Testing must show that ToolBridge starts, discovers correct tool contracts, validates requests and responses, handles failures predictably, preserves cancellation, and runs offline without provider credentials.

## Current state

Version `0.2.0` has 28 automated tests across three layers:

- **API and protocol:** Phase 1 service routes plus MCP initialize, list-tools, and call-tool over the mounted ASGI path
- **Core units:** definitions, registry, discovery, request/input validation, response validation, execution, timeout, cancellation, and normalized failures
- **Adapters:** MCP schema projection and execution plus structured logging allowlist behavior

The module-scoped API `TestClient` starts one application lifespan because one MCP session manager instance can be started only once per process.

## Running tests

```powershell
.\.venv\Scripts\Activate.ps1
python -m pytest
python -m pip check
```

For a concise run without pytest cache creation:

```powershell
python -m pytest -q -p no:cacheprovider
```

Current verified result: **28 passed** on 2026-08-05. FastAPI/Starlette's current test-client integration emits one third-party `StarletteDeprecationWarning`; it does not fail the suite.

## Current coverage by responsibility

| Responsibility | Covered behavior |
| --- | --- |
| Tool definitions | Valid and invalid names, typed schemas, timeouts |
| Registry | Unique registration, duplicate rejection, lookup, unknown tool, alphabetical discovery |
| Request validation | Valid envelope, non-JSON data, strict types, extra fields, size limit |
| Response validation | Valid output, wrong schema, extra/missing fields, size limit |
| Execution | Sync success, unknown tool, bad arguments, timeout, cancellation, internal exception, invalid result |
| Error safety | Stable codes/messages, retryability, correlation IDs, hidden internal messages |
| Logging | Allowlisted metadata only; no arguments, results, rejected values, or arbitrary messages |
| MCP adapter | Discovery input/output schemas, execution through core, strict extra-field rejection |
| MCP protocol | Initialize, `tools/list`, and `tools/call` through `/mcp/` |
| Phase 1 compatibility | `/`, `/health`, `/docs` composition, `system_status` name and fields |

## Test layers

### Unit tests

Use for contracts, registry behavior, validation, execution policy, error mapping, and deterministic tool logic. They must not use network access or real credentials.

### Component tests

Exercise the executor with fake handlers and adapters. Cover success, invalid inputs and outputs, timeouts, cancellation, retries only where approved, and safe failures.

### API integration tests

Run the ASGI application through an in-process client. Verify paths, status codes, response schemas, host rules, and lifecycle behavior.

### MCP protocol tests

Use JSON-RPC through the mounted Streamable HTTP application or the official client where a live server is appropriate. Verify initialize, list tools, call tool, schema rejection, error mapping, and shutdown.

### External-provider contract tests

When providers are added, keep their tests opt-in and credential-gated. The default suite must use fakes and remain offline.

### Deployment tests

When deployment exists, verify startup, liveness, readiness, authentication, authorization, tool execution, telemetry, graceful shutdown, and rollback.

## Required coverage by risk

| Change | Minimum tests |
| --- | --- |
| Tool contract | Valid, missing, malformed, extra, boundary, and oversized data |
| Tool implementation | Success, dependency failure, timeout, cancellation where possible, and safe output |
| Registry | Registration, discovery, duplicate, and unknown tool |
| MCP adapter or SDK upgrade | Discovery schema, strict rejection, execution, and full protocol path |
| Provider adapter | Mapping, authentication failure, rate limit, timeout, malformed response |
| Routing/failover | Priority, health state, retry eligibility, budget, and exhaustion |
| Security control | Authorized, unauthorized, forbidden, redaction, and abuse cases |
| Deployment change | Startup, health/readiness, shutdown, and rollback smoke test |

## Test design rules

- Tests must be deterministic, isolated, repeatable, and credential-free by default.
- Use fakes at external boundaries and assert stable public behavior.
- Never place secrets, customer data, or unrestricted production samples in fixtures.
- Each fixed defect receives a regression test.
- Test both returned data and the absence of sensitive data.
- For timestamps, validate format or bounds rather than exact clock values.
- Run MCP adapter and protocol tests for every MCP SDK upgrade because the strict input-model integration uses an isolated SDK internal seam.
- Async cancellation tests must prove cancellation is re-raised, not silently converted.
- Sync timeout tests must not assume the underlying worker thread can be forcibly terminated.

## Phase gates

Phase 2's documented quality gate is satisfied. Phase 3 must add tool-specific unit, security, component, and MCP protocol tests for every approved production tool. The default suite must continue to pass offline.

## Future automation

CI is not implemented. When approved, it should create a clean Python 3.12 environment, install `requirements.txt`, run all tests and `pip check`, and later add approved formatting, type, dependency, secret, and vulnerability checks.
