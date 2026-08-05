# Security Guidelines

## Current security posture

Version `0.2.0` remains a local-development service. It binds to `127.0.0.1` in documented commands and has no authentication, authorization, rate limiting, provider credentials, persistent data, or production tools. It must not be exposed to untrusted networks in its current form.

The MCP Core now implements these defense-in-depth controls:

- strict typed request and tool-input validation,
- unknown-field rejection with rejected values hidden from transport errors,
- encoded request and response size limits,
- strict declared output validation,
- per-tool timeouts and cancellation propagation,
- safe normalized errors with correlation identifiers,
- structured logging that excludes arguments, results, and exception messages,
- deterministic registry discovery and duplicate rejection.

These controls do not replace identity, authorization, network limits, or production hardening.

## Trust boundaries

Treat all of the following as untrusted:

- MCP tool arguments and HTTP request data
- Website, file, CSV, document, database, and API content
- Provider and model output
- Environment values supplied by deployment systems
- Agent-generated tool choices or parameters
- Error messages from external services

Validate data each time it crosses from a less-trusted component into a more-privileged one.

## Secrets

- Never commit secrets or real credentials.
- Keep `.env` local and use `.env.example` only for safe placeholders.
- Use an approved secret manager in shared environments.
- Pass secrets only to the adapter that needs them.
- Never include secrets in URLs, logs, traces, exception text, metrics labels, MCP results, or test fixtures.
- Support rotation without code changes and revoke credentials after suspected exposure.

## Authentication and authorization

Before non-local exposure:

- Authenticate every MCP and administrative request.
- Authorize by user/client, tool, operation, and resource where applicable.
- Deny by default.
- Separate operator capabilities from normal client capabilities.
- Validate token issuer, audience, signature, expiry, and relevant claims.
- Do not rely on dashboard visibility or network obscurity as authorization.

The specific identity system is undecided and requires an architectural decision.

## Input and output safety

- Enforce typed schemas, bounds, allowed formats, and maximum payload sizes.
- Reject unknown or dangerous parameters.
- Normalize paths and prevent traversal for future filesystem tools.
- Allowlist destinations and defend against SSRF for future web/API tools.
- Parameterize SQL and restrict database roles for future query tools.
- Treat document and website contents as data, not trusted instructions.
- Escape output for its destination and avoid returning raw internal exceptions.
- Apply output size limits and safe truncation.

## Tool safety

Every new tool requires a threat review covering:

- data sources and destinations,
- required permissions,
- destructive or irreversible effects,
- tenant and user isolation,
- input and output limits,
- timeout and cancellation,
- audit requirements,
- abuse cases and cost exposure.

Prefer read-only, deterministic tools first. Require explicit confirmation and stronger authorization for future write, financial, messaging, deletion, or external side-effect tools.

## Provider and agent safety

- Place provider SDKs behind least-privileged adapters.
- Set timeouts, concurrency limits, request-size limits, and spend limits.
- Fail over only for errors classified as safe to retry.
- Do not send sensitive data to a provider without an approved data-processing basis.
- Treat model output as untrusted and validate it before tool execution.
- Do not let prompts override system authorization or project policies.
- Keep agent memory scoped and apply explicit retention rules before persistence.

## Network security

- Use TLS for all non-local traffic.
- Bind only to required interfaces.
- Restrict outbound network access to approved destinations.
- Configure trusted proxies explicitly; do not trust forwarded headers from arbitrary clients.
- Apply rate limits, connection limits, timeouts, and request-body limits.
- Keep management endpoints private.

## Logging and privacy

- Log identity references, tool name, outcome, timing, and correlation identifier when approved.
- Do not log raw tokens, authorization headers, prompts, files, database results, or full tool arguments by default.
- Redact known secret patterns before emission.
- Define retention, access, deletion, and residency requirements before collecting user data.
- Separate security audit events from verbose debugging logs.

## Dependencies and supply chain

- Pin direct dependencies and review upgrades.
- Use trusted package indexes and verify artifact provenance where supported.
- Add automated vulnerability and secret scanning before production deployment.
- Generate a software bill of materials for releases when packaging is implemented.
- Remove unused packages and avoid unmaintained libraries.
- Review licenses before distribution.

## Error handling

Client errors should be stable and minimal. Internal logs may contain actionable technical context only after redaction. Do not reveal stack traces, filesystem paths, environment values, provider credentials, or internal topology to clients.

## Incident handling

Before production, define contacts and procedures for detection, containment, credential revocation, evidence preservation, recovery, user notification, and post-incident review. Security fixes require regression tests and changelog entries that do not expose exploitable detail prematurely.

## Security checklist for every change

- What new trust boundary or privilege is introduced?
- Can the input trigger network, filesystem, database, cost, or external side effects?
- Are authorization and tenant boundaries enforced?
- Are sizes, time, concurrency, and destinations bounded?
- Could logs or results leak sensitive data?
- Are failure and retry behavior safe?
- Are tests included for abuse and denial cases?
- Does the deployment need a new secret or permission?
