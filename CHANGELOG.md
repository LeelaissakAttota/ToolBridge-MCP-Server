# Changelog

All notable changes to this project are recorded here. The format follows Keep a Changelog principles, and releases use semantic versioning.

## [Unreleased]

No unreleased changes.

## [0.5.0] - 2026-08-06

### Added

- `website_reader` with public-destination validation, bounded HTTPS streaming, HTML boilerplate removal, and structured clean text
- `sql_query` with a database-neutral port, SQLite read-only/query-only execution, named parameters, row bounds, and progress timeout
- `csv_analysis` with confined paths, delimiter and column detection, inferred types, statistics, missing-value analysis, and preview
- `currency_converter` with configurable Frankfurter integration, multi-target conversion, bounded retries, cache, and request coalescing
- `hcl_curie_analysis` with analyze/summarize operations and existing LLM Provider Router integration
- Typed Phase 5 configuration and safe environment examples for every new tool
- Stable MCP error categories for website, database, file, currency-rate, and LLM-analysis failures
- Offline unit and protocol tests for all Phase 5 tools

### Changed

- Promoted package version from `0.4.0` to `0.5.0`.
- Expanded automatic MCP discovery from two to seven tools.
- Composed the Provider Router before managed tools so the LLM Analysis Tool can receive it without owning its lifecycle.
- Added Phase 5 as Remaining Core MCP Tools and moved the unimplemented agent/dashboard outcome to Phase 6.
- Preserved the Phase 4 framework architecture and all Phase 1-4 interfaces.

### Security

- Website URLs require credential-free HTTPS; non-public destinations, redirects, unsupported content, and oversized responses are rejected.
- SQL accepts only one conservative read-only statement, uses named parameters, opens SQLite files read-only, enables query-only mode, and interrupts long queries.
- CSV paths are confined beneath a configured root and file bytes, rows, columns, fields, and previews are bounded.
- Currency amounts and ISO codes are validated; provider responses and rates are bounded and only successful normalized rates are cached.
- LLM source text is treated as untrusted document data and remains excluded from logs.
- URLs, SQL, parameters, paths, filenames, CSV cells, prompts, content, provider bodies, and results remain outside structured logs and metrics.

### Testing

- Expanded the offline suite from 75 to 98 tests.
- Added registration, discovery, success, invalid-input, error, timeout, cache, response-contract, configuration, and security coverage for all five tools.
- Verified 98 tests pass, compilation succeeds, and `pip check` reports no broken requirements.

### Compatibility

- Existing HTTP routes, MCP transport, `system_status`, `stock_price`, MCP Core, Provider Router, and Phase 4 lifecycle behavior remain compatible.
- No dependency version changed and no dependency was added.
- No Dashboard, agent, authentication, CI/CD, deployment, or Phase 6 capability was implemented.

## [0.4.0] - 2026-08-06

### Added

- Reusable `BaseTool` lifecycle and `ToolManager` registration, health, startup, rollback, and shutdown
- In-memory tool execution counts, outcome totals, durations, and status snapshots
- `stock_price` MCP tool with strict symbol input and normalized quote output
- Yahoo Finance chart adapter and optional Alpha Vantage `GLOBAL_QUOTE` fallback
- Configuration for stock provider priority, timeouts, retries, backoff, cache duration, cache size, endpoints, paths, response limits, and health probes
- Successful-response-only per-symbol cache with concurrent request coalescing
- Structured stock-provider logging with an explicit safe-field allowlist
- Offline framework, service, adapter, configuration, health, metrics, and security tests

### Changed

- Promoted package version from `0.3.0` to `0.4.0`.
- Composed `system_status` and `stock_price` through the common managed-tool lifecycle.
- Extended application lifespan to initialize and close managed tool resources.
- Expanded MCP discovery from one tool to `stock_price` and `system_status`.
- Expanded the safe environment example with complete Stock Price Tool configuration.

### Security

- Stock symbols are normalized, length-bounded, and pattern-restricted before network access.
- Stock provider origins require safe HTTPS URLs without credentials, queries, fragments, or embedded paths.
- Relative provider paths cannot override authorities or traverse directories; redirects are disabled.
- Upstream bodies, cache entries, retries, timeouts, and backoff are bounded.
- API keys, symbols, URLs, payloads, responses, and exception messages are excluded from stock logs.
- Alpha Vantage credentials use `SecretStr` and are unwrapped only during adapter composition.

### Testing

- Expanded the offline suite from 56 to 75 tests.
- Added registration, discovery, success, invalid-symbol, network, timeout, response-validation, retry, failover, cache, health, metrics, adapter, configuration, and log-redaction coverage.
- Verified 75 tests pass and `pip check` reports no broken requirements.

### Compatibility

- Existing HTTP paths, `system_status`, MCP Core behavior, and LLM Provider Router behavior remain compatible.
- No dependency version changed and no stock SDK was added.
- No Phase 5 or later capability was implemented.

## [0.3.0] - 2026-08-06

### Added

- Provider-neutral domain contracts for generation, streaming, model discovery, token usage, health, status, and normalized errors
- Replaceable `BaseProvider` lifecycle interface
- Cerebras, NVIDIA, and OpenRouter HTTP adapters
- Configuration-driven provider priority, endpoints, credentials, models, timeouts, retries, token limits, temperature, and prompt limits
- Active-provider routing with bounded retries, capped exponential backoff, and category-aware failover
- Concurrent on-demand provider health checks and immutable status snapshots
- Safe streaming failover before the first emitted chunk
- Structured provider JSON logging with a strict metadata allowlist
- Offline provider configuration, routing, adapter, health, streaming, error, limit, and logging tests

### Changed

- Promoted provider routing to Phase 3 and moved Core Tools to Phase 4 by owner direction.
- Promoted package version from `0.2.0` to `0.3.0`.
- Extended application lifespan management to initialize and close provider resources.
- Expanded the safe environment example with disabled provider configuration.

### Security

- Provider API keys use `SecretStr` and are unwrapped only at outbound adapter composition.
- Enabled provider endpoints require HTTPS.
- Keys, prompts, responses, authorization headers, and vendor error bodies are excluded from provider logs and normalized errors.
- Provider request bytes, prompt bytes, maximum tokens, timeouts, and retries are bounded.
- Every provider remains disabled by default.

### Testing

- Expanded the offline suite from 28 to 56 tests.
- Added coverage for selection, failover, retry eligibility, health state, configuration, all provider adapters, streaming boundaries, error mapping, and log redaction.

### Compatibility

- Existing FastAPI paths, MCP transport, MCP schemas, and `system_status` behavior remain unchanged.
- No dependency versions changed and no provider SDK was added.
- No provider-backed MCP tool was introduced.

## [0.2.0] - 2026-08-05

### Added

- Framework-independent MCP Core contracts for tool inputs, outputs, definitions, metadata, execution requests/responses, and error categories
- Deterministic tool registry with unique registration, lookup, and discovery
- Strict request, JSON, argument, and request-size validation
- Strict output-schema, JSON-encoding, and response-size validation
- Timeout-aware execution service with cancellation propagation
- Safe normalized error responses with correlation identifiers
- FastMCP adapter that projects core definitions into MCP discovery and execution
- Strict FastMCP generated argument models that forbid extra fields and hide rejected values
- Structured JSON execution logging with an explicit safe-field allowlist
- Typed timeout and request/response limit settings
- Typed `system_status` input/output definition while preserving its Phase 1 interface
- Unit tests for registry, validation, execution, errors, cancellation, timeout, logging, and MCP adapter behavior
- Automated MCP initialize, `tools/list`, and `tools/call` protocol test

### Changed

- Promoted package version from `0.1.0` to `0.2.0`.
- Routed the existing `system_status` MCP tool through the registry and execution core.
- Expanded architecture, roadmap, testing, security, status, task, and README documentation for Phase 2.

### Security

- Tool arguments and results are excluded from ToolBridge execution logs.
- Raw internal exception messages are not returned to MCP clients.
- Input and output sizes are bounded at the core execution boundary.
- Rejected FastMCP input values are hidden from generated validation errors.

### Compatibility

- `GET /`, `GET /health`, `GET /docs`, `/mcp/`, and the `system_status` name and output fields remain unchanged.
- No dependency versions changed.

## [0.1.0] - 2026-08-05

### Added

- Python 3.12 project foundation and local virtual environment setup
- Pinned direct runtime and test dependencies
- FastAPI control plane with `/`, `/health`, and generated `/docs`
- FastMCP server mounted at `/mcp/` using stateless Streamable HTTP and JSON responses
- `system_status` diagnostic MCP tool
- Typed environment configuration using `TOOLBRIDGE_` variables and optional `.env`
- Endpoint smoke tests
- Safe Git ignore rules and environment example
- Project governance and engineering documentation
- Git repository initialized on the `main` branch

### Verified

- Dependency integrity, application import, Uvicorn startup, health response, MCP discovery, and endpoint smoke tests
