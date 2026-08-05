# Coding Standards

## Scope

These standards apply to Python application code, tests, configuration, scripts, and code examples in documentation.

## Python baseline

- Target Python 3.12.
- Use UTF-8 text files and four-space indentation.
- Follow PEP 8 naming and layout conventions.
- Use modern built-in generics such as `dict[str, str]`.
- Avoid compatibility code for unsupported Python versions.

No formatter or linter is currently installed. Until tooling is approved, contributors should keep code PEP 8-compliant manually. Adding Ruff, Black, mypy, or similar tooling is a separate dependency and workflow decision.

## Types and interfaces

- Type all public functions, methods, and return values.
- Prefer specific types over `Any`; use `Any` only at genuine untyped boundaries.
- Model structured external input and output explicitly.
- Keep MCP tool schemas stable and intentional.
- Treat environment variables, endpoint paths, tool names, and result shapes as public interfaces.
- Do not expose vendor SDK types outside provider adapters.

## Modules and naming

- Use lowercase `snake_case` module and function names.
- Use `PascalCase` for classes and typed models.
- Use `UPPER_SNAKE_CASE` only for constants.
- Give tools verb-oriented or outcome-oriented names that remain clear to MCP clients.
- Keep modules cohesive; split a module when it owns unrelated responsibilities.

## Functions and classes

- Keep functions small enough to describe with one clear responsibility.
- Prefer dependency injection over hidden globals for services that vary by environment.
- Avoid mutable global state.
- Keep transport handlers thin: validate, invoke a service, and translate the result.
- Do not embed business logic in FastAPI routes or FastMCP decorators.
- Use classes only when state, lifecycle, or polymorphism justifies them.

## Async behavior

- Use `async` for network, filesystem, database, and provider operations that have asynchronous APIs.
- Do not perform blocking I/O on the event loop.
- Propagate cancellation and apply explicit timeouts at external boundaries.
- Start and stop long-lived resources through application lifespan management.
- Respect the MCP session manager lifecycle; one manager instance is started once per process.

## Configuration

- Add settings to the typed `Settings` model.
- Prefix application environment variables with `TOOLBRIDGE_`.
- Provide safe, non-secret examples in `.env.example`.
- Never commit real credentials or production endpoints that contain secrets.
- Validate configuration at startup when a missing value would make the service unusable.

## Errors

- Raise or return domain-specific errors at internal boundaries.
- Translate errors to stable client-facing categories at the transport boundary.
- Preserve actionable context for logs without exposing secrets or sensitive inputs.
- Never use broad exception handling that silently discards a failure.
- Include retryability only when the system can determine it reliably.

## Logging

- Prefer structured fields over string interpolation once structured logging is introduced.
- Include a correlation identifier for request and tool execution events.
- Log lifecycle and outcome, not full payloads.
- Never log API keys, authorization headers, passwords, tokens, connection strings, or unredacted sensitive data.

## Documentation

- Give each module a concise module docstring.
- Document public functions and non-obvious behavior.
- Explain why a constraint exists; avoid comments that merely repeat the code.
- Update architecture, configuration, testing, security, and changelog documents with relevant changes.

## Dependencies

- Import only packages declared in `requirements.txt` or the standard library.
- Keep imports grouped: standard library, third party, then project imports.
- Pin direct dependencies and verify upgrades with the full test suite and `python -m pip check`.
- Do not add a dependency for a small function that is clear to implement and maintain locally.

## Review checklist

- Is the behavior within approved scope?
- Are interfaces typed and validated?
- Are timeouts, cancellation, and failure paths handled?
- Are secrets and sensitive data protected?
- Are tests proportional to risk?
- Are documentation and the changelog current?
