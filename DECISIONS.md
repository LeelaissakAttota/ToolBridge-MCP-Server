# Decision Log

This lightweight log records architectural decisions for the current foundation. New decisions should be appended; superseded entries remain for history.

## Decision template

- **Status:** Proposed, Accepted, Superseded, or Rejected
- **Context:** The problem and constraints
- **Decision:** The selected approach
- **Consequences:** Benefits, costs, and follow-up work

## D-001 — Python 3.12 baseline

- **Date:** 2026-08-05
- **Status:** Accepted
- **Context:** The project needed a consistent local runtime compatible with the selected libraries.
- **Decision:** Target Python 3.12 and record it in `.python-version`.
- **Consequences:** Code may use Python 3.12 syntax and typing. Supporting another version requires explicit testing and a revised decision.

## D-002 — FastAPI and FastMCP in one ASGI process

- **Date:** 2026-08-05
- **Status:** Accepted for the foundation
- **Context:** The service needs both operational HTTP endpoints and an MCP transport without early distributed-system complexity.
- **Decision:** Compose FastAPI and a mounted FastMCP application in one Uvicorn process.
- **Consequences:** Local operation is simple and one lifecycle manages both surfaces. Isolation or independent scaling may require reconsideration later.

## D-003 — Streamable HTTP with stateless JSON MCP responses

- **Date:** 2026-08-05
- **Status:** Accepted
- **Context:** The initial MCP endpoint needs a modern HTTP transport and should avoid server-side session persistence.
- **Decision:** Configure FastMCP with `stateless_http=True`, `json_response=True`, and mount it at `/mcp/`.
- **Consequences:** The service is easier to scale conceptually and no MCP session store is required. Clients must use the documented trailing-slash endpoint. Stateful features require a new decision.

## D-004 — MCP session manager follows application lifespan

- **Date:** 2026-08-05
- **Status:** Accepted
- **Context:** The SDK session manager requires explicit startup and can be started only once per instance.
- **Decision:** Start it in the FastAPI lifespan and keep one lifespan per running application process.
- **Consequences:** Tests share one `TestClient` lifecycle for the module. Future application factories must create fresh MCP manager instances.

## D-005 — Typed environment configuration

- **Date:** 2026-08-05
- **Status:** Accepted
- **Context:** Runtime values need safe defaults and future environment-specific overrides.
- **Decision:** Use `pydantic-settings`, an optional `.env`, and the `TOOLBRIDGE_` prefix. Cache settings once per process.
- **Consequences:** Configuration is typed and centralized. Startup-time cache behavior means tests that change environment values must clear the cache or construct settings directly.

## D-006 — Pin direct dependencies in requirements.txt

- **Date:** 2026-08-05
- **Status:** Accepted for the foundation
- **Context:** The initial environment needed repeatable direct dependency versions without introducing another packaging workflow.
- **Decision:** Use `requirements.txt` with exact versions for direct runtime and test dependencies.
- **Consequences:** Setup remains familiar. Transitive resolution may still change if packages do not constrain dependencies fully; a lockfile or hash-pinned artifact may be adopted for release builds later.

## D-007 — Begin with a diagnostic tool only

- **Date:** 2026-08-05
- **Status:** Accepted
- **Context:** Protocol and lifecycle behavior needed verification before adding privileged or external tools.
- **Decision:** Expose only `system_status` in Phase 1.
- **Consequences:** The MCP path is testable without credentials or external dependencies. Production tool selection is deferred to approved later phases.

## D-008 — Separate implemented and target architecture

- **Date:** 2026-08-05
- **Status:** Accepted
- **Context:** The original product concept includes providers, routing, agents, databases, observability, tools, UI, and deployment components that are not implemented.
- **Decision:** Documentation must label capabilities as current, proposed, or future.
- **Consequences:** Planning remains ambitious without misrepresenting project readiness. Phase 2 requires explicit owner approval.

## D-009 - Framework-independent MCP Core contracts

- **Date:** 2026-08-05
- **Status:** Accepted
- **Context:** Phase 2 requires stable tool discovery and execution behavior without coupling domain logic to FastMCP.
- **Decision:** Define project-owned Pydantic input/output models, immutable tool definitions, registry metadata, normalized execution responses, and stable error codes under `toolbridge/core`.
- **Consequences:** Tools and application services can be tested without an MCP transport. Every future tool must use the core definition interface and structured output model.

## D-010 - Registry is the tool source of truth

- **Date:** 2026-08-05
- **Status:** Accepted
- **Context:** Direct decorator registration would duplicate metadata and bypass project validation.
- **Decision:** Register immutable definitions in `ToolRegistry`, discover them deterministically, and project them into FastMCP through `MCPToolAdapter`.
- **Consequences:** Duplicate names fail at startup and discovery is stable. The adapter owns all SDK-specific behavior.

## D-011 - Strict FastMCP argument-model compatibility seam

- **Date:** 2026-08-05
- **Status:** Accepted with upgrade constraint
- **Context:** MCP SDK `1.29.0` creates permissive generated argument models and provides no public post-registration hook to enforce the core's strict, extra-forbidden policy.
- **Decision:** Isolate one access to FastMCP's internal tool manager in the MCP adapter. Update the generated model to `strict=True`, `extra="forbid"`, and `hide_input_in_errors=True`, rebuild it, and publish its resulting schema.
- **Consequences:** MCP discovery and runtime validation match the core contract and rejected values do not appear in errors. Every MCP SDK upgrade must run adapter and full protocol regression tests; replace this seam when a supported public hook becomes available.

## D-012 - Normalized execution outcomes and safe logging

- **Date:** 2026-08-05
- **Status:** Accepted
- **Context:** Tool failures need stable client behavior and useful operational context without leaking payloads or secrets.
- **Decision:** The executor returns typed success/failure responses with safe messages and generated correlation IDs. A logging port emits start, success, and failure events through a standard-library JSON adapter with an allowlist.
- **Consequences:** Arguments, results, and exception messages are absent from ToolBridge execution logs. Internal failures expose only a safe category to clients and an exception type to logs.

## D-013 - Timeout and cancellation policy

- **Date:** 2026-08-05
- **Status:** Accepted
- **Context:** Tool calls must be bounded without breaking cooperative cancellation.
- **Decision:** Apply an `asyncio.timeout` per tool. Propagate caller cancellation after logging it. Run synchronous handlers through `asyncio.to_thread` so they do not block the event loop.
- **Consequences:** Async handlers can stop cooperatively. A timed-out synchronous handler's worker thread cannot be forcibly terminated, so future blocking tools should use cancellable async APIs or process isolation when required.

## Open decisions

The following require proposals before implementation:

- Phase 3 first production tool and authoritative data source
- Authentication and authorization approach
- Provider interface and routing policy
- Broader metrics, tracing, and telemetry stack
- Packaging and hosting platform
- Persistence and cache requirements
- License and distribution terms
- CI/CD and repository hosting platform
