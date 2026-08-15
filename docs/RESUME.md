# ToolBridge MCP Server Resume Material

Use this content as a truthful source for a resume, portfolio, or interview. Adjust tense and length to match the surrounding resume without adding unverified scale or production claims.

## Project Name

ToolBridge MCP Server

## One-Line Resume Description

Built a Python Model Context Protocol server with seven validated tools, plugin-based multi-provider LLM routing, secret-safe operations monitoring, and a hardened local Docker deployment.

## Recommended Resume Bullets

- Engineered a FastAPI/FastMCP Streamable HTTP server that exposes seven schema-validated MCP tools with bounded execution, Pydantic input/output contracts, timeouts, and normalized non-secret errors.
- Designed a Clean Architecture provider platform where Cerebras, NVIDIA, and OpenRouter adapters self-register as plugins and route through capability filtering, model ranking, health scoring, retries, failover, and configurable budget controls.
- Implemented read-only SQLite, CSV, website, market-data, currency, system-status, and LLM-analysis capabilities with conservative SQL validation, filesystem confinement, SSRF-aware URL checks, and bounded external responses.
- Built a read-only Streamlit operations dashboard backed by FastAPI health, readiness, and allowlisted snapshot endpoints for tool/provider status, metrics, estimated cost, and bounded safe logs.
- Packaged the service with a multi-stage non-root Docker image, loopback-only Docker Compose topology, GitHub Actions startup/container checks, Ruff gates, and 123 passing automated tests.

## Tech Stack

- Python 3.12
- FastAPI and Uvicorn
- Model Context Protocol Python SDK and FastMCP
- Pydantic and Pydantic Settings
- HTTPX
- Streamlit
- SQLite and Python CSV processing
- pytest and Ruff
- Docker and Docker Compose
- GitHub Actions

## Interview Talking Points

### What problem does this solve?

ToolBridge gives MCP-compatible AI clients one discoverable, typed interface to approved local and external capabilities. It prevents each client from directly coupling to vendor APIs, databases, files, validation rules, retries, and operational telemetry.

### Why did you use MCP?

MCP standardizes initialization, capability discovery, tool schemas, and tool execution. A compatible client can inspect `tools/list` and invoke validated tools without a bespoke integration for each function.

### Why Clean Architecture?

The domain and application layers own contracts and policy, while FastAPI, FastMCP, HTTPX, SQLite, files, Streamlit, and provider implementations stay in outer adapters. That makes routing, budgets, validation, and tool behavior testable without network services or frameworks.

### How does provider failover work?

Enabled plugins health-check and discover models at startup. A request applies hard capability, availability, and budget filters, then ranks eligible models using health, latency, configured cost/free status, context, and reasoning quality. Retryable provider failures receive bounded backoff, and failover-eligible failures advance to another candidate. No provider is enabled by default.

### How do you prevent unsafe SQL operations?

The input model accepts one conservative statement beginning with `SELECT` or `WITH`, rejects comments, separators, pragmas, transaction commands, and mutating keywords, and binds named parameters separately. The SQLite adapter applies query-only/read-only controls, row limits, progress limits, and an outer timeout.

### How are secrets protected?

Provider keys are typed secrets loaded from ignored environment configuration and unwrapped only when constructing outbound adapters. Operational models are allowlisted and exclude prompts, tool arguments/results, URLs, SQL, paths, headers, credentials, provider bodies, and raw exceptions. The Docker build excludes `.env`.

### What would you improve for public production deployment?

Add authenticated client identity, authorization by tenant/tool/resource, TLS termination, rate/concurrency limits, persistent audit and telemetry, a distributed budget ledger/cache, managed secrets, stronger outbound network policy, vulnerability/SBOM/provenance controls, and an orchestrated deployment design. The current release intentionally supports loopback/local use.

### What was technically challenging?

The hardest part was keeping protocol, tool, provider, and monitoring boundaries strict at the same time: discovery had to expose exact schemas, provider plugins had to remain vendor-neutral, routing had to combine hard filters with ranking and budgets, and the dashboard had to be useful without retaining sensitive payloads.

## 30-Second Explanation

ToolBridge is a local-first MCP server I built in Python. It exposes seven validated tools through FastMCP, while a Clean Architecture core handles timeouts, errors, lifecycle, and observability. LLM work routes through self-registering Cerebras, NVIDIA, and OpenRouter plugins with capability-aware ranking, health, failover, and budget controls. A read-only Streamlit dashboard shows safe operational state, and the release is packaged with Docker, CI, and 123 passing tests.

## 2-Minute Explanation

ToolBridge solves the integration problem between MCP-compatible AI clients and a mixed set of local data tools, public APIs, and LLM providers. Instead of giving a client direct access to each dependency, the server exposes one Streamable HTTP MCP endpoint. Clients initialize, discover seven authoritative schemas with `tools/list`, and call tools through a common validated executor.

Internally, I used Clean Architecture. Domain models define provider-neutral and tool-neutral contracts. Application services own validation, timeouts, tool lifecycle, model ranking, budgets, health, retries, failover, and operations aggregation. FastMCP, FastAPI, HTTPX, SQLite, CSV files, provider APIs, logging, and Streamlit are adapters or infrastructure. That separation lets the 123-test offline suite exercise behavior with temporary data and mock transports rather than live credentials.

The v1.1.0 provider platform discovers self-registering Cerebras, NVIDIA, and OpenRouter plugins. Enabled providers can health-check and discover model metadata, while routing filters by required capability and budget before scoring health, latency, configured cost, context, and quality. Providers are disabled by default, so startup is network-free.

For operations, FastAPI exposes cheap liveness, lifecycle readiness, and a strict read-only snapshot. Streamlit renders provider, model, tool, metric, estimated-cost, and safe-log views without receiving prompts, queries, paths, credentials, or raw external responses. The supported deployment is intentionally loopback-only because inbound authentication is not part of this release. Docker and GitHub Actions validate the same constrained single-host topology.

