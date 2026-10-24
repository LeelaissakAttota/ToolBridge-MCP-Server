# ToolBridge MCP Server — Recruiter Project Summary

## Problem

AI clients need controlled access to tools, local data, public APIs, and multiple LLM providers. Direct integrations duplicate protocol code, expose vendor-specific contracts, and make validation, failure handling, cost controls, and observability difficult to enforce consistently.

## Solution

ToolBridge is a local-first Model Context Protocol server. It gives compatible clients one Streamable HTTP endpoint for discovery and execution while enforcing strict typed contracts, bounded work, normalized errors, provider-neutral routing, and secret-safe operations monitoring.

## Architecture

The Python codebase follows Clean Architecture:

- **Domain:** strict tool, provider, error, and operations models
- **Application:** tool execution/lifecycle, provider routing/ranking/budgets, and operations aggregation
- **Adapters:** FastMCP, FastAPI, HTTP providers, SQLite, CSV, logging, and Streamlit
- **Infrastructure:** typed configuration and runtime composition

Detailed Mermaid diagrams are available in [ARCHITECTURE.md](../ARCHITECTURE.md).

## Key Features

- MCP initialization, `tools/list`, and schema-validated `tools/call`
- deterministic registry and reusable managed-tool lifecycle
- timeout, cancellation, request/response size, and normalized error controls
- self-registering LLM provider plugins
- capability-aware model discovery and ranking
- health scoring, bounded retries, failover, and configurable budgets
- FastAPI health, readiness, OpenAPI, and secret-free operations snapshot
- read-only Streamlit provider/tool/metric/cost/log dashboard

## Seven Tools

1. `system_status`
2. `stock_price`
3. `website_reader`
4. `sql_query`
5. `csv_analysis`
6. `currency_converter`
7. `llm_analysis`

Local SQL is restricted to conservative read-only statements. CSV access is confined to a configured root. Website requests validate public destinations and bound responses. External market, website, currency, and LLM behavior remains network/provider dependent.

## Provider Platform

Cerebras, NVIDIA, and OpenRouter are built-in self-registering plugins. Enabled plugins can authenticate, health-check, and discover model metadata during startup. The router filters by capability, availability, and hard budgets, then ranks eligible models using health, latency, configured cost/free status, context, and quality. Eligible transient failures can retry and fail over.

Providers are disabled by default. Live provider execution requires owner-supplied credentials, configuration, network access, quota, cost approval, and provider terms.

## Security

The supported topology is loopback/local. Inputs and external data are untrusted and strictly validated. Secrets come from ignored environment configuration; the monitoring model excludes credentials, prompts, tool payloads, URLs, SQL, paths, headers, and provider bodies. Containers use a non-root identity, read-only roots, dropped capabilities, bounded temporary storage, and loopback-only host publication.

The release does not include inbound authentication, authorization, tenants, application rate limits, or a persistent audit backend and must not be directly exposed to an untrusted network.

## Testing

- 228 deterministic automated tests passing with no warnings; Ruff and mypy clean
- unit, integration, API/MCP, provider, tool, dashboard, startup, and release-safety coverage
- temporary SQLite/CSV fixtures and mock HTTP transports; default suite requires no credentials or paid requests
- Ruff formatting and lint gates
- local service and Docker Compose smoke validation in GitHub Actions
- owner manual validation passed with network/configuration-dependent tests clearly separated

Retained point-in-time portfolio evidence includes MCP execution through NVIDIA using `meta/llama-3.1-8b-instruct`, AAPL data from Yahoo Finance, and USD-to-INR/EUR conversion through Frankfurter. These captures do not imply permanent provider availability, successful live execution of every provider, or a production SLA.

## Deployment

The release includes a multi-stage Python 3.12 Docker image and a two-service Docker Compose topology for the API and Streamlit dashboard. Host ports publish only on `127.0.0.1`. CI builds and smoke-tests the stack and creates tagged image artifacts, but does not publish or deploy them automatically.

## Current Release

- Version/tag: `v1.1.0`
- Release commit: `4d8d73bb3ffa63102c7059429f14b459eb668546`
- Approved product roadmap: complete
- All seven MCP contracts remain stable

The historical `v1.1.0` tag remains at the release commit above. Later compatibility, documentation, and portfolio-validation updates exist on `main` and do not redefine that historical release boundary.

## Known Limitations

- no inbound identity, authorization, tenancy, or public deployment profile
- process-local metrics, health, caches, logs, and budgets reset on restart
- no distributed state, shared budget ledger, external telemetry backend, or horizontal orchestration
- live external data and provider calls depend on network access and third-party services
- LLM calls require separately configured credentials and approved cost/data handling
- SQLite is the implemented SQL runtime; no production PostgreSQL adapter is included

## Future Integration Possibility

An external assistant or agent, including a future system such as JARVIS, could connect to ToolBridge as an MCP client. That possibility is outside the completed ToolBridge v1.1.0 scope and does not require changing the current server contracts.
