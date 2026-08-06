# ToolBridge MCP Server v1.0.0 Release Notes

Release date: 2026-08-06

## Release summary

ToolBridge v1.0.0 delivers a validated MCP server, a replaceable multi-provider LLM router, seven production-oriented tools, a read-only operations dashboard, hardened container packaging, automated CI validation, and complete operator documentation.

## Architecture summary

The code follows Clean Architecture: domain models and rules are independent; application services coordinate ports; adapters implement provider, HTTP, file, SQLite, MCP, and logging boundaries; infrastructure composes runtime implementations. FastAPI and Streamlit are outer delivery mechanisms and do not define provider or tool business behavior.

## Highlights

- MCP Streamable HTTP discovery and execution with strict request/response schemas
- Cerebras primary, NVIDIA secondary, and OpenRouter fallback routing
- bounded retries, failover, normalized errors, health, latency, usage, and cost estimates
- Stock Price, Website Reader, SQL Query, CSV Analysis, Currency Converter, HCL Curie Analysis, and System Status tools
- liveness, readiness, graceful shutdown, startup validation, metrics, and safe operational logs
- read-only Streamlit dashboard for system, providers, tools, metrics, costs, and logs
- Python 3.12 multi-stage non-root image and loopback-only Compose deployment
- GitHub Actions quality, test, startup, image build, Compose smoke, and tagged image-artifact jobs
- release verification script that validates version, liveness, readiness, registrations, dashboard, and secret-free monitoring keys

## Technology stack

Python 3.12, FastAPI, MCP Python SDK/FastMCP, Pydantic Settings, HTTPX, Streamlit, Uvicorn, SQLite, pytest, Ruff, Docker, Docker Compose, and GitHub Actions.

## Project statistics

- Production Python files: 75 under `toolbridge/`
- Release validation Python files: 2 under `scripts/`
- Documentation files: 22 Markdown files after release preparation
- Automated tests: 114 expected test cases after Phase 7 additions
- Supported MCP tools: 7
- Supported LLM providers: 3

Final passing counts and validation evidence are recorded in `PROJECT_STATUS.md` after the release test run.

## Final folder structure

```text
.
|-- .github/workflows/ci.yml
|-- Dockerfile
|-- docker-compose.yml
|-- requirements.txt
|-- requirements-dev.txt
|-- pyproject.toml
|-- scripts/
|   `-- verify_release.py
|-- toolbridge/
|   |-- core/
|   |-- providers/{domain,application,adapters,infrastructure}/
|   |-- tools/{domain,application,adapters,infrastructure}/
|   |-- operations/{domain,application}/
|   |-- dashboard/
|   `-- main.py
|-- tests/
|   `-- unit/
`-- *.md
```

## Known limitations

Inbound identity controls, multi-tenancy, persistent telemetry, public deployment, PostgreSQL runtime support, external alerting, horizontal scaling, and automatic deployment are not included. One dependency-owned Starlette TestClient deprecation warning remains. See `KNOWN_LIMITATIONS.md` for the authoritative list.

## Future roadmap

Possible post-v1 work requires separate owner approval: authentication and authorization, tenant isolation, persistent metrics/tracing/audit integration, PostgreSQL adapter, hardened outbound gateway, dependency migrations, orchestration, and controlled image publication/deployment.

## Upgrade and rollback

This is the first stable release. Deploy from the immutable `v1.0.0` source tag and `toolbridge-mcp:1.0.0` image. Preserve configuration and data backups. Roll back by restoring the prior approved image/configuration pair without deleting persistent data.
