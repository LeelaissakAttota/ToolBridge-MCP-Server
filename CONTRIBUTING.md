# Contributing

## Before changing code

Read `ARCHITECTURE.md` and `docs/TESTING_STRATEGY.md`. Open an issue to discuss larger changes before starting work.

## Development setup

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --requirement requirements-dev.txt
```

Create a focused branch from synchronized `main`. Use lowercase Conventional Commit messages and keep unrelated changes separate.

## Required quality gates

```powershell
python -m pip check
python -m ruff format --check toolbridge tests scripts
python -m ruff check toolbridge tests scripts
python -m pytest tests
docker compose config --quiet
docker build --tag toolbridge-mcp:local .
```

Tests must be deterministic and offline by default. Use fake ports or `httpx.MockTransport`; live provider tests require separate approval, credentials, network, terms, quota, and cost controls.

## Architecture and security

- Preserve Domain -> Application -> Adapters -> Infrastructure dependencies.
- Keep FastAPI, MCP, HTTP, SQLite, Streamlit, and provider SDK details out of domain code.
- Validate inputs and outputs at boundaries.
- Never log prompts, content, queries, paths, credentials, headers, or provider payloads.
- Never commit `.env`, API keys, generated databases, CSV data, caches, or test artifacts.
- Update decisions, tests, changelog, status, and relevant guides when behavior or operations change.

## Pull request content

Describe scope, architecture impact, tests, security impact, documentation, known limitations, and rollback. CI must pass before merge. Reviews should reject hidden business features, public exposure without identity controls, or unbounded external I/O.
