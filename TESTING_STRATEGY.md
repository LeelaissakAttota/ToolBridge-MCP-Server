# Testing Strategy

## Objectives

Testing must show that ToolBridge starts, preserves interfaces, validates requests and responses, routes providers predictably, protects secrets, bounds external work, preserves cancellation, and runs offline without credentials.

## Current state

Version `0.4.0` has **75 automated tests** across five layers:

- API and MCP protocol: service routes, initialize, discovery, and execution
- MCP Core: contracts, registry, validation, execution, timeout, cancellation, errors, and logs
- LLM Provider Router: selection, retries, failover, health, lifecycle, streaming, adapters, configuration, and logs
- Tool framework: registration, discovery, lifecycle, health, metrics, and automatic composition
- Stock Price Tool: routing, caching, retries, failover, adapters, invalid symbols, network and timeout failures, response validation, configuration, and log redaction

The API `TestClient` shares one application lifespan because the MCP session manager starts once per process. Default tests use fakes and `httpx.MockTransport`; they perform no stock or LLM provider network request.

## Running tests

```powershell
.\.venv\Scripts\Activate.ps1
python -m pytest -q -p no:cacheprovider
python -m pip check
```

Current verified result: **75 passed** and no broken requirements on 2026-08-06. One third-party `StarletteDeprecationWarning` does not fail the suite.

## Current behavioral coverage

| Responsibility | Covered behavior |
| --- | --- |
| Phase 1 compatibility | `/`, `/health`, `/docs`, lifespan, and `system_status` |
| MCP Core | Registry, discovery, strict input/output validation, sizes, timeout, cancellation, safe errors |
| LLM routing | Priority, retries, failover, health, streaming boundary, adapters, configuration, redaction |
| Tool framework | Base lifecycle, automatic registration, deterministic discovery, health, metrics, shutdown |
| Stock configuration | Defaults, environment nesting, priority, bounds, HTTPS, paths, required secret, masking |
| Stock routing | Primary success, authentication failover, retry exhaustion, invalid symbol, cache hit |
| Stock adapters | Yahoo normalization, Alpha normalization, status mapping, malformed and oversized responses |
| Resilience | Network errors, HTTP timeout, whole-tool timeout, response-contract violation |
| Security | Unsafe symbol rejection, response bounds, log allowlists, secret and payload absence |
| Health | Healthy, degraded, unavailable, and provider detail snapshots |

## Test layers and rules

### Unit and application tests

Use project-owned fakes for domain contracts, error mapping, routing, retry classification, cache behavior, metrics, and lifecycle. Keep clock, sleep, and provider outcomes deterministic.

### Adapter component tests

Use `httpx.MockTransport` to verify URL paths, query parameters, headers, payload normalization, status classification, timeouts, malformed responses, and response-size bounds. Never use real credentials.

### API and MCP protocol tests

Run the ASGI application in-process. Verify service paths, version, MCP initialization, discovery schemas, existing tool execution, and lifespan compatibility. Do not call live stock data from the default protocol suite.

### External contract tests

Real Yahoo, Alpha Vantage, Cerebras, NVIDIA, and OpenRouter tests remain opt-in, credential/network-gated, cost-bounded, and excluded from the default suite. Yahoo contract testing also requires an approved usage and licensing basis.

## Required coverage by risk

| Change | Minimum tests |
| --- | --- |
| New tool | Registration, discovery, input, success, output, error, timeout, health, logging |
| Stock adapter | Request mapping, success, invalid symbol, timeout/network, status errors, malformed/oversized response |
| Retry/cache policy | Eligibility, attempt count, failover, cache hit/expiry, cancellation |
| Configuration | Environment parsing, secrets, HTTPS origin, safe paths, bounds, priority |
| Security control | Rejected abuse input, bounded data, safe errors, forbidden fields absent |
| MCP change | Discovery schema, execution path, protocol compatibility |
| Deployment change | Startup, liveness, readiness, shutdown, rollback smoke test |

## Design rules

- Keep default tests deterministic, isolated, repeatable, credential-free, and offline.
- Assert both returned behavior and absence of sensitive fields.
- Never log or fixture real keys, customer data, investment accounts, or production prompts.
- Prove syntactically invalid inputs never reach an adapter.
- Prove retries and failover occur only for classified safe failures.
- Validate timestamp awareness or presence rather than wall-clock equality.
- Propagate cancellation.
- Re-run MCP protocol tests for every MCP SDK upgrade.

## Coverage interpretation

The suite behaviorally covers every Phase 4 requirement: registration, discovery, successful execution, invalid symbols, network failures, timeout handling, response validation, configuration, providers, health, logs, and metrics. A line-coverage dependency is not installed, so no percentage is claimed. Adding pinned coverage, formatter, linter, or type-checker tooling remains a separate workflow decision.

## Phase gate

Phase 4 implementation is complete and awaits owner acceptance. Phase 5 must not begin without explicit scope approval.

## Future automation

CI is not implemented. When approved, it should create a clean Python 3.12 environment, install `requirements.txt`, run the offline suite and `pip check`, then add approved formatting, typing, coverage, secret, dependency, and vulnerability checks.
