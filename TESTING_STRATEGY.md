# Testing Strategy

## Objectives

Testing proves that ToolBridge starts, preserves MCP/HTTP contracts, validates boundaries, bounds external work, protects sensitive data, routes providers predictably, registers all tools, reports health/readiness, renders safe monitoring, packages correctly, and remains deployable without live credentials.

## Test layers

| Layer | Evidence |
| --- | --- |
| Unit | domain rules, validation, registry, execution, errors, adapters, provider router, tool services, metrics, dashboard helpers, release scan |
| Integration | application composition, lifecycle, automatic tool registration, provider/tool monitoring, local SQLite/CSV adapters |
| API/MCP | lifespan, identity, health, readiness, operations snapshot, initialize, discovery, execution |
| Dashboard | component rendering, safe client behavior, Streamlit process health |
| Startup/release | local Uvicorn/Streamlit smoke and `scripts/verify_release.py` |
| Container | Compose validation, image build, health checks, full stack smoke in CI/local Docker |

The default suite is deterministic and offline. It uses fakes, `httpx.MockTransport`, temporary SQLite/CSV resources, and no live provider credentials or paid requests.

## Required local gates

```powershell
python -m pip check
python -m ruff format --check toolbridge tests scripts
python -m ruff check toolbridge tests scripts
python -m pytest tests
docker compose config --quiet
```

For release validation after starting the stack:

```powershell
python scripts/verify_release.py --timeout-seconds 90
```

## Current v1.0.0 result

- total: 114 automated test cases
- passed: 114
- failed: 0
- warnings: one non-failing dependency-owned `StarletteDeprecationWarning`
- dependency integrity: passed
- Ruff formatting and lint: passed
- API and dashboard startup smoke: passed
- Compose configuration: passed
- Docker image and Compose stack: build/start/health/release smoke passed locally

The validated Linux/amd64 image is approximately 199.3 MB. GitHub Actions repeats the image build and stack smoke on every push.

## Live contract tests

Live stock, website, currency, or LLM provider tests are not part of default CI. They require explicit approval of network access, credentials, terms, privacy, quota, model, and cost. A live test failure must not be confused with an offline application regression.

## Regression policy

- Every fixed defect receives a focused test when practical.
- Interface changes cover success, invalid input, timeout/cancellation, dependency failure, and response validation.
- Security tests verify rejection and redaction without inserting real secrets.
- Test counts are based on pytest collection, including parametrized cases.
- Do not suppress dependency warnings merely to make output quiet; investigate and document ownership/action.

## Release acceptance

No release is ready with a failed dependency check, formatting/lint gate, automated test, health/readiness check, registration check, dashboard health check, Compose parse, or secret-safety check. Public exposure and live provider validation remain separate owner-controlled decisions.
