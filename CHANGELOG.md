# Changelog

All notable changes to this project are recorded here. The format follows Keep a Changelog principles, and releases use semantic versioning.

## [Unreleased]

### Added

- PostgreSQL is now the only `sql_query` backend; SQLite is rejected in configuration. Local setup: a `toolbridge` database with a `SELECT`-only `toolbridge_ro` role and the `books`/`loans` demo tables.
- PostgreSQL adapter for `sql_query` (`TOOLBRIDGE_PHASE5__SQL_QUERY__BACKEND=postgres`), using the existing read-only port, asyncpg, bound parameters, row limits, and statement timeout. Default suite: 239 passed, 1 skipped live PostgreSQL test.
- tests for the Claude Desktop stdio bridge (including an end-to-end stdio check), Tool Playground helpers, simplified tool panels, and `.env.example` loading (suite now 228 tests)
- package metadata so `pip install -e .` works
- README sections for the Tool Playground, guided provider setup with Auto (cheapest) model choice, Claude Desktop setup, demo video, and fresh screenshots

### Fixed

- copying `.env.example` to `.env` no longer breaks startup (blank values fall back to defaults)
- the dashboard's SQL/CSV panels now use the API-configured database and CSV root first

### Security

- pillow 13.0.0 (via streamlit 1.66.1), resolving advisories against pillow 12.3.0

- Bundled demo data: `data/demo.db` (companies and financials) and `data/csv` samples, used as the defaults. Rebuild them with `scripts/seed_demo_data.py`.
- Optional `TOOLBRIDGE_MCP_AUTH_TOKEN` bearer-token protection for `/mcp`, plus `TOOLBRIDGE_MCP_ALLOWED_HOSTS`/`_ORIGINS` for reverse-proxy hostnames. Both are off by default.
- `TOOLBRIDGE_PROVIDER_STREAM_TIMEOUT_SECONDS` (default 120) sets an overall deadline for streamed LLM responses.
- mypy configuration in `pyproject.toml` and a CI type-check step.
- The dashboard History page now shows real in-memory tool usage and recent events.

### Changed

- `website_reader` now follows up to `MAX_REDIRECTS` (default 5) HTTPS redirects. Every hop is re-validated (scheme, port, credentials, allowlist, public IP). This supersedes the earlier "redirects are rejected" behaviour.
- `website_reader` pins each TCP connection to the IP address that passed validation, which closes the DNS-rebinding window. TLS SNI and the Host header are unchanged.
- The dashboard navigation drops the placeholder Chat and Agent pages and the incorrect CrewAI reference. HTML fragments are escaped, and `width=` replaces the removed `use_container_width`.
- API tests use an in-repo `httpx.ASGITransport` client instead of Starlette's deprecated `TestClient`.
- The live MCP smoke script accepts `--port`/`--url`/`--token`.

### Fixed

- `sql_query` `parameters` is optional over MCP. Previously `default_factory` fields were advertised as required.
- SQLite value and statement length are capped, which prevents memory exhaustion from functions such as `zeroblob`.
- The SQL read-only validator tokenizes queries, so keywords inside string literals and `replace()` calls are no longer rejected.
- Streaming no longer assumes provider iterators implement `aclose()`, and it tolerates a missing `request_id`. LLM tool health accepts plugin providers with string names.

- RW-002: MCP string-enum arguments advertised by tool schemas are now accepted at the JSON transport boundary and converted to typed domain enums

### Security

- retained strict validation for non-enum inputs, unknown-field rejection, bounded request/response validation, and safe validation errors

### Testing

- added ten offline regressions covering valid and invalid enum strings, schema/transport compatibility, unknown fields, and unrelated strict input behavior

## [1.1.0] - 2026-08-06

### Added

- self-registering `ProviderPluginRegistry`, public `register_provider()`, and automatic adapter-package discovery
- generic provider configuration for future adapters while retaining built-in environment compatibility
- normalized capability catalog for chat, reasoning, streaming, embeddings, image/audio generation, tool/function use, vision, long context, JSON mode, web search, and code generation
- rich startup model discovery metadata: provider, cost/free status, context, capabilities, latency, health, availability, quality, and discovery time
- capability/task-aware `ModelRankingEngine` with dynamic ranking and optional explicit priority
- process-local `ProviderBudgetManager` with daily, monthly, and per-request limits, soft deprioritization, hard exclusion, and failover
- provider health scoring with request/success/error/retry counts, latency, last success/failure, deprioritization, and recovery
- provider/model operations fields and expanded read-only Streamlit provider dashboard
- nine offline tests for plugin registration/discovery, generic configuration, ranking, budgets, smart routing, budget failover, and startup discovery

### Changed

- promoted the working package and operational version from `1.0.0` to `1.1.0`
- changed empty provider priority to dynamic model ranking; configured priority remains supported
- replaced the hardcoded three-provider factory switch with registry-driven composition
- enabled providers now authenticate/health-check and discover models during startup; disabled default startup remains network-free
- expanded normalized provider identifiers to accept arbitrary validated plugin IDs while retaining `ProviderName` built-in compatibility constants

### Security

- API keys remain typed secrets and are unwrapped only at adapter construction
- model prices and all budget limits are configuration-driven; no prices or credentials are hardcoded
- provider telemetry remains allowlisted and excludes prompts, output, response bodies, endpoints, headers, and secrets
- hard budget limits prevent routing to an over-budget provider and permit safe fallback

### Compatibility

- no MCP Core, MCP tool name/input/output schema, existing HTTP path, or deployment topology changed
- Cerebras, NVIDIA, OpenRouter, and their public adapter imports remain compatible
- no new MCP tool, authentication system, public exposure, deployment workflow, commit, push, or tag was created

## [1.0.0] - 2026-08-06

### Added

- multi-stage Python 3.12 slim Dockerfile with pinned runtime dependencies, fixed non-root identity, application healthcheck, and persistent data volume
- hardened `docker-compose.yml` for API and Streamlit dashboard with loopback-only host publication, shared loopback namespace, read-only filesystems, dropped capabilities, and health checks
- `.dockerignore`, runtime/development dependency split, Ruff configuration, and pinned development requirements
- GitHub Actions workflow for dependency integrity, formatting, lint, all tests, local startup, image build, Compose smoke validation, JUnit artifact, and tagged image/SHA-256 artifacts
- secret-safe release verification script for version, health, readiness, three providers, seven tools, dashboard health, and monitoring-key safety
- installation, deployment, user, API, troubleshooting, contribution, production checklist, known-limitations, and v1.0.0 release-note documents
- two unit tests for release monitoring-payload safety

### Changed

- promoted package and operational version from `0.6.0` to `1.0.0`
- changed the default displayed phase to Phase 7 - Deployment & v1.0.0 Release
- moved pytest from runtime requirements to pinned development requirements
- adopted Ruff as the deterministic formatter/import organizer/linter and mechanically formatted the Python tree
- synchronized roadmap, tasks, rules, architecture, standards, testing, security, deployment, Git workflow, decisions, status, and README with the release state

### Security

- kept `.env` outside Git and Docker build context and retained loopback defaults in `.env.example`
- published Compose API/dashboard ports only to host `127.0.0.1`
- configured non-root containers, read-only roots, bounded temporary storage, all capabilities dropped, and `no-new-privileges`
- retained the dashboard's application-enforced loopback API URL by sharing the API network namespace
- added release validation that rejects secret-, prompt-, and tool-payload-bearing keys in operational output
- did not add authentication or authorize direct public exposure

### Testing

- expanded the offline suite from 112 to 114 tests
- verified dependency integrity, Ruff format/lint, API/MCP integration, dashboard components/startup, release validation, and Compose configuration
- retained one documented third-party `StarletteDeprecationWarning` without suppression or workaround

### Operations

- documented supported single-host loopback deployment, configuration, data persistence, health/readiness, rollback, troubleshooting, and production acceptance
- CI validates and packages tagged image artifacts but intentionally does not publish or deploy
- Phase 7 was subsequently approved, committed as `86cc575`, tagged `v1.0.0`, and pushed to `origin`

### Investigated

- Traced the remaining `StarletteDeprecationWarning` to Starlette `1.4.1`: `starlette/testclient.py:36` cannot import optional `httpx2`, intentionally falls back to compatible `httpx==0.28.1`, and emits the warning at `starlette/testclient.py:47`. The displayed location is FastAPI's re-export at `fastapi/testclient.py:1`, reached by `tests/test_api.py:6`.
- No warning suppression, application workaround, dependency patch, or test-client replacement was added. The fallback is operational and all tests pass; migrate to `httpx2` only through a separately reviewed dependency update with a full regression run.

## [0.6.0] - 2026-08-06

### Added

- professional read-only Streamlit dashboard with System, Provider, MCP Tool, Metrics, Cost, and Log sections
- lifecycle-aware `/ready` endpoint with `200`/`503` responses and no external probes
- bounded secret-free `/operations/snapshot` endpoint for local dashboard consumption
- startup registry/version validation and categorized lifecycle error reporting
- process-local operational models/service for system, provider, tool, request, cost, readiness, and safe-log views
- provider generation usage observer for non-streaming token totals and streaming request counts
- configurable per-provider input/output token cost rates
- configurable log capacity, recent-log limit, local dashboard API URL/timeout, and readiness policy
- cached tool lifecycle monitoring and last-execution timestamps
- dashboard client, metrics, configuration, readiness, provider/tool monitoring, and component tests

### Changed

- promoted package version from `0.5.0` to `0.6.0`
- composed console logging, framework metrics, and bounded operational observers without changing tool execution contracts
- extended application lifespan to validate startup, mark readiness, enter stopping state before closure, and report safe failure categories
- exposed Provider Router lifecycle/priority state and normalized generation usage through replaceable ports
- added pinned `streamlit==1.60.0`
- preserved existing `/health`, `/mcp/`, seven-tool discovery, and all Phase 1-5 behavior

### Security

- restricted dashboard API configuration to loopback origins without embedded credentials, query data, or fragments
- dashboard uses only a credential-free, redirect-disabled local `GET`
- operational output uses explicit safe models and excludes arguments, prompts, content, URLs, SQL, paths, secrets, provider bodies, and exception messages
- bounded recent logs retain only timestamp, level, source, event, component, status, latency, safe request identifier, and error category
- readiness and dashboard snapshots perform no external provider/tool health probes
- cost estimates use only normalized token counts and configured prices; missing streaming usage is never invented

### Testing

- expanded the offline suite from 98 to 112 tests
- added tests for dashboard composition/client behavior, readiness, operations API, tool/provider monitoring, bounded safe logs, token/cost metrics, and configuration validation
- verified 112 tests pass, compilation succeeds, and `pip check` reports no broken requirements
- retained one non-failing third-party `StarletteDeprecationWarning`

### Compatibility

- no MCP tool name, input schema, output schema, execution behavior, provider priority, or existing HTTP path was removed or changed incompatibly
- no live external request is required for startup or default tests
- no authentication, agent, CI/CD, deployment pipeline, or Phase 7 capability was implemented

## [0.5.0] - 2026-08-06

### Added

- `website_reader` with public-destination validation, bounded HTTPS streaming, HTML boilerplate removal, and structured clean text
- `sql_query` with a database-neutral port, SQLite read-only/query-only execution, named parameters, row bounds, and progress timeout
- `csv_analysis` with confined paths, delimiter and column detection, inferred types, statistics, missing-value analysis, and preview
- `currency_converter` with configurable Frankfurter integration, multi-target conversion, bounded retries, cache, and request coalescing
- `llm_analysis` with analyze/summarize operations and existing LLM Provider Router integration
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

- Website URLs require credential-free HTTPS; non-public destinations, redirects, unsupported content, and oversized responses are rejected. (Redirect handling changed in Unreleased: safe redirects are now followed with per-hop validation.)
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
