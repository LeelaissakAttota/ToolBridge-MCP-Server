# Project Status

> Text dashboard for the current repository. Update whenever version, phase, tests, branch, milestone, issues, or synchronization changes.

| Field | Current status |
| --- | --- |
| **Current Version** | `0.5.0` |
| **Current Phase** | Phase 5 - Remaining Core MCP Tools complete; awaiting project-owner acceptance |
| **Completion Percentage** | **63% overall** - 5 of 8 roadmap phases implemented; Phases 1 through 5 are 100% implemented |
| **Tests Passed** | **98 of 98** automated tests passing as of 2026-08-06 |
| **Current Branch** | `main` |
| **Repository** | Initialized Git repository with GitHub remote `origin` configured |
| **Synchronization** | Committed Phase 4 `main` matches `origin/main`; Phase 5 changes are intentionally uncommitted and unpushed |
| **Next Milestone** | Project-owner review and acceptance of Phase 5; no Phase 6 work without explicit approval |
| **Last Updated** | 2026-08-06 (Asia/Calcutta) |

## Known Issues

1. The service has no inbound authentication, authorization, tenant controls, rate limiting, or production hardening and must remain local-development only.
2. Website destination checks have a residual DNS-rebinding time-of-check/time-of-use risk. Production requires an explicit allowlist and outbound firewall enforcement.
3. The SQL tool has a PostgreSQL-ready port but only a SQLite runtime adapter. Conservative validation may reject harmless SQL containing forbidden words in string literals.
4. SQL and CSV tools operate on operator-configured local data without a tenant authorization or data-governance layer.
5. Frankfurter currency coverage, availability, freshness, and terms are external dependencies; no secondary exchange-rate provider exists.
6. LLM output remains untrusted, can be incomplete or incorrect, and provider use may incur cost. No agent or autonomous tool chaining is implemented.
7. Yahoo Finance remains undocumented and requires supported-contract and licensing review before production stock use.
8. Tool caches and metrics are process-local; health checks are on demand and no readiness endpoint or circuit breaker exists.
9. The suite emits one third-party `StarletteDeprecationWarning` from FastAPI/Starlette `TestClient`.
10. Strict FastMCP validation still uses one isolated MCP SDK internal due version `1.29.0` limitations.
11. Live external provider contract tests require separately approved network access, credentials, terms, and cost and are excluded from the offline suite.

## Completed in Phase 5

- Website Reader, SQL Query, CSV Analysis, Currency Converter, and HCL Curie / LLM Analysis tools
- Automatic registry integration through the unchanged Phase 4 framework
- Existing validation, timeout, response, error, structured logging, metrics, health, and lifecycle behavior reused
- Typed Phase 5 settings and safe environment examples
- Clean Architecture ports for websites, databases, CSV sources, exchange rates, and existing Provider Router integration
- SSRF controls, read-only SQL controls, path confinement, bounded files/responses, safe retries/caching, and untrusted-LLM-output handling
- Offline tests for registration, discovery, success, invalid input, error handling, timeouts, caching, response validation, configuration, and protocol compatibility
- Required README, architecture, roadmap, changelog, status, tasks, decisions, testing, and security updates

## Status basis

- Version: `toolbridge/__init__.py`
- Phase and milestone: `ROADMAP.md` and `TASKS.md`
- Tests: `python -m pytest -q -p no:cacheprovider`
- Dependencies: `python -m pip check`
- Branch and synchronization: Git status and tracking state
- Architecture and constraints: `ARCHITECTURE.md`, `DECISIONS.md`, and `SECURITY_GUIDELINES.md`
