# Deployment Plan

## Current deployment status

ToolBridge is not production-deployed and has no Dockerfile, container configuration, reverse proxy, CI/CD workflow, cloud manifest, database, or secret manager integration. The only verified deployment mode is local Uvicorn on Python 3.12.

```powershell
.\.venv\Scripts\Activate.ps1
python -m uvicorn toolbridge.main:app --host 127.0.0.1 --port 8000
```

This binds to loopback only and is appropriate for local development. Do not expose the current service publicly: authentication, authorization, rate limiting, transport policy, and production monitoring are not implemented.

## Deployment principles

- Build one immutable, reproducible artifact per release.
- Promote the same artifact through environments.
- Inject configuration and secrets at runtime.
- Run as a non-administrative identity with minimum permissions.
- Require health verification and a documented rollback.
- Keep the MCP endpoint behind an approved trust boundary until security controls exist.

## Proposed environments

| Environment | Purpose | Data and access |
| --- | --- | --- |
| Local | Development and unit/integration testing | Fake or developer-owned data; loopback only |
| Test | Automated integration and security checks | Synthetic data; no production credentials |
| Staging | Deployment rehearsal and acceptance | Production-like configuration with isolated secrets |
| Production | Approved client traffic | Managed secrets, audited access, monitoring, backups as required |

The hosting platform and regional requirements are undecided.

## Packaging decision still required

A later phase should evaluate an OCI container versus a managed Python service. Containerization is suggested by the original architecture concept but has not been approved or implemented. The selected option must support:

- Python 3.12 and pinned dependency installation
- Non-root execution
- Read-only application filesystem where practical
- Runtime secret injection
- Health/readiness probes
- Graceful termination of the FastAPI lifespan and MCP session manager
- Centralized logs and telemetry
- Resource limits and horizontal scaling tests

## Configuration

Current settings are prefixed with `TOOLBRIDGE_`. Deployment must provide environment-specific values without baking them into artifacts. `TOOLBRIDGE_HOST`, `TOOLBRIDGE_PORT`, and `TOOLBRIDGE_LOG_LEVEL` are modeled but the current command must pass corresponding Uvicorn options explicitly.

Before production, classify settings as:

- safe defaults,
- required non-secret configuration,
- secrets managed by a secret store,
- deployment-platform values.

Fail startup clearly when required production configuration is missing.

## Health and readiness

- Keep `GET /health` as a cheap process-liveness signal.
- Add a separate readiness endpoint before external dependencies participate in request handling.
- Readiness should report only safe aggregate state, not credentials or internal topology.
- Provider degradation should not necessarily restart a healthy process.

## Proposed delivery pipeline

1. Validate metadata and dependency lock/pins.
2. Install into a clean Python 3.12 environment.
3. Run offline tests and `python -m pip check`.
4. Run linting, type checks, and security scans once those tools are approved.
5. Build and identify the immutable artifact.
6. Generate dependency and provenance metadata where supported.
7. Deploy to test, then staging.
8. Run API, MCP, security, lifecycle, and rollback smoke tests.
9. Require explicit production approval.
10. Deploy gradually and monitor defined service-level indicators.

No CI/CD provider has been selected.

## Release verification

At minimum, verify:

- Process starts and reaches ready state.
- `/health` returns the expected environment.
- MCP initialize, list-tools, and a safe diagnostic call succeed.
- Unauthorized access is rejected once authentication exists.
- Logs contain correlation context and no secrets.
- Shutdown completes without abandoned sessions.
- Previous release can be restored.

## Rollback

Retain the previously verified artifact and its compatible configuration. Roll back when health, error rate, latency, security, or data-integrity thresholds are breached. Database changes, once introduced, must be backward-compatible or have a separately tested recovery procedure.

## Operations still required before public release

- Hosting and network architecture decision
- TLS termination and trusted proxy configuration
- Authentication and authorization
- Rate and resource limits
- Central logs, metrics, traces, alerting, and retention policy
- Secret management and rotation
- Backup/recovery plan for any persisted state
- Vulnerability and dependency scanning
- Incident response contacts and runbooks
- Capacity, load, and failure testing
- Data residency, privacy, and retention decisions
