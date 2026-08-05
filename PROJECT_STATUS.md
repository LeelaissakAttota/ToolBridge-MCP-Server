# Project Status

> Text dashboard for the current repository state. Update this file whenever the version, phase, test result, branch, milestone, or known-issue list changes.

| Field | Current status |
| --- | --- |
| **Current Version** | `0.3.0` |
| **Current Phase** | Phase 3 - Provider Router complete; awaiting project-owner acceptance before Phase 4 |
| **Completion Percentage** | **43% overall** - 3 of 7 roadmap phases complete; Phases 1, 2, and 3 are 100% complete |
| **Tests Passed** | **56 of 56** automated tests passing as of 2026-08-06 |
| **Current Branch** | `main` |
| **Repository** | Initialized Git repository with GitHub remote `origin` configured |
| **Synchronization** | Committed `main` tracks `origin/main`; Phase 3 changes are intentionally uncommitted and unpushed |
| **Next Milestone** | Owner acceptance of Phase 3 and approval of one specific Phase 4 production tool, data/model source, security boundary, cost boundary, and acceptance criteria |
| **Last Updated** | 2026-08-06 (Asia/Calcutta) |

## Known Issues

1. The test suite emits one third-party `StarletteDeprecationWarning` from FastAPI/Starlette's `TestClient` integration.
2. Strict FastMCP argument validation uses one isolated SDK internal (`_tool_manager`) because version `1.29.0` has no public post-registration hook. MCP SDK upgrades require adapter and protocol regression tests.
3. A timeout stops waiting for a synchronous MCP tool handler but cannot forcibly terminate its worker thread.
4. `TOOLBRIDGE_HOST` and `TOOLBRIDGE_PORT` are modeled in settings but are not automatically applied by a project launcher.
5. Provider health checks are on demand; no background scheduler, readiness endpoint, or circuit-breaker cooldown exists.
6. Live provider contract tests require separately approved credentials and are not part of the default offline suite.
7. Authentication, authorization, inbound rate limiting, persistence, provider budgets, CI/CD, and production packaging are not implemented. The service remains suitable for local development only.

## Completed in Phase 3

- Provider-neutral generation, streaming, discovery, health, status, and error contracts
- Replaceable lifecycle interface for Cerebras, NVIDIA, and OpenRouter
- Configuration-driven active-provider selection and priority
- Bounded retries, capped backoff, and category-aware failover
- Normalized responses and safe streaming failover behavior
- Latency and last success/failure monitoring
- Secret-aware settings and HTTPS-only provider endpoints
- Allowlisted structured logging without keys, prompts, or response content
- Offline router, adapter, configuration, health, error, stream, and logging tests

## Status Basis

- Version: `toolbridge/__init__.py`
- Phase and milestones: `ROADMAP.md` and `TASKS.md`
- Test result: `python -m pytest -q -p no:cacheprovider`
- Branch: `git branch --show-current`
- Repository state: `git status --short --branch`
- Architecture and constraints: `ARCHITECTURE.md`, `DECISIONS.md`, and `SECURITY_GUIDELINES.md`

## Update Rules

- Keep this file factual and concise; planned capabilities must not be presented as implemented.
- Recalculate overall completion when a roadmap phase is accepted as complete or the roadmap changes.
- Record both the test count and date of the most recent successful run.
- Remove resolved issues and add newly discovered blockers or operational limitations.
- Update `CHANGELOG.md` when a status change corresponds to a project change.
