# Security Guidelines

## Current security posture

Version `0.4.0` remains a local-development service. It now exposes the read-only `stock_price` MCP tool, but it still has no inbound authentication, authorization, rate limiting, persistent data, deployment hardening, or production market-data agreement. Do not expose it to untrusted networks.

Current Phase 4 controls:

- strict, extra-forbidden tool input and output schemas,
- bounded symbol syntax, request size, response size, timeout, retries, backoff, cache duration, and cache entries,
- safe HTTPS stock provider origins without credentials, query strings, fragments, or embedded paths,
- relative path validation against authority overrides and traversal,
- disabled HTTP redirects,
- normalized stock provider errors without response bodies or exception messages,
- successful normalized responses only in process-local cache,
- Alpha Vantage keys loaded as `SecretStr` and unwrapped only during adapter composition,
- allowlisted execution and provider logs without symbols, keys, URLs, payloads, or results,
- aggregate metrics without arguments, results, or correlation identifiers,
- credential-free and network-free default tests.

Phase 2 MCP validation and cancellation controls and Phase 3 LLM secret/routing controls remain in force.

## Trust boundaries

Treat all of the following as untrusted:

- MCP arguments and HTTP request data
- Stock symbols and external market-data payloads
- Website, file, document, database, and API content
- LLM provider and model output
- Environment configuration
- Agent-selected tools or parameters
- External error messages

Validate every crossing from a less-trusted component into a more-privileged one.

## Stock tool threat review

The Stock Price Tool is read-only but introduces outbound network access and market-data governance obligations.

- Data sources: configured Yahoo Finance and optional Alpha Vantage HTTPS origins
- Destination: one structured MCP response; successful values may enter a bounded in-memory cache
- Side effects: outbound GET requests, provider quota/cost usage, and memory use
- Input controls: one normalized ticker with length and character bounds
- Output controls: typed finite non-negative prices, bounded strings, timezone-aware timestamp, response-size limit
- Availability controls: explicit timeouts, retry cap, exponential-backoff cap, provider failover, cache bounds
- Privacy: no customer, portfolio, or account data is required or retained
- Logging: no symbol, query URL, API key, provider body, quote result, or exception message
- Licensing: Yahoo's undocumented chart feed is not production-approved; Alpha Vantage use must comply with the selected entitlement and terms
- Advice boundary: returned values are informational data, not financial or investment advice

## Secrets

- Never commit secrets or real credentials.
- Keep `.env` local and safe placeholders in `.env.example`.
- Use an approved secret manager in shared environments.
- Pass each secret only to its adapter.
- Never put secrets in logs, errors, metrics, MCP results, traces, or test fixtures.
- Alpha Vantage requires a query parameter key under its documented protocol; never emit the resulting URL.
- Support rotation without code changes and revoke suspected exposures.

## Authentication and authorization

Before non-local exposure:

- authenticate every MCP and administrative request,
- authorize by client, tool, operation, and resource,
- deny by default,
- separate operator and client capabilities,
- validate token issuer, audience, signature, expiry, and claims,
- add inbound rate and concurrency limits.

The identity system remains undecided and requires an architectural decision.

## Input and output safety

- Enforce typed schemas, bounds, allowed formats, and payload limits.
- Reject unknown or dangerous parameters.
- Normalize paths and prevent traversal.
- Restrict outbound destinations and prevent SSRF.
- Parameterize future database access and use least-privileged roles.
- Treat provider and model content as data, not instructions.
- Escape output for its destination and never return raw exceptions.
- Reject non-finite financial values and naive timestamps.

## Tool and provider safety

Every new tool requires a review of sources, destinations, permissions, side effects, tenants, limits, timeout, cancellation, audit, abuse, privacy, licensing, and cost.

- Prefer read-only deterministic tools.
- Use replaceable project-owned ports.
- Retry only failures classified as safe.
- Bound requests, responses, time, retries, backoff, concurrency, memory, and spend.
- Fail over invalid symbols only to check provider coverage; never repeatedly retry them.
- Treat output as untrusted before later tool or agent use.
- Require confirmation and stronger authorization for future side-effecting tools.

## Network security

- Use TLS for non-local traffic.
- Bind only to required interfaces.
- Restrict outbound network access to approved provider origins.
- Do not follow provider redirects unless separately threat-reviewed.
- Configure trusted proxies explicitly.
- Keep management endpoints private.
- Add rate, connection, timeout, and body controls before exposure.

## Logging, metrics, and privacy

- Use structured allowlists.
- Log tool/provider, outcome, latency, safe error category, and correlation/operation identifier only where approved.
- Do not log symbols, arguments, prompts, files, SQL results, stock quotes, URLs, tokens, or authorization headers.
- Do not use high-cardinality or sensitive metric labels.
- Define retention, access, deletion, and residency before collecting user data.
- Separate security audit events from debugging logs.

## Dependencies and supply chain

- Pin direct dependencies and review upgrades.
- Prefer trusted indexes and maintained packages.
- Add vulnerability and secret scanning before production.
- Generate an SBOM for releases.
- Remove unused packages and review licenses.

No dependency was added for Phase 4; the existing pinned `httpx` client is reused.

## Error and incident handling

Client errors must be stable and minimal. Do not reveal stack traces, filesystem paths, environment values, provider bodies, credentials, or internal topology.

Before production, define incident contacts, credential revocation, evidence preservation, recovery, notifications, market-data-provider escalation, and post-incident review.

## Change checklist

- What trust boundary, privilege, provider, quota, or cost is introduced?
- Can input trigger network, filesystem, database, financial, or external effects?
- Are identity and tenant boundaries sufficient?
- Are destinations, redirects, sizes, time, retries, concurrency, and memory bounded?
- Could logs, metrics, cache, or results leak sensitive data?
- Are failure, retry, failover, and cancellation safe?
- Are licensing, entitlement, freshness, and advice boundaries documented?
- Are abuse and denial tests present?
- Does deployment require a new secret or permission?
