# Security Guidelines

## Current security posture

Version `0.5.0` remains a local-development service. It exposes seven read-only MCP tools but has no inbound authentication, authorization, tenant separation, rate limiting, persistent audit trail, deployment hardening, or approved production data contracts. Do not expose it to untrusted networks.

Phase 2 validation/cancellation controls, Phase 3 LLM secret/routing controls, and Phase 4 stock controls remain in force.

## Phase 5 controls

- strict extra-forbidden input and output schemas with core request/response byte limits,
- common whole-tool timeouts, structured allowlisted execution logs, aggregate metrics, and normalized client errors,
- configuration-driven external origins, timeouts, retries, caches, file/database roots, rows, columns, fields, and response limits,
- no Phase 5 secret committed or logged; LLM credentials remain isolated in Provider Router adapters,
- offline tests without live credentials, production data, or provider traffic.

## Trust boundaries

Treat MCP arguments, URLs, DNS, website content, SQL, parameters, SQLite values, paths, CSV cells, exchange-rate payloads, provider/model output, environment settings, and external errors as untrusted. Validate every crossing into a more privileged component.

## Website Reader threat review

- Require credential-free HTTPS on standard port 443.
- Optionally enforce an exact hostname allowlist; production must configure one.
- Reject localhost, `.local`, and any resolved non-global address.
- Refuse redirects, unsupported content types, status errors, and oversized streamed responses.
- Remove scripts and common navigation/layout boilerplate; still treat returned text as untrusted.
- Never log URLs, query strings, content, or exception messages.
- Residual risk: DNS may change between validation and connection. Production requires outbound firewall/DNS policy and re-evaluation before public exposure.
- Review robots, copyright, site terms, privacy, personal data, and retention before use.

## SQL Query threat review

- Accept only one conservatively validated `SELECT` or `WITH` statement.
- Reject separators, comments, transaction commands, pragmas, attachment, schema changes, and data mutation keywords.
- Pass named parameters separately; never interpolate values.
- Open configured SQLite files in URI read-only mode and enable SQLite query-only mode.
- Enforce row caps, JSON-safe scalars, duplicate-column rejection, progress-handler timeout, and outer tool timeout.
- Keep database paths in configuration beneath a root; never accept paths or connection strings from MCP input.
- Production still requires authenticated per-tool authorization, least-privileged database roles/files, tenant isolation, query governance, and audit.
- A future PostgreSQL adapter must use a read-only transaction, statement timeout, parameter binding, and a least-privileged account.

## CSV Analysis threat review

- Accept only relative `.csv` paths and verify the resolved file remains beneath the configured root.
- Bound file bytes, rows, columns, field characters, preview rows, and total execution time.
- Parse outside the event loop; normalize filesystem and parse errors without returning paths.
- Do not log filenames, cells, statistics, or previews.
- Treat formula-like cells and all returned values as untrusted if exported to spreadsheet or HTML destinations.
- Production requires tenant authorization, file permissions, malware/content handling policy, retention, and personal-data governance.

## Currency Converter threat review

- Validate finite positive bounded amounts and distinct uppercase ISO currency codes.
- Require a safe HTTPS provider origin and path; disable redirects.
- Stream and bound provider responses, validate requested base/targets, reject non-finite or extreme rates, and normalize errors.
- Retry only timeout, network, rate-limit, and unavailable categories with capped backoff.
- Cache only successful normalized rate sets with TTL and entry bounds; no customer account or payment data is used.
- Returned rates are informational, not financial advice or a settlement guarantee.
- Production requires provider terms, attribution, freshness, currency coverage, outage, and fallback decisions.

## HCL Curie / LLM Analysis threat review

- Bound source text, optional instructions, provider request bytes, output tokens, temperature, execution time, and response bytes.
- Use the existing Provider Router for secrets, HTTPS, retry, failover, safe errors, and allowlisted logs.
- Place supplied text inside an explicitly untrusted document wrapper with a fixed system instruction.
- Never log source text, prompts, instructions, responses, keys, authorization headers, or vendor bodies.
- Treat output as untrusted and potentially inaccurate. Do not execute it, grant it authority, or chain tools automatically.
- Production requires approved provider/model, data-processing terms, residency, retention, sensitive-data policy, cost controls, and human review rules.

## Logging, metrics, and privacy

Core logs may contain only tool name, correlation identifier, duration, status, safe error code, and approved exception type. Provider logs retain only provider, latency, status, request identifier, and safe error category. Metrics use bounded tool-name aggregates. Never log arguments, URLs, SQL, parameters, paths, filenames, cells, prompts, content, results, credentials, or provider bodies.

## Authentication and authorization

Before non-local exposure, authenticate every MCP request; authorize by client, tenant, tool, operation, database/file resource, and outbound destination; deny by default; separate operator and client privileges; and add inbound request, connection, rate, concurrency, size, and cost controls.

## Dependencies and supply chain

No dependency was added in Phase 5. Standard-library HTML, SQLite, CSV, DNS, and statistics capabilities plus the existing pinned `httpx` client are used. Continue pinning direct dependencies; add approved secret, dependency, license, and vulnerability scanning before production.

## Incident and change checklist

Review sources, destinations, permissions, side effects, tenants, limits, cancellation, audit, abuse, privacy, licensing, and cost for every change. Client errors must never reveal stack traces, queries, paths, environment values, provider bodies, credentials, or topology. Before production, define credential revocation, data containment/deletion, evidence handling, provider escalation, notifications, recovery, and post-incident review.
