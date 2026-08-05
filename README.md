# ToolBridge MCP Server

ToolBridge is a Model Context Protocol (MCP) service that exposes typed, validated, observable capabilities through a single transport. Version `0.3.0` completes Phase 3: a provider-neutral LLM router now supports Cerebras, NVIDIA, and OpenRouter behind replaceable adapters.

Provider-backed MCP tools have not been added. Phase 4 remains blocked on project-owner approval of a specific production tool and its data, cost, and security boundaries.

## Current capabilities

- FastAPI control plane and stateless FastMCP Streamable HTTP transport
- Framework-independent MCP tool contracts, registry, validation, and execution
- Provider-neutral generation, streaming, model discovery, health, and lifecycle contracts
- Configured provider priority: Cerebras, NVIDIA, then OpenRouter
- Automatic retries and safe failover using normalized provider error categories
- Health snapshots with status, latency, last success, and last failure timestamps
- OpenAI-compatible HTTP adapters for all three providers
- Structured provider logging that excludes API keys, prompts, and responses
- Bounded provider timeouts, retries, prompt bytes, output tokens, and temperature
- One MCP diagnostic tool: `system_status`
- Offline automated tests using fakes and `httpx.MockTransport`

## Prerequisites

- Python 3.12
- Internet access for initial dependency installation
- A provider API key and approved model identifier only when enabling that provider

## Setup

```powershell
py -3.12 -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
Copy-Item .env.example .env
python -m pytest
```

The `.env` copy is optional. Every provider is disabled by default, so the service and default test suite run without credentials or network access. Local `.env` files are ignored by Git.

## Run locally

```powershell
.\.venv\Scripts\Activate.ps1
python -m uvicorn toolbridge.main:app --host 127.0.0.1 --port 8000
```

| Purpose | URL |
| --- | --- |
| Service metadata | <http://127.0.0.1:8000/> |
| Liveness check | <http://127.0.0.1:8000/health> |
| OpenAPI documentation | <http://127.0.0.1:8000/docs> |
| MCP Streamable HTTP | `http://127.0.0.1:8000/mcp/` |

The trailing slash on the MCP URL is intentional. `/health` remains a cheap process-liveness endpoint and does not call external providers.

## Provider routing

The application runtime constructs enabled providers from typed settings and owns their startup and shutdown. The router exposes:

- `initialize()` and `close()`
- `health_check()` and `provider_status()`
- `list_models()`
- `generate()`
- `stream_generate()`

A request begins with the active provider. Retryable failures use the configured retry policy. Authentication, timeout, rate-limit, unavailable, invalid-response, and internal provider failures may fail over when safe. Invalid requests are not retried or sent to another provider.

Streaming retries and failover are allowed only before the first chunk. Once content has been emitted, a later error is returned immediately to avoid duplicated or conflicting partial output.

## Provider configuration

Provider priority and retry timing are application settings:

| Variable | Default |
| --- | --- |
| `TOOLBRIDGE_PROVIDER_PRIORITY` | `cerebras,nvidia,openrouter` |
| `TOOLBRIDGE_PROVIDER_RETRY_BACKOFF_SECONDS` | `0.25` |
| `TOOLBRIDGE_PROVIDER_MAX_RETRY_BACKOFF_SECONDS` | `2` |
| `TOOLBRIDGE_PROVIDER_MAX_REQUEST_BYTES` | `262144` |

Each provider uses nested settings under `TOOLBRIDGE_CEREBRAS__`, `TOOLBRIDGE_NVIDIA__`, or `TOOLBRIDGE_OPENROUTER__`:

| Suffix | Purpose |
| --- | --- |
| `ENABLED` | Load the provider when `true` |
| `API_KEY` | Secret credential; required only when enabled |
| `BASE_URL` | HTTPS API base URL |
| `DEFAULT_MODEL` | Approved default model identifier; required when enabled |
| `TIMEOUT_SECONDS` | Per-request HTTP timeout |
| `RETRY_COUNT` | Additional attempts before failover |
| `MAX_TOKENS` | Default and maximum request token limit |
| `TEMPERATURE` | Default sampling temperature |
| `MAX_PROMPT_BYTES` | Maximum encoded message payload |
| `MODELS_PATH` | Model discovery path |
| `CHAT_COMPLETIONS_PATH` | Generation and streaming path |

OpenRouter additionally supports optional `HTTP_REFERER` and `APP_TITLE` attribution settings. See `.env.example` for the complete safe template. Never commit `.env` or real credentials.

## Architecture

```text
MCP / application caller
        |
        v
ProviderRouter (application)
        |
        +-- BaseProvider port
                |
                +-- CerebrasProvider
                +-- NvidiaProvider
                +-- OpenRouterProvider
                        |
                        v
                 configured HTTPS APIs
```

Provider-domain and application modules do not import FastAPI, FastMCP, or vendor SDKs. Provider-specific HTTP behavior is isolated in adapters, while configuration, logging, and composition remain infrastructure concerns.

## Project layout

```text
ToolBridge MCP Server/
├── toolbridge/
│   ├── core/                    MCP Core contracts and services
│   ├── adapters/                MCP and execution-logging adapters
│   ├── providers/
│   │   ├── domain/              Normalized requests, responses, health, errors
│   │   ├── application/         Base provider port and router policy
│   │   ├── adapters/            Cerebras, NVIDIA, OpenRouter HTTP adapters
│   │   └── infrastructure/      Provider factory and structured logging
│   ├── tools/                   Diagnostic MCP tool
│   ├── bootstrap.py             Runtime composition
│   ├── config.py                Typed service and provider settings
│   └── main.py                  FastAPI/FastMCP composition root
└── tests/
    ├── unit/providers/          Provider configuration, routing, adapter, log tests
    ├── unit/                    MCP Core unit tests
    └── test_api.py              HTTP and MCP protocol tests
```

## Tests

```powershell
python -m pytest -q -p no:cacheprovider
python -m pip check
```

The Phase 3 suite contains 56 offline tests. The suite emits one documented third-party `StarletteDeprecationWarning` from FastAPI/Starlette's test-client integration.

## Documentation

- [Project status dashboard](PROJECT_STATUS.md)
- [Project rules](PROJECT_RULES.md)
- [Roadmap](ROADMAP.md)
- [Architecture](ARCHITECTURE.md)
- [Task register](TASKS.md)
- [Changelog](CHANGELOG.md)
- [Coding standards](CODING_STANDARDS.md)
- [Testing strategy](TESTING_STRATEGY.md)
- [Git workflow](GIT_WORKFLOW.md)
- [Deployment plan](DEPLOYMENT_PLAN.md)
- [Security guidelines](SECURITY_GUIDELINES.md)
- [Decision log](DECISIONS.md)

## Current limitations

- No provider-backed capability is exposed as an MCP tool.
- Provider health checks are on demand; no background scheduler or readiness endpoint exists.
- No authentication, authorization, inbound rate limiting, persistence, agent orchestration, UI, deployment packaging, or CI/CD is implemented.
- External-provider contract tests with real credentials remain opt-in and are not part of the default suite.
- The service remains intended for local development and must not be exposed to untrusted networks.

## License

No license has been selected. Until one is added, no permission to copy, modify, or redistribute the project is granted by default.
