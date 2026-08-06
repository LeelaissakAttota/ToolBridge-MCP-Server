# Testing Strategy

## Objectives

Testing must prove that ToolBridge starts, preserves MCP/HTTP contracts, validates boundaries, bounds external work, protects secrets and sensitive inputs, routes providers predictably, reports readiness correctly, renders safe monitoring data, preserves cancellation, and runs offline without credentials.

## Current state

Version `0.6.0` has **112 automated tests** across:

- API, lifespan, liveness, readiness, safe operations snapshot, MCP initialize/discovery/execution
- MCP Core registry, strict validation, sizes, timeout, cancellation, safe errors, and logs
- Provider Router selection, retries, failover, health, streaming, lifecycle, adapters, configuration, usage observation, and redaction
- Tool framework, Stock Price, Website Reader, SQL Query, CSV Analysis, Currency Converter, and HCL Curie / LLM Analysis
- Phase 6 metrics, bounded logs, cost estimation, startup/readiness state, provider/tool monitoring, local dashboard client, configuration, and dashboard components

Default tests use fakes, `httpx.MockTransport`, temporary SQLite databases, and temporary CSV files. They perform no live stock, website, currency, or LLM request and incur no API cost.

## Running tests

```powershell
.\.venv\Scripts\Activate.ps1
python -m pytest -q -p no:cacheprovider tests
python -m pip check
```

Current verified result on 2026-08-06: **112 passed**, no broken requirements, and one non-failing third-party `StarletteDeprecationWarning`.

## Phase 6 behavioral coverage

| Responsibility | Covered behavior |
| --- | --- |
| Dashboard components | All required sections render from an immutable snapshot; tables/charts are invoked without mutations |
| Dashboard client | Only local `GET /operations/snapshot`, no authorization header, strict JSON validation, safe errors |
| Liveness/readiness | Existing `/health`, ready `200`, local checks, provider-router/tool-manager lifecycle state |
| Operations API | Three providers, seven tools, system/readiness/metrics/cost/log schema |
| Tool monitoring | registration, cached lifecycle health, execution count, average/last duration, last completion |
| Provider monitoring | configured/disabled visibility, priority, active/failover state, status, latency, usage |
| Metrics | requests, success/failure, error categories, response timing, tool/provider usage |
| Cost | normalized tokens, configured input/output pricing, streaming without invented token totals |
| Logs | bounded newest-first buffer, safe fields, warning/error categories, no exception text |
| Configuration | loopback-only dashboard URL, bounds, nested price environment values |
| Compatibility | unchanged seven-tool MCP discovery and all Phase 1-5 tests |

## Design rules

- Keep default tests deterministic, isolated, credential-free, network-free, and cost-free.
- Assert behavior and the absence of sensitive fields.
- Prove operational reads do not call external providers, files, databases, or websites.
- Use dependency injection and supported public interfaces at adapters.
- Preserve cancellation and retry only failures classified safe.
- Use temporary synthetic data; never production/customer data.
- Re-run MCP protocol tests for MCP SDK or adapter changes.
- Treat dashboard and operations JSON as public contracts.

## Coverage interpretation

The suite behaviorally covers every Phase 6 requirement. No line-coverage package is installed, so no numerical code-coverage percentage is claimed. Formatting, linting, typing, secret scanning, dependency scanning, and vulnerability tooling remain separately approved workflow decisions.

## External contract tests

Live Yahoo, Alpha Vantage, Frankfurter, website, Cerebras, NVIDIA, and OpenRouter tests remain opt-in and network/credential/terms/cost gated. Production database and CSV tests require approved synthetic data and permissions. Dashboard public-network testing is prohibited until an authentication design is approved.

## Phase gate

Phase 6 implementation is complete and awaits owner acceptance. Phase 7 must not begin without explicit scope approval.
