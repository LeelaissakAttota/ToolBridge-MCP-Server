# Roadmap

This roadmap records delivered outcomes. Any post-v1 work requires a new owner-approved scope; future ideas are not commitments.

## Release roadmap

| Phase | Outcome | Status |
| --- | --- | --- |
| 1. Foundation | Python 3.12, FastAPI/FastMCP baseline, configuration, Git | Complete |
| 2. MCP Core | Registry, discovery, strict validation, execution, errors, logging, tests | Complete |
| 3. Provider Router | Cerebras, NVIDIA, OpenRouter, retry/failover/health | Complete |
| 4. Tool Framework | Common lifecycle, metrics, Stock Price tool | Complete |
| 5. Core MCP Tools | Website, SQLite, CSV, currency, and LLM analysis | Complete |
| 6. Dashboard & Production Readiness | Read-only operations UI, health/readiness, metrics, lifecycle | Complete |
| 7. Deployment & v1.0.0 Release | Docker, Compose, CI validation, release docs, version 1.0.0 | Complete; awaiting owner approval |

## Phase 7 exit criteria

- multi-stage Python 3.12 image uses a non-root user, healthcheck, slim runtime, environment configuration, and persistent data volume
- Compose validates and keeps unauthenticated API/dashboard ports on host loopback
- CI runs `pip check`, Ruff format/lint, all tests, local startup, image build, Compose startup, API/readiness/tool/provider/dashboard smoke validation, and tagged artifacts
- runtime and development dependencies are pinned separately
- release verifier checks v1.0.0, health, readiness, all seven tools, all three provider slots, dashboard health, and forbidden monitoring keys
- installation, deployment, user, API, troubleshooting, contribution, production checklist, known limitations, and release notes exist
- package, dashboard status, changelog, architecture, decisions, testing, security, tasks, and roadmap are synchronized
- no new MCP tool, authentication system, business feature, automatic deployment, commit, push, or tag was created

## Future roadmap - not approved

Possible proposals after v1.0.0 include:

- inbound authentication, authorization, tenant isolation, rate/concurrency/cost controls
- identity-aware proxy and supported public network topology
- persistent metrics, audit integration, tracing, scheduled probes, and alerts
- PostgreSQL adapter and governed multi-tenant data access
- hardened website egress proxy and DNS pinning strategy
- dependency migration including Starlette TestClient/httpx2 review
- signed image publication, vulnerability/SBOM/provenance automation, environment promotion, and rollback orchestration
- horizontal scaling and external cache/state backends

None of these items is authorized or implemented by Phase 7.
