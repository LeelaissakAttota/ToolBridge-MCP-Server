# Testing Strategy

## Objectives

Testing must show that ToolBridge starts, preserves MCP interfaces, validates requests and responses, routes providers predictably, protects secrets, preserves cancellation, and runs offline without provider credentials.

## Current state

Version `0.3.0` has 56 automated tests across four layers:

- **API and MCP protocol:** service routes plus MCP initialize, list-tools, and call-tool
- **MCP Core units:** contracts, registry, validation, execution, timeout, cancellation, errors, and logging
- **Provider application:** selection, active state, retries, failover, health snapshots, lifecycle, and streaming policy
- **Provider adapters and infrastructure:** configuration, HTTP mapping, model discovery, streaming, error normalization, limits, and log allowlists

The module-scoped API `TestClient` starts one application lifespan because one MCP session manager instance can be started only once per process. Provider tests use fakes and `httpx.MockTransport`; the default suite performs no provider network calls.

## Running tests

```powershell
.\.venv\Scripts\Activate.ps1
python -m pytest -q -p no:cacheprovider
python -m pip check
```

Current verified result: **56 passed** on 2026-08-06. FastAPI/Starlette's current test-client integration emits one third-party `StarletteDeprecationWarning`; it does not fail the suite.

## Current coverage by responsibility

| Responsibility | Covered behavior |
| --- | --- |
| Phase 1 compatibility | `/`, `/health`, `/docs`, application lifespan, and `system_status` |
| MCP Core | Registry, discovery, strict validation, output limits, execution, timeout, cancellation, safe errors |
| Provider configuration | Defaults, nested environment values, secret masking, required credentials/model, HTTPS, priority validation |
| Provider interface | Initialization, health, model listing, generation, streaming, and close behavior |
| Routing | Primary selection, active-provider update, retry count, safe failover, exhaustion, no-provider behavior |
| Health monitoring | Concurrent probes, status, latency, last-success, last-failure, and error category |
| Streaming | SSE normalization, failover before first chunk, and no failover after partial output |
| HTTP adapters | Cerebras, NVIDIA, and OpenRouter request/response mapping and bearer authentication |
| Provider errors | Invalid request, authentication, rate limit, timeout, unavailable, and malformed response |
| Resource limits | Maximum token and prompt byte enforcement |
| Logging security | Explicit field allowlists; keys, prompts, responses, and arbitrary messages excluded |

## Test layers

### Unit tests

Use for domain contracts, configuration, registry behavior, validation, execution policy, error mapping, health state, retry classification, and deterministic routing logic. They must not use real credentials or network access.

### Component tests

Exercise `ProviderRouter` with fake providers and provider adapters with `httpx.MockTransport`. Cover selection, retries, failover, health, lifecycle, malformed responses, limits, and safe failures.

### API integration tests

Run the ASGI application through an in-process client. Verify paths, status codes, response schemas, unchanged liveness behavior, and lifecycle compatibility with providers disabled.

### MCP protocol tests

Use JSON-RPC through the mounted Streamable HTTP application. Verify initialize, list tools, call tool, schema rejection, error mapping, and shutdown.

### External-provider contract tests

Real Cerebras, NVIDIA, and OpenRouter tests remain opt-in, credential-gated, cost-bounded, and excluded from the default suite. They require explicit approval and must never expose keys, prompts, or provider content in test output.

## Required coverage by risk

| Change | Minimum tests |
| --- | --- |
| Provider adapter | Request mapping, model discovery, streaming, authentication, rate limit, timeout, malformed response |
| Routing/failover | Priority, active state, retry eligibility, exhaustion, health recovery, and stream boundary |
| Provider configuration | Environment parsing, secret masking, required fields, HTTPS, bounds, and priority |
| Security control | Redaction, forbidden fields, bounded data, and safe error messages |
| MCP change | Discovery schema, execution, and full protocol path |
| Deployment change | Startup, liveness, readiness, shutdown, and rollback smoke test |

## Test design rules

- Keep default tests deterministic, isolated, repeatable, credential-free, and offline.
- Use project-owned fakes at application boundaries and `httpx.MockTransport` at HTTP boundaries.
- Never place real secrets, customer data, or production prompts in fixtures.
- Assert both returned behavior and the absence of sensitive data.
- Validate timestamp format or presence rather than exact clock values.
- Prove invalid requests are not retried or failed over.
- Permit streaming failover only before the first emitted chunk.
- Re-run MCP adapter and protocol tests for every MCP SDK upgrade.
- Propagate cancellation rather than translating it to a normal failure.

## Coverage interpretation

The suite covers every Phase 3 requirement behaviorally: provider selection, failover, retries, health monitoring, configuration, normalized errors, all three provider adapters, streaming, lifecycle, limits, and logging redaction. A line-coverage dependency is not installed, so no percentage is claimed. Adding a pinned coverage tool is a separate tooling decision.

## Phase gates

Phase 3's implementation gate is satisfied and awaits owner acceptance. Phase 4 must not begin until one exact production tool and its provider/data, permissions, cost, privacy, and test boundaries are approved.

## Future automation

CI is not implemented. When approved, it should create a clean Python 3.12 environment, install `requirements.txt`, run the full offline suite and `pip check`, and add approved formatting, typing, coverage, dependency, secret, and vulnerability checks.
