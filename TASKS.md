# Tasks

## Phase 7 - Deployment & v1.0.0 Release

### Docker and Compose

- [x] Add multi-stage Python 3.12 Dockerfile.
- [x] Use a fixed non-root user and minimal runtime dependency set.
- [x] Add API healthcheck, environment defaults, and persistent `/app/data` volume.
- [x] Add hardened read-only Compose services for API and dashboard.
- [x] Bind both published ports to host loopback.
- [x] Add `.dockerignore` excluding secrets, Git, tests, caches, and artifacts.

### CI and release automation

- [x] Add GitHub Actions for every push and pull request.
- [x] Install pinned development dependencies and run `pip check`.
- [x] Enforce Ruff formatting and static checks.
- [x] Run the full automated test suite and upload JUnit results.
- [x] Verify local API/dashboard startup.
- [x] Build the production image and smoke-test the Compose stack.
- [x] Generate compressed image and SHA-256 artifacts for release tags.
- [x] Keep publishing/deployment owner-controlled.

### Production validation

- [x] Add bounded release verification for version, health, readiness, registrations, dashboard, and safe monitoring keys.
- [x] Verify provider slots initialize safely when disabled by default.
- [x] Verify all seven tools register without live external requests.
- [x] Run dependency, formatting, lint, unit, integration/API, dashboard, and startup checks.
- [ ] Owner reviews local Docker engine validation evidence and Phase 7 report.

### Documentation and release

- [x] Create all nine requested operator/release documents.
- [x] Update README, changelog, status, roadmap, architecture, decisions, testing, security, standards, rules, workflow, deployment plan, and task records.
- [x] Promote package version to `1.0.0`.
- [x] Prepare release summary, architecture summary, project statistics, final structure, technology stack, limitations, and future roadmap.
- [x] Prepare suggested commit message and `v1.0.0` tag without committing, pushing, or tagging.

## Approval gate

- [ ] Project owner approves Phase 7.
- [ ] After approval only: create reviewed commit and tag through the documented Git workflow.
- [ ] No post-v1 implementation without a new explicit scope.
