# Tasks

## v1.1.0 - Provider Plugin Platform

- [x] Replace centralized provider construction with self-registering adapter plugins and automatic discovery.
- [x] Preserve built-in Cerebras, NVIDIA, and OpenRouter compatibility.
- [x] Add generic typed provider configuration and optional dynamic priority.
- [x] Add normalized capability and rich model-discovery metadata.
- [x] Add capability/task filtering and health/latency/cost/quality/context ranking.
- [x] Add daily, monthly, and per-request budgets with soft/hard behavior.
- [x] Add health scoring, retries/errors/success/latency telemetry, and recovery.
- [x] Extend the read-only operations snapshot and Streamlit provider/model dashboard.
- [x] Add nine focused plugin-platform tests.
- [x] Preserve MCP Core, all seven tool contracts, HTTP paths, and deployment architecture.
- [x] Synchronize project documentation.
- [x] Complete dependency, Ruff, then-current 123-test release baseline, startup, API/readiness, Docker, and dashboard validation.
- [x] Owner review and approval.
- [x] Commit and push the approved v1.1.0 changes; preserve the annotated release tag at `4d8d73bb3ffa63102c7059429f14b459eb668546`.

## Post-release compatibility and portfolio validation

- [x] Preserve all seven MCP tools and synchronize strict MCP enum validation with published JSON contracts.
- [x] Update the Frankfurter endpoint compatibility configuration.
- [x] Verify the current automated baseline: 133 tests passed with one non-failing Starlette/httpx deprecation warning; Ruff lint and format checks passed.
- [x] Capture MCP initialization and discovery of all seven tools.
- [x] Retain point-in-time NVIDIA, Yahoo Finance AAPL, and Frankfurter validation evidence without claiming permanent availability or deployment.
- [x] Capture rejection of a destructive SQL `DELETE` request.

## v1.0.0 release status

- [x] Owner approved Phase 7.
- [x] Commit `86cc575` created on `main`.
- [x] Annotated tag `v1.0.0` created and pushed with `main` to `origin`.

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
- [x] Owner reviewed and approved Phase 7; release commit/tag were pushed.

### Documentation and release

- [x] Create all nine requested operator/release documents.
- [x] Update README, changelog, status, roadmap, architecture, decisions, testing, security, standards, rules, workflow, deployment plan, and task records.
- [x] Promote package version to `1.0.0`.
- [x] Prepare release summary, architecture summary, project statistics, final structure, technology stack, limitations, and future roadmap.
- [x] Prepare suggested commit message and `v1.0.0` tag without committing, pushing, or tagging.

## Approval gate

- [x] Project owner approved Phase 7.
- [x] Reviewed Phase 7 commit and tag were created and pushed.
- [x] Provider Plugin Platform was separately authorized as an explicit post-v1 scope.
