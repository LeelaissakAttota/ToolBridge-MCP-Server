# Testing Strategy

## Objectives

Testing must show that ToolBridge starts, preserves interfaces, validates requests and responses, bounds external work, protects secrets and sensitive inputs, routes providers predictably, preserves cancellation, and runs offline without credentials.

## Current state

Version `0.5.0` has **98 automated tests** across these layers:

- API and MCP protocol: service routes, initialize, discovery of seven tools, and execution
- MCP Core: contracts, registry, strict input/output validation, sizes, timeout, cancellation, safe errors, and logs
- LLM Provider Router: selection, retries, failover, health, lifecycle, streaming, adapters, configuration, and redaction
- Tool framework and Stock Price: automatic registration, lifecycle, metrics, providers, cache, retries, failover, adapters, and security
- Phase 5 tools: Website Reader, SQL Query, CSV Analysis, Currency Converter, and HCL Curie / LLM Analysis

Default tests use fakes, `httpx.MockTransport`, temporary SQLite databases, and temporary CSV files. They perform no live website, stock, exchange-rate, or LLM request.

## Running tests

```powershell
.\.venv\Scripts\Activate.ps1
python -m pytest -q -p no:cacheprovider
python -m pip check
```

Current verified result: **98 passed** and no broken requirements on 2026-08-06. One third-party `StarletteDeprecationWarning` does not fail the suite.

## Current behavioral coverage

| Responsibility | Covered behavior |
| --- | --- |
| Compatibility | Existing HTTP paths, MCP initialize, deterministic discovery, `system_status`, Stock Price, and Provider Router tests |
| Website Reader | HTML extraction, boilerplate removal, URL normalization, public-IP/allowlist control, status errors, oversized response, lifecycle |
| SQL Query | Parameterized success, row truncation, forbidden statements/comments/separators, missing database, duplicate columns, progress timeout |
| CSV Analysis | Columns, delimiter, types, numeric statistics, missing values, preview, traversal, missing/malformed files, scan limit |
| Currency Converter | Multi-target conversion, request mapping, retry, cache, input validation, malformed provider response |
| LLM Analysis | Provider Router use, structured output, untrusted-document wrapper, configured input limit, unavailable routing, health |
| Framework | Automatic registration and strict discovery schemas for all seven tools |
| Configuration | Defaults, nested environment models, HTTPS origins, safe paths, bounds, enablement, and provider selection |
| Security | SSRF checks, read-only SQL, path confinement, bounded data, safe errors, secret/payload logging exclusions |

## Required coverage by risk

Every new tool must cover registration, discovery schema, success, invalid input, normalized errors, timeout or bounded cancellation behavior, response contract, health, logs, and metrics. Adapter tests must verify request mapping, status/transport failures, malformed/oversized responses, and no live credentials. Configuration tests must reject insecure origins, paths, duplicates, missing required values, and out-of-bound settings.

## Design rules

- Keep default tests deterministic, isolated, credential-free, network-free, and cost-free.
- Assert returned behavior and the absence of sensitive fields.
- Prove invalid input does not reach network, database, or filesystem adapters.
- Retry only failures classified safe; preserve cancellation.
- Use temporary files and databases with no customer or production data.
- Treat website, CSV, database, exchange-rate, and LLM output as untrusted test data.
- Re-run MCP protocol tests for any MCP SDK change.

## Coverage interpretation

The suite behaviorally covers every Phase 5 requirement. No line-coverage package is installed, so no numerical code-coverage claim is made. Adding coverage, formatting, linting, typing, secret scanning, or vulnerability tooling remains a separately approved workflow decision.

## External contract tests

Live Yahoo, Alpha Vantage, Frankfurter, website, Cerebras, NVIDIA, and OpenRouter tests remain opt-in, network/credential/terms-gated, cost-bounded, and excluded from the default suite. Production database and CSV tests require approved synthetic data and permissions.

## Phase gate

Phase 5 implementation is complete and awaits owner acceptance. Phase 6 must not begin without explicit scope approval.
