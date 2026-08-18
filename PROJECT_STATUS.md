# Project Status

> Text dashboard for the current repository. Update whenever version, phase, tests, branch, milestone, issues, or synchronization changes.

| Field | Current status |
| --- | --- |
| **Current Version** | `1.1.0`, released as Git tag `v1.1.0` |
| **Current Phase** | Approved roadmap and historical v1.1.0 release complete; subsequent compatibility, documentation, and portfolio validation recorded on `main` |
| **Completion Percentage** | **100% of the approved provider-platform scope implemented and validated** |
| **Tests Passed** | **133 of 133** automated tests passing; 0 failed |
| **Current Branch** | `main` |
| **Repository** | Initialized; GitHub `origin` configured at `git@github.com:LeelaissakAttota/ToolBridge-MCP-Server.git` |
| **Synchronization** | The historical `v1.1.0` release remains tagged at `4d8d73bb3ffa63102c7059429f14b459eb668546`; subsequent documentation, compatibility, and portfolio-validation updates exist on `main` |
| **Next Milestone** | No additional implementation milestone is approved; future work remains subject to owner approval |
| **Known Issues** | One dependency-owned `StarletteDeprecationWarning`; process-local budgets/metrics reset on restart; see `KNOWN_LIMITATIONS.md` |
| **Last Updated** | 2026-08-18 (Asia/Calcutta) |

## v1.1.0 provider platform

- Provider adapters self-register through `register_provider()` and are discovered from the adapter package; router/factory code contains no provider-name switch.
- Built-in Cerebras, NVIDIA, and OpenRouter adapters remain compatible, while a new provider requires only an adapter module, registration metadata, typed configuration, and its API key.
- Startup initializes, health-checks, and discovers models for each enabled provider. Disabled providers perform no network work.
- The runtime model catalog records provider, capabilities, cost, context window, availability, health, latency, reasoning quality, and discovery time.
- Requests may declare a task and required capabilities. Dynamic routing ranks eligible models by availability, health, latency, configured cost/free status, reasoning quality, and context; an optional explicit priority remains supported.
- Per-provider daily, monthly, and per-request limits support soft deprioritization and hard routing exclusion/failover.
- Health telemetry records success rate, average latency, errors, retries, availability, and last success/failure. Health checks permit automatic recovery.
- The read-only dashboard now exposes provider/model catalogs, capabilities, active selection and reason, health, latency, request/error/success data, discovery/cache age, and budget/cost state.

## Compatibility and security

- All seven MCP tools, MCP Core contracts, existing HTTP paths, and built-in provider imports remain compatible.
- MCP JSON string-enum values advertised by tool schemas are accepted and converted to typed domain enums; invalid values and unknown fields remain rejected.
- The router remains FastAPI-independent and adapters remain replaceable behind project-owned ports.
- API keys are unwrapped only at adapter construction. Prompts, generated content, secrets, and provider response bodies remain excluded from logs and monitoring.
- Provider settings and budget values are environment-driven; there are no hardcoded credentials or provider prices.

## Validation targets

- dependency integrity: `pip check`
- formatting and static checks: Ruff
- current audited automated suite: 133 passing unit, integration, API/MCP, dashboard, and startup tests
- local service: health, readiness, operations snapshot, and Streamlit dashboard
- known non-failing warning: dependency-owned Starlette TestClient/httpx migration warning
