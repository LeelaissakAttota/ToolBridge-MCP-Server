# Changelog

All notable changes to this project are recorded here. The format follows Keep a Changelog principles, and releases use semantic versioning.

## [Unreleased]

No unreleased changes.

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
