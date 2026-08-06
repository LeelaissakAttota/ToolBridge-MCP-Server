# Security Guidelines

## Current security posture

Version `0.6.0` remains a local-only service. It exposes seven read-only MCP tools plus a read-only monitoring dashboard, but it has no inbound authentication, authorization, tenant separation, rate limiting, persistent audit trail, deployment hardening, or approved production data contracts. Bind the API and dashboard to loopback; do not expose either to an untrusted network.

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

## Existing tool controls

### Website Reader

Require credential-free HTTPS, reject local/non-global destinations, refuse redirects and unsupported/oversized content, and use an explicit production allowlist plus outbound firewall. DNS rebinding remains a residual risk.

### SQL Query

Accept one conservative `SELECT`/`WITH`, bind named parameters separately, use SQLite URI read-only and query-only modes, and enforce row/query/outer time limits. Production requires least-privileged identities, authorization, tenants, governance, and audit.

### CSV Analysis

Confine relative `.csv` paths beneath the configured root; bound bytes, rows, columns, fields, preview, and execution time. Never log filenames or cells. Treat formula-like values as untrusted on export.

### Currency Converter

Validate finite bounded amounts/codes, require configured HTTPS, disable redirects, validate/bound responses, retry only normalized transient failures, and cache only successful normalized rates.

### HCL Curie / LLM Analysis

Bound source/instructions/tokens/time/bytes, use only Provider Router secret/failover controls, wrap source as untrusted document data, never log content, and treat output as untrusted. Human review and provider data-processing approval remain required.

## Authentication and authorization

Before any non-local exposure, authenticate every MCP and operations request; authorize by client, tenant, tool, resource, operation, and operator role; deny by default; separate dashboard/operator and MCP-client privileges; and add request, connection, rate, concurrency, size, and cost controls.

## Dependencies and supply chain

Phase 6 adds pinned `streamlit==1.60.0`. Continue pinning direct dependencies and verify with the full suite and `pip check`. Secret, dependency, license, provenance, and vulnerability scanning remain future approved workflow work. Streamlit and its transitive dependencies must be included in production supply-chain review.

## Incident and change checklist

Review sources, destinations, permissions, side effects, tenants, limits, cancellation, audit, abuse, privacy, licensing, retention, and cost for every change. Client/dashboard errors must never reveal stack traces, queries, paths, environment values, provider bodies, credentials, or topology. Before production, define credential revocation, containment/deletion, evidence handling, provider escalation, notification, recovery, and post-incident review.

## Phase gate

Phase 6 is complete and awaits owner acceptance. Do not implement authentication, deployment, CI/CD, or Phase 7 without separate approval.
