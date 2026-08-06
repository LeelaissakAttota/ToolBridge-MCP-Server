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

## D-014 - Provider Router promoted to Phase 3

- **Date:** 2026-08-06
- **Status:** Accepted
- **Context:** The roadmap placed Core Tools in Phase 3 and Provider Routing in Phase 4, but the project owner explicitly approved Provider Router as Phase 3 and prohibited later-phase implementation.
- **Decision:** Swap the two outcomes: Provider Router is Phase 3 and Core Tools becomes Phase 4. Keep all Phase 4 tool work blocked pending separate approval.
- **Consequences:** Version `0.3.0` contains routing but no provider-backed MCP tool. Roadmap, status, tasks, architecture, and tests must use the revised phase order.

## D-015 - Project-owned provider port with HTTP adapters

- **Date:** 2026-08-06
- **Status:** Accepted
- **Context:** Cerebras, NVIDIA, and OpenRouter expose compatible chat-completion APIs, but vendor SDK types would couple application policy to external libraries.
- **Decision:** Define `BaseProvider` and normalized domain models under `toolbridge/providers`. Implement vendor adapters with the existing pinned `httpx` dependency and inject transports for offline tests.
- **Consequences:** Providers are independently replaceable and application code has no FastAPI, FastMCP, or vendor SDK dependency. Provider API differences remain isolated in adapters. Official API changes require adapter contract tests.

## D-016 - Retry, failover, and streaming boundary

- **Date:** 2026-08-06
- **Status:** Accepted
- **Context:** Provider failures require bounded recovery without duplicating requests that are invalid or streams that already emitted content.
- **Decision:** Retry timeout, rate-limit, and unavailable errors within the configured per-provider count using capped exponential backoff. Fail over for provider-local failures but never for invalid requests. Permit streaming retry or failover only before the first chunk.
- **Consequences:** Recovery behavior is deterministic and bounded. Mid-stream failure returns immediately to avoid duplicate partial output. On-demand health checks can restore the highest-priority healthy provider.

## D-017 - Provider secrets, logging, and lifecycle

- **Date:** 2026-08-06
- **Status:** Accepted
- **Context:** Provider integration introduces outbound credentials, sensitive prompts, external responses, and long-lived HTTP clients.
- **Decision:** Keep providers disabled by default; load keys through typed secret settings; require HTTPS; unwrap keys only during adapter construction; allowlist provider log fields; and initialize/close adapters through application lifespan.
- **Consequences:** Keys, prompts, responses, authorization headers, and vendor error bodies are absent from ToolBridge provider logs and normalized errors. Deployment still requires an approved secret manager, identity controls, budgets, and outbound network policy.

## D-018 - Managed tool lifecycle reuses the MCP Core

- **Date:** 2026-08-06
- **Status:** Accepted
- **Context:** Phase 4 requires every tool to share registration, validation, execution, response, logging, metrics, health, and lifecycle behavior without duplicating the Phase 2 pipeline.
- **Decision:** Define a transport-independent `BaseTool`, compose tools through `ToolManager`, register immutable definitions in the existing `ToolRegistry`, and observe the existing executor with structured logging followed by in-memory metrics.
- **Consequences:** Tools remain independently testable and FastMCP-independent. Registry, validation, error, timeout, and response behavior remains centralized. Metrics are process-local aggregates and reset on restart.

## D-019 - Stock data port with Yahoo primary and optional Alpha fallback

- **Date:** 2026-08-06
- **Status:** Accepted for local Phase 4
- **Context:** The approved first tool needs broad current quote metadata, credential-free local operation, and an optional configured alternative without coupling application logic to a stock SDK.
- **Decision:** Define a project-owned `StockQuoteProvider` port. Use an asynchronous Yahoo Finance chart adapter as the default primary and an optional Alpha Vantage `GLOBAL_QUOTE` adapter as fallback. Normalize missing provider metadata as null or `unknown`; never invent values.
- **Consequences:** Providers are replaceable and tests remain offline through injected HTTP transports. Yahoo's chart contract is undocumented and cannot be considered production-approved until legal, licensing, and supported-contract review is complete. Alpha Vantage freshness depends on entitlement and its quote response omits some metadata.

## D-020 - Bounded stock retries, cache, health, and safe observability

- **Date:** 2026-08-06
- **Status:** Accepted
- **Context:** External market data introduces latency, rate limits, malformed payloads, memory pressure, credentials, and sensitive request metadata.
- **Decision:** Configure provider priority, timeouts, retry count, capped exponential backoff, cache duration, cache size, endpoints, response size, and health symbol. Cache only successful normalized responses per symbol, coalesce concurrent misses, disable redirects, restrict origins and paths, and allowlist stock log fields. Retain only aggregate tool metrics.
- **Consequences:** Recovery and resource use are bounded. Invalid symbols are not retried, retryable failures fail over after exhaustion, and cancellation propagates. Cache and health remain process-local/on-demand; distributed cache, scheduled probes, readiness, and broader telemetry require later approval.


## D-021 - Phase 5 extends the existing managed-tool lifecycle

- **Date:** 2026-08-06
- **Status:** Accepted for Phase 5
- **Context:** The owner approved five remaining Core MCP Tools and prohibited changes to the Phase 4 framework unless necessary.
- **Decision:** Keep `BaseTool`, `ToolManager`, `ToolRegistry`, `ToolExecutor`, validators, logs, metrics, and health contracts unchanged. Add each tool as a definition-backed application service behind project-owned ports and compose them in a Phase 5 infrastructure factory.
- **Consequences:** Phase 1-4 behavior remains centralized and compatible. The Provider Router is now built before managed tools so it can be injected into LLM Analysis without giving the tool router-lifecycle ownership.

## D-022 - Website Reader uses bounded HTTP and public-destination validation

- **Date:** 2026-08-06
- **Status:** Accepted for local Phase 5
- **Context:** Reading arbitrary web pages introduces SSRF, redirects, oversized content, unsafe HTML, privacy, and licensing risks.
- **Decision:** Require credential-free HTTPS on port 443, optional exact-host allowlisting, public-address resolution, disabled redirects, text-only content, bounded streaming, and dependency-free boilerplate removal. Return normalized text and never log URLs or content.
- **Consequences:** Local/private destinations and common abuse paths are rejected. DNS validation remains separate from connection, so production requires an outbound firewall and explicit allowlist to mitigate rebinding and destination-policy gaps.

## D-023 - SQL and CSV use configured local resources behind replaceable ports

- **Date:** 2026-08-06
- **Status:** Accepted for local Phase 5
- **Context:** Database and file tools can expose arbitrary local data or perform mutations if paths, queries, time, or output are not controlled.
- **Decision:** Define database-neutral and CSV data-source ports. Implement only SQLite and confined local CSV adapters. Accept a single conservative read-only SQL statement with named parameters, SQLite read-only/query-only enforcement and progress timeout. Accept only relative CSV paths beneath one root and bound file, row, column, field, and preview sizes.
- **Consequences:** A PostgreSQL adapter can be added later without changing the tool contract, but is not implemented. Conservative SQL validation may reject harmless text. Production requires identity, per-resource authorization, tenant separation, least privilege, and data governance.

## D-024 - Currency conversion uses normalized base-unit rates with bounded cache

- **Date:** 2026-08-06
- **Status:** Accepted for local Phase 5
- **Context:** Exchange-rate APIs introduce network failures, freshness concerns, provider terms, request duplication, and malformed financial values.
- **Decision:** Define an exchange-rate provider port and implement a configured Frankfurter-compatible HTTPS adapter. Fetch base-unit rates, validate the requested base and targets, retry only normalized transient failures, coalesce cache misses, and cache only successful bounded rate sets.
- **Consequences:** Multi-currency conversion is provider-neutral and offline-testable. One provider means no failover. Provider terms, currency coverage, attribution, freshness, and production suitability remain open decisions.

## D-025 - HCL Curie / LLM Analysis delegates only to Provider Router

- **Date:** 2026-08-06
- **Status:** Accepted for Phase 5
- **Context:** Text analysis is required without duplicating vendor routing, credentials, retries, failover, or logging, and without introducing agent autonomy.
- **Decision:** Build one non-streaming analyze/summarize tool that constructs a provider-neutral request, wraps source text as untrusted document data, and calls the existing Provider Router. Return structured provider-neutral content and token usage. Do not add tool calling, chaining, memory, or agents.
- **Consequences:** Provider-specific behavior and secrets remain hidden. The tool is discoverable but unavailable when no LLM provider is enabled. Model output remains untrusted and production use requires data-processing, retention, model, cost, and review policies.
## Open decisions

The following require proposals before implementation:

- Supported and licensed production stock-data contract
- Exact Phase 6 scope and acceptance criteria
- Authentication and authorization approach
- Broader metrics, tracing, and telemetry stack
- Packaging and hosting platform
- Persistence and cache requirements
- License and distribution terms
- Production website outbound policy, privacy, and content licensing
- Database and CSV identity, tenancy, authorization, and data governance
- PostgreSQL adapter and connection policy
- Exchange-rate provider terms, coverage, attribution, freshness, and fallback
- LLM model, data-processing, residency, retention, and cost policy
- CI/CD automation
