# Installation

ToolBridge v1.0.0 supports Python 3.12 and Docker. Use a local Python environment for development or Docker Compose for an isolated release runtime.

## Prerequisites

- Git
- Python 3.12 for local installation
- Docker Engine with Docker Compose for container installation

## Local development installation

From the repository root on Windows PowerShell:

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
python -m pip install --requirement requirements-dev.txt
python -m pip check
Copy-Item .env.example .env
```

On Linux or macOS, activate with `source .venv/bin/activate` and copy the environment file with `cp .env.example .env`.

The example configuration contains no secrets and keeps providers disabled. Add credentials only to the ignored `.env` file or a deployment secret store. Enabling an LLM provider also requires its default model.

## Start locally

Start the API and MCP server:

```powershell
python -m uvicorn toolbridge.main:app --host 127.0.0.1 --port 8000
```

In a second terminal, start the read-only dashboard:

```powershell
python -m streamlit run toolbridge/dashboard/app.py --server.address 127.0.0.1 --server.port 8501
```

Open `http://127.0.0.1:8501`. API documentation is at `http://127.0.0.1:8000/docs`.

## Install with Docker Compose

Optionally copy `.env.example` to `.env`, edit only required values, then run:

```powershell
docker compose up --build --detach
python scripts/verify_release.py
```

Both published ports remain bound to host loopback. The API is at port 8000 and the dashboard at port 8501. Stop the stack with `docker compose down`; omit `--volumes` to preserve the named data volume.

## Verify the installation

```powershell
python -m pip check
python -m ruff format --check toolbridge tests scripts
python -m ruff check toolbridge tests scripts
python -m pytest tests
```

See [TROUBLESHOOTING.md](TROUBLESHOOTING.md) if startup or validation fails.
