# Changelog

All notable changes to this project are recorded here. The format follows Keep a Changelog principles, and releases use semantic versioning.

## [Unreleased]

No unreleased changes.

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
