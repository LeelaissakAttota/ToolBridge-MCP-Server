# Project Status

> Text dashboard for the current repository state. Update this file whenever the version, phase, test result, branch, milestone, or known-issue list changes.

| Field | Current status |
| --- | --- |
| **Current Version** | `0.4.0` |
| **Current Phase** | Phase 4 - Core Tool Framework and Stock Price Tool complete; awaiting project-owner acceptance |
| **Completion Percentage** | **57% overall** - 4 of 7 roadmap phases implemented; Phases 1 through 4 are 100% implemented |
| **Tests Passed** | **75 of 75** automated tests passing as of 2026-08-06 |
| **Current Branch** | `main` |
| **Repository** | Initialized Git repository with GitHub remote `origin` configured |
| **Synchronization** | Committed Phase 3 `main` matches `origin/main`; Phase 4 changes are intentionally uncommitted and unpushed |
| **Next Milestone** | Project-owner acceptance of Phase 4, resolution of the Yahoo production data-contract decision, and explicit approval of any Phase 5 scope |
| **Last Updated** | 2026-08-06 (Asia/Calcutta) |

## Known Issues

1. Yahoo Finance's chart endpoint is undocumented and may change; production or commercial use requires an approved supported contract and data-license review.
2. Alpha Vantage `GLOBAL_QUOTE` may be end-of-day without an applicable entitlement and does not supply company name, currency, exchange, or per-symbol market status.
3. Tool cache and metrics are in-process only, reset on restart, and are not shared across workers.
4. Stock and LLM provider health checks are on demand; no scheduler, readiness endpoint, or circuit-breaker cooldown exists.
5. The test suite emits one third-party `StarletteDeprecationWarning` from FastAPI/Starlette's `TestClient`.
6. Strict FastMCP validation uses one isolated SDK internal because version `1.29.0` has no public post-registration hook.
7. A timeout stops waiting for a synchronous MCP tool handler but cannot forcibly terminate its worker thread.
8. Live external provider contract tests require separately approved credentials or network access and are excluded from the offline suite.
9. Authentication, authorization, inbound rate limiting, persistence, budgets, dashboard, agents, CI/CD, and production packaging are not implemented. The service remains local-development only.

## Completed in Phase 4

- Common independently testable `BaseTool` lifecycle
- Automatic managed-tool registration with deterministic MCP discovery
- Existing MCP Core validation, execution, error, logging, and cancellation pipeline reused
- Typed health status and in-process outcome/duration metrics
- Stock symbol validation and normalized quote response
- Yahoo Finance primary and optional Alpha Vantage fallback adapters
- Configured timeouts, retries, cache, provider priority, endpoints, paths, and bounds
- Per-symbol request coalescing and successful-response caching
- Safe retries and failover with normalized upstream errors
- HTTPS origin, traversal, redirect, response-size, and secret controls
- Offline tests covering all Phase 4 acceptance paths
- Required architecture, roadmap, task, changelog, status, decision, testing, security, and README updates

## Status basis

- Version: `toolbridge/__init__.py`
- Phase and milestone: `ROADMAP.md` and `TASKS.md`
- Tests: `python -m pytest -q -p no:cacheprovider`
- Dependencies: `python -m pip check`
- Branch and synchronization: Git status and tracking state
- Architecture and constraints: `ARCHITECTURE.md`, `DECISIONS.md`, and `SECURITY_GUIDELINES.md`

## Update rules

- Keep planned capabilities separate from implemented behavior.
- Recalculate completion when a roadmap phase is accepted or reordered.
- Record test count and date from the most recent successful full run.
- Remove resolved issues and add newly discovered limitations.
- Update `CHANGELOG.md` when status corresponds to a project change.
