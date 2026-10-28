# Testing Strategy

## Objectives

Testing proves that ToolBridge starts, preserves MCP/HTTP contracts, validates boundaries, bounds external work, protects sensitive data, routes providers predictably, registers all tools, reports health/readiness, renders safe monitoring, packages correctly, and remains deployable without live credentials.

## Test layers

| Layer | Evidence |
| --- | --- |
| Unit | domain rules, validation, registry, execution, errors, adapters, provider router, tool services, metrics, dashboard helpers, release scan |
| Integration | application composition, lifecycle, automatic tool registration, provider/tool monitoring, local CSV adapter, mocked PostgreSQL adapter, bundled demo-data checks |
| API/MCP | lifespan, identity, health, readiness, operations snapshot, initialize, discovery, execution |
| Dashboard | component rendering, safe client behavior, Streamlit process health |
| Startup/release | local Uvicorn/Streamlit smoke and `scripts/verify_release.py` |
| Container | Compose validation, image build, health checks, full stack smoke in CI/local Docker |

The default suite is deterministic and offline. It uses fakes, `httpx.MockTransport`, temporary CSV resources, and no live provider credentials or paid requests.

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

## Current result

- total: 240 automated test cases
- passed: 239
- skipped: 1 live PostgreSQL test unless `TOOLBRIDGE_TEST_POSTGRES_DSN` is set
- failed: 0
- warnings: none
- mypy: passed
- dependency integrity: passed
- Ruff formatting and lint: passed
- API and dashboard startup smoke: passed
- Compose configuration: passed
- Docker image and Compose stack: build/start/health/release smoke passed locally

The validated Linux/amd64 image is approximately 199.3 MB. GitHub Actions repeats the image build and stack smoke on every push.

The v1.1.0 provider-platform tests cover arbitrary plugin registration, package discovery, generic configuration, capability filtering, dynamic free/paid and health ranking, per-request/daily limits, smart routing, budget failover, and startup health/model discovery.

RW-002 regressions cover strict JSON-boundary conversion of advertised MCP string enums, invalid enum rejection, unknown-field rejection, unrelated strict-type rejection, and FastMCP adapter execution without live provider calls.

## Live contract tests

An opt-in live MCP smoke script, `tests/live/mcp_live_smoke.py`, is not collected by pytest. It targets `http://127.0.0.1:8000/mcp/` by default; override this with `--port`, `--host`, `--url`, or `TOOLBRIDGE_SMOKE_PORT`/`TOOLBRIDGE_SMOKE_URL`. It sends `TOOLBRIDGE_MCP_AUTH_TOKEN` as a bearer token when that is set, and `--analysis` adds the LLM tool call. Live stock, website, currency, or LLM provider tests are not part of default CI. They require explicit approval of network access, credentials, terms, privacy, quota, model, and cost. A live test failure must not be confused with an offline application regression.

## Regression policy

- Every fixed defect receives a focused test when practical.
- Interface changes cover success, invalid input, timeout/cancellation, dependency failure, and response validation.
- Security tests verify rejection and redaction without inserting real secrets.
- Test counts are based on pytest collection, including parametrized cases.
- Do not suppress dependency warnings merely to make output quiet; investigate and document ownership/action.

## Release acceptance

No release is ready with a failed dependency check, formatting/lint gate, automated test, health/readiness check, registration check, dashboard health check, Compose parse, or secret-safety check. Public exposure and live provider validation remain separate owner-controlled decisions.
