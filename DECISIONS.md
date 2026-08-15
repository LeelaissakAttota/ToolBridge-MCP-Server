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

## D-026 - Read-only operational snapshot separates monitoring from execution

- **Date:** 2026-08-06
- **Status:** Accepted for Phase 6
- **Context:** A separate Streamlit process needs system, provider, tool, metric, cost, and log data without importing the running server, sharing mutable globals, or gaining tool-execution authority.
- **Decision:** Expose one strict, bounded `OperationsSnapshot` through local `GET /operations/snapshot`. Aggregate it in an application service from registry, manager, router, and safe observer state. The dashboard validates this JSON and renders it without mutation controls.
- **Consequences:** UI and server lifecycles are independent; domain/application layers remain FastAPI/Streamlit-independent. The endpoint must remain local until identity and authorization are approved.

## D-027 - Readiness uses local lifecycle state and cached tool monitoring

- **Date:** 2026-08-06
- **Status:** Accepted for Phase 6
- **Context:** Dashboard polling and readiness checks must not create network traffic, provider cost, stock requests, or slow external dependencies.
- **Decision:** Keep `/health` as cheap liveness. Make `/ready` check lifecycle, registry composition, ToolManager initialization, and Provider Router initialization using local state. Cache tool lifecycle health for monitoring. Optional active-provider and all-tool-health gates are typed configuration.
- **Consequences:** Reads are deterministic, fast, and side-effect free. Provider/tool health is last-known or lifecycle state, not a scheduled live probe. A future scheduled probe system requires a separate decision.

## D-028 - Bounded safe operational metrics and recent logs

- **Date:** 2026-08-06
- **Status:** Accepted for Phase 6
- **Context:** The dashboard requires request outcomes, timings, error categories, provider/tool usage, and recent logs without retaining high-cardinality or sensitive payloads.
- **Decision:** Compose existing structured loggers with a thread-safe process-local observer. Retain fixed-label aggregates and a configured-capacity deque of allowlisted metadata only. Add tool last-completion timestamps and a provider usage observer that receives provider identity and normalized token counts.
- **Consequences:** Memory is bounded and prompts, arguments, results, URLs, SQL, paths, provider bodies, secrets, and exception text remain absent. Metrics reset on restart and are not persistent audit evidence or cross-worker telemetry.

## D-029 - Provider cost values are configuration-driven estimates

- **Date:** 2026-08-06
- **Status:** Accepted for Phase 6
- **Context:** Provider prices change and vary by model/contract; hardcoded prices would become inaccurate and could be mistaken for billing truth.
- **Decision:** Configure input/output USD-per-million-token rates per provider with zero defaults. Estimate from normalized token usage. Count streaming requests but keep token/cost increments at zero when the stream contract supplies no usage.
- **Consequences:** Operators control assumptions and the system never invents token counts or prices. Values are estimates only; production billing reconciliation and model-specific price catalogs remain open.

## D-030 - Streamlit is a pinned local read-only adapter

- **Date:** 2026-08-06
- **Status:** Accepted for Phase 6
- **Context:** Phase 6 explicitly requires a professional Streamlit dashboard while prohibiting authentication and deployment work.
- **Decision:** Pin `streamlit==1.60.0`, run it as a separate loopback-bound process, allow only manual refresh, and keep all UI operations read-only. Validate the configured API URL as loopback without credentials/query/fragment.
- **Consequences:** Dashboard implementation is replaceable and cannot mutate server state. Public/shared access is prohibited until authentication, authorization, TLS, and operator permissions are approved. The larger dependency tree requires supply-chain review before production.

## Open decisions

The following require proposals before implementation:

- Supported and licensed production stock-data contract
- Authentication and authorization approach
- Persistent metrics/audit backend, tracing, scheduled probes, retention, and alert delivery
- Persistence and cache requirements
- License and distribution terms
- Production website outbound policy, privacy, and content licensing
- Database and CSV identity, tenancy, authorization, and data governance
- PostgreSQL adapter and connection policy
- Exchange-rate provider terms, coverage, attribution, freshness, and fallback
- LLM model, data-processing, residency, retention, and cost policy

## D-031 - One multi-stage non-root image serves API or dashboard

- **Date:** 2026-08-06
- **Status:** Accepted for v1.0.0
- **Context:** Production packaging must use Python 3.12, minimize runtime contents, and support both delivery processes without duplicating dependency graphs.
- **Decision:** Build runtime dependencies in a Python 3.12 slim builder virtual environment and copy it with application source into one slim runtime image. Run with fixed non-root UID/GID 10001. Select API or dashboard through the container command.
- **Consequences:** One reviewed artifact covers both processes and excludes tests/dev tools. Streamlit remains a runtime dependency, so the API-only footprint is larger than a dedicated image; splitting images can be proposed after measuring operational benefit.

## D-032 - Compose preserves the loopback-only dashboard trust boundary

- **Date:** 2026-08-06
- **Status:** Accepted for v1.0.0
- **Context:** Separate containers normally communicate through service DNS, but application configuration intentionally rejects non-loopback dashboard API URLs because inbound identity is absent.
- **Decision:** Run dashboard with `network_mode: service:api`, call the API over shared loopback, bind both service listeners inside the container namespace, and publish both ports only on host `127.0.0.1`. Keep the dashboard API validator unchanged.
- **Consequences:** The existing security invariant remains true and no container DNS exception is introduced. The topology is single-host and couples network lifecycle; horizontal orchestration requires a future authenticated design.

## D-033 - Runtime and development dependencies are separated and pinned

- **Date:** 2026-08-06
- **Status:** Accepted for v1.0.0
- **Context:** pytest and formatting tools are unnecessary in the production image, while CI must reproduce exact quality tooling.
- **Decision:** Keep application packages in `requirements.txt`; make `requirements-dev.txt` include runtime requirements plus pinned pytest and Ruff. Configure Ruff and pytest in `pyproject.toml`.
- **Consequences:** Images are smaller and CI/local gates are reproducible. Both files require dependency maintenance and full upgrade review.

## D-034 - CI validates and packages but does not deploy

- **Date:** 2026-08-06
- **Status:** Accepted for v1.0.0
- **Context:** Phase 7 requires CI/CD automation but deployment credentials, target platform, promotion policy, signing, and rollback authority are not approved.
- **Decision:** On push/PR, run dependency, Ruff, tests, startup, image, Compose, and release smoke gates. On version tags, export an image tarball and SHA-256 artifact. Do not publish or deploy.
- **Consequences:** Every change receives production-shape validation and review artifacts without creating external release state. Registry publishing and environment deployment require separate decisions.

## D-035 - Release verification uses bounded standard-library probes

- **Date:** 2026-08-06
- **Status:** Accepted for v1.0.0
- **Context:** Local operators and CI need one portable check for version, liveness, readiness, registrations, dashboard health, and operational secret-safety.
- **Decision:** Add a bounded retrying script using `urllib`, strict expected tool/provider sets, and recursive forbidden monitoring-key checks. It performs only read requests.
- **Consequences:** The verifier runs without extra host dependencies and catches composition leaks. It verifies safe key names, not arbitrary secret values, and complements rather than replaces code review and secret scanning.

## D-036 - Provider adapters self-register into a discovered plugin catalog

- **Date:** 2026-08-06
- **Status:** Accepted for v1.1.0
- **Context:** The fixed provider enum and factory switch required central router/composition edits for every new vendor, conflicting with the approved unlimited-provider architecture.
- **Decision:** Each adapter module calls `register_provider()` with its identifier, construction factory, default capabilities, and optional legacy settings attribute. Infrastructure imports adapter-package modules through package discovery and builds enabled registrations from the catalog. Runtime identifiers are validated strings; `ProviderName` remains only a built-in compatibility convenience.
- **Consequences:** A provider can be added with one adapter module plus typed settings/API key and no router, MCP Core, tool, FastAPI, or dashboard edit. Adapter modules are trusted application code and are imported at startup; plugin installation therefore requires the same code-review and supply-chain controls as any dependency.

## D-037 - Model discovery and capability-aware ranking replace fixed-provider selection

- **Date:** 2026-08-06
- **Status:** Accepted for v1.1.0
- **Context:** Provider identity alone cannot select safely among chat, reasoning, streaming, embedding, multimodal, tool-use, long-context, search, or code models, and a fixed three-provider priority cannot adapt to availability, latency, price, or quality.
- **Decision:** Every provider exposes `discover_models()` through the base port. Cache normalized model metadata and filter by request task/required capabilities before deterministic scoring by provider health, latency, configured price/free status, reasoning quality, and context window. Empty priority enables dynamic ranking; configured priority adds a deterministic preference without adding provider-name branches.
- **Consequences:** Existing generation callers remain valid because new routing hints have defaults. Capability metadata describes routability; provider-native embeddings/image/audio/tool-call payload contracts are not invented by this change. Model catalogs are startup snapshots until the process is restarted or a future refresh scheduler is approved.

## D-038 - Provider budgets are process-local routing safety limits

- **Date:** 2026-08-06
- **Status:** Accepted for v1.1.0
- **Context:** Provider failover without budget controls can exceed operator limits, while provider prices and organizational policies vary and must not be hardcoded.
- **Decision:** Configure per-provider daily, monthly, and per-request USD limits plus a soft-limit ratio. Estimate a candidate request from discovered model prices and token bounds; deprioritize soft-limited providers, exclude hard-limited candidates, and fail over. Record normalized successful token cost into a thread-safe process-local ledger.
- **Consequences:** Zero/absent prices produce zero estimates and values remain estimates rather than billing truth. Limits reset on process restart and do not coordinate workers, so durable organization-wide enforcement requires a shared authoritative ledger before distributed production use.

## D-039 - Enabled providers validate health and models during startup

- **Date:** 2026-08-06
- **Status:** Accepted for v1.1.0
- **Context:** Routing should not select a provider whose key, endpoint, model catalog, or required capability is invalid, and the dashboard requires discovery time/cache age.
- **Decision:** For every enabled plugin, create the adapter, run its health check, fetch models/capabilities, normalize/cache metadata, and mark failures unavailable without exposing vendor details. Disabled providers remain network-free. Later health checks probe all enabled providers so recovered providers can return to ranking.
- **Consequences:** Enabling a provider makes startup dependent on a bounded provider request and may delay readiness by its configured timeout/retries. Default startup remains offline because all providers are disabled. Operators requiring an active provider may enable the existing readiness gate.

## D-040 - Provider/model observability remains a read-only safe projection

- **Date:** 2026-08-06
- **Status:** Accepted for v1.1.0
- **Context:** Operators need model, capability, selection, health, latency, budget, cost, error, and discovery data without making the dashboard an execution/configuration surface or leaking prompts/secrets.
- **Decision:** Extend strict operations models with allowlisted provider/model metadata and render them in the existing read-only Streamlit tab. Expose active provider/model, selection reason, availability, health score, requests/errors/retries/success rate, cost/budget state, and discovery/cache timing. Continue excluding payloads, content, endpoints, headers, and credentials.
- **Consequences:** Existing operations clients must tolerate the additive `models` field and additive provider fields. The dashboard performs no provider call and all operational state remains process-local and non-authoritative.
