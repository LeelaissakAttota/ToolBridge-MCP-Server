# Deployment Plan
> Phase 7 superseding status: the v1.0.0 single-host Compose deployment is implemented. This document retains earlier planning context; `DEPLOYMENT.md` is the operator runbook.

## Implemented v1.0.0 plan

| Concern | Implemented control |
| --- | --- |
| Artifact | multi-stage `toolbridge-mcp:1.0.0` Python 3.12 slim image |
| Identity | fixed non-root UID/GID 10001 |
| Configuration | typed `TOOLBRIDGE_` environment variables; host `.env` excluded from image/Git |
| Persistence | named `toolbridge-data` volume mounted at `/app/data` |
| Network | API and dashboard published only on host loopback |
| Health | image/API and dashboard healthchecks plus `/ready` |
| Hardening | read-only root, bounded tmpfs, dropped capabilities, no-new-privileges |
| Automation | push/PR quality/tests/startup/build/smoke; tag artifacts only |
| Validation | `scripts/verify_release.py` checks version, endpoints, registrations, dashboard, safe keys |
| Rollback | restore prior approved immutable image/config; preserve data volume |

## Promotion sequence

1. Obtain owner approval of this uncommitted Phase 7 worktree.
2. Run all quality, test, startup, Compose, image, security, and release checks.
3. Create the reviewed release commit.
4. Create annotated tag `v1.0.0` only after the commit is accepted.
5. Let CI reproduce gates and create the tagged image artifact/SHA-256.
6. Review the artifact, vulnerability/license/SBOM evidence, configuration, backups, and checklist.
7. Deploy manually to the approved loopback/trusted single-host environment.
8. Run release verification and record evidence without secrets.

Automatic publishing, environment deployment, public ingress, credentials, and platform-specific rollout remain intentionally outside v1.0.0.

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
