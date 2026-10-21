# Security Guidelines

## Current security posture

Version `1.1.0` builds on the packaged v1.0.0 deployment and is for a hardened loopback-only single-host deployment. It exposes seven read-only MCP tools plus a read-only monitoring dashboard, but it has no per-client inbound authentication (only an optional shared MCP bearer token), authorization, tenant separation, application rate limiting, persistent audit trail, or approved production data contracts. Keep API and dashboard publication on loopback; do not expose either directly to an untrusted network.

All Phase 2-5 validation, timeout, cancellation, secret, provider, tool, SSRF, SQL, filesystem, and logging controls remain in force.

## Phase 6 controls

- dashboard configuration accepts only a loopback API origin with no credentials, query, or fragment
- dashboard performs only `GET /operations/snapshot` and exposes no mutations
- `/ready` evaluates local cached/lifecycle state and performs no external probe
- operational snapshots use strict immutable models and bounded containers
- lifecycle/startup failures are reduced to safe categories; exception messages are not retained
- tool/provider observers receive allowlisted metadata, not arguments or results
- recent logs are bounded and process-local, preventing unbounded memory retention
- provider token cost is computed only from normalized counts and configured rates
- disabled providers remain visible without requiring or exposing credentials
- all Phase 6 tests run offline without credentials or live provider traffic

## Operational data allowlist

The operations endpoint and dashboard may display only:

- version, environment, phase, uptime, lifecycle, and readiness decisions
- tool/provider stable names, registration/configuration status, health state, priority, active/failover state
- counts, durations, safe timestamps, normalized error categories, and safe request/correlation identifiers
- normalized token totals and configured cost estimates
- safe event name, source, component, status, level, and latency

Never store, log, return, or display:

- API keys, passwords, access tokens, authorization headers, cookies, connection strings, or secrets
- prompts, tool arguments, instructions, source text, outputs, responses, provider bodies, or exception messages
- URLs, query strings, SQL, parameters, database paths, filenames, CSV cells/statistics/previews, or website content
- environment dumps, network topology, stack traces, or customer/tenant identifiers

Request IDs are operational correlators only. Do not embed user content or secrets in identifiers.

## Trust boundaries

Treat MCP arguments, URLs, DNS, website content, SQL, parameters, SQLite values, paths, CSV cells, exchange-rate payloads, provider/model output, dashboard JSON, environment settings, and external errors as untrusted. Validate every crossing into a more privileged component.

## Dashboard threat review

- Keep Streamlit on `127.0.0.1`; no authentication was authorized in Phase 6.
- Use only the typed local API URL. The dashboard client refuses redirects and sends no credentials.
- Treat operational JSON as untrusted and validate it with strict models before rendering.
- Keep the UI read-only; refresh is the only interactive server-related control and only reruns the page.
- Do not add raw log-file access, environment display, arbitrary URLs, query tools, shell commands, or configuration mutation.
- Do not present cost estimates as authoritative billing data.
- Before public or shared access, add approved authentication, authorization, CSRF/session controls where applicable, TLS termination, headers, rate limits, and an operator permission model.

## Readiness and monitoring threat review

- `/health` proves process liveness only; it must remain cheap and independent of optional systems.
- `/ready` reveals only stable local check names and states. It must not expose paths, provider endpoints, credentials, or exception text.
- optional provider/tool readiness gates are explicit configuration decisions.
- monitoring reads must not generate stock/provider traffic or create billing/cost side effects.
- bounded in-memory logs are diagnostic, not tamper-evident audit evidence.
- multi-worker/process deployments would fragment metrics and must not sum them without a designed backend.

## Provider plugin, discovery, and budget controls

- Treat provider adapter modules as trusted executable dependencies; review provenance and source before installation.
- Plugin identifiers are bounded and validated. Router/factory code never interprets a provider name through a vendor switch.
- API keys remain `SecretStr`, are required only for enabled providers, and are unwrapped only at outbound adapter construction.
- Enabled-provider startup health/model requests use configured HTTPS origins, paths, timeouts, response bounds, and normalized errors.
- Model metadata and prices are untrusted provider/operator inputs and are validated before routing or display.
- Capability requirements are hard filters; unsupported tasks are not silently routed to an incompatible model.
- Budget values are estimates. Process-local hard limits reduce accidental spend but are not an authoritative distributed billing control.
- Logs/metrics may contain only provider ID, request ID, status, latency, and normalized error category; never prompts, outputs, model payloads, headers, endpoints, or credentials.
- Dashboard provider/model tables remain read-only and display only normalized allowlisted fields.
## Existing tool controls

### Website Reader

Require credential-free HTTPS, reject local/non-global destinations, follow at most `MAX_REDIRECTS` (default 5) redirects while re-validating scheme, port, credentials, allowlist, and resolved IP on every hop, refuse unsupported/oversized content, and use an explicit production allowlist plus outbound firewall. Each TCP connection is pinned to the IP address that passed validation (TLS SNI and the Host header still use the URL hostname), which closes the DNS-rebinding window.

### SQL Query

Accept one conservative `SELECT`/`WITH`, bind named parameters separately, use SQLite URI read-only and query-only modes, and enforce row/query/outer time limits. Production requires least-privileged identities, authorization, tenants, governance, and audit.

### CSV Analysis

Confine relative `.csv` paths beneath the configured root; bound bytes, rows, columns, fields, preview, and execution time. Never log filenames or cells. Treat formula-like values as untrusted on export.

### Currency Converter

Validate finite bounded amounts/codes, require configured HTTPS, disable redirects, validate/bound responses, retry only normalized transient failures, and cache only successful normalized rates.

### LLM Analysis

Bound source/instructions/tokens/time/bytes, use only Provider Router secret/failover controls, wrap source as untrusted document data, never log content, and treat output as untrusted. Human review and provider data-processing approval remain required.

## Authentication and authorization

Optional built-in controls (off by default, so the default behaviour is unchanged): set `TOOLBRIDGE_MCP_AUTH_TOKEN` to require `Authorization: Bearer <token>` on every `/mcp` request (constant-time comparison, `401` otherwise). Set `TOOLBRIDGE_MCP_ALLOWED_HOSTS` / `TOOLBRIDGE_MCP_ALLOWED_ORIGINS` (comma-separated) to accept a reverse-proxy hostname in addition to the loopback defaults. A shared token is not per-client identity or authorization; the guidance below still applies before any shared exposure.

Before any non-local exposure, authenticate every MCP and operations request; authorize by client, tenant, tool, resource, operation, and operator role; deny by default; separate dashboard/operator and MCP-client privileges; and add request, connection, rate, concurrency, size, and cost controls.

## Dependencies and supply chain

Phase 6 adds pinned `streamlit==1.60.0`. Continue pinning direct dependencies and verify with the full suite and `pip check`. Secret, dependency, license, provenance, and vulnerability scanning remain future approved workflow work. Streamlit and its transitive dependencies must be included in production supply-chain review.

## Incident and change checklist

Review sources, destinations, permissions, side effects, tenants, limits, cancellation, audit, abuse, privacy, licensing, retention, and cost for every change. Client/dashboard errors must never reveal stack traces, queries, paths, environment values, provider bodies, credentials, or topology. Before production, define credential revocation, containment/deletion, evidence handling, provider escalation, notification, recovery, and post-incident review.

## Phase gate

The v1.0.0 release is tagged and synchronized. The approved v1.1.0 provider plugin scope does not authorize public exposure, inbound identity, or other post-v1 security architecture.

## v1.0.0 deployment controls

- The image uses a fixed non-root identity and contains only runtime dependencies plus application source.
- Compose drops all Linux capabilities, enables `no-new-privileges`, uses read-only roots, and limits writable temporary space.
- Published API and dashboard ports are explicitly bound to host `127.0.0.1`; direct public exposure is unsupported.
- The dashboard shares the API network namespace so its configured API URL remains loopback and passes existing application validation.
- `.env`, Git metadata, tests, caches, local data, and generated artifacts are excluded from image context.
- Provider secrets remain `SecretStr` environment configuration and must be injected at runtime; no Compose or workflow secret values are defined.
- The release verifier recursively rejects monitoring keys that imply credentials, authorization, prompts, or tool payloads.
- Health and readiness checks use local non-sensitive endpoints and perform no paid provider probe.

## CI and supply-chain boundary

The workflow uses read-only repository contents permission, pinned direct Python dependencies, dependency integrity checks, formatting/lint/tests, image build, and runtime smoke validation. Release-tag artifacts include a SHA-256 file. The workflow does not publish, sign, deploy, or receive production credentials.

Before an operator accepts a deployment, separately perform current base-image/dependency vulnerability, license, SBOM, provenance, and platform-policy review. Major GitHub Actions are referenced by reviewed major tags; organizations needing immutable supply-chain pinning should replace them with approved commit SHAs.

## Residual risk

The application still lacks inbound identity, authorization, tenancy, and rate limiting. Host-loopback publication is a compensating boundary, not an authentication system. A public or multi-user topology requires an explicit identity-aware proxy/network design and application authorization review. Other authoritative residual risks are in `KNOWN_LIMITATIONS.md`.
