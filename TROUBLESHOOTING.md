# Troubleshooting

## API does not start

Run `python -m pip check`, confirm Python 3.12, and inspect the startup error. Configuration validation intentionally stops startup for invalid priority, retry, URL, secret, or enabled-provider/model combinations.

If port 8000 is occupied, stop the conflicting process or set `TOOLBRIDGE_API_PORT` for Docker. Local Python commands must also use the matching dashboard API URL.

## Readiness returns 503

Inspect the `checks` list returned by `/ready`. Common causes are an application still starting, an uninitialized tool manager, provider router initialization failure, or an intentionally strict readiness policy.

## Dashboard is unavailable

Confirm the API is ready, then check `http://127.0.0.1:8501/_stcore/health`. The dashboard API URL is restricted to loopback. In Compose, the dashboard shares the API network namespace by design.

## Docker command cannot reach the engine

Start Docker Desktop or the Docker daemon and verify the active context. `docker compose config --quiet` validates configuration without starting containers. Engine access is still required for build and runtime validation.

## Provider is disabled or unavailable

An enabled provider requires its API key and default model. Check provider priority, network policy, quota, service status, and configured base URL. Logs intentionally do not echo credentials or prompts.

## A local data tool rejects a path

SQL and CSV paths must resolve within their configured roots. In Docker, place approved files in the persistent `/app/data` volume. Path traversal and out-of-root access are rejected.

## Website Reader rejects a URL

The default policy accepts safe HTTPS origins and requires public IP resolution. Private, loopback, link-local, credential-bearing, and unsupported destinations are rejected. Configure an allowlist only after an outbound-access review.

## Tests fail creating temporary files on Windows

Run the repository-configured command `python -m pytest tests`. If the host temp directory is restricted, provide an existing writable directory with `--basetemp`. These are environment setup errors, not tool failures.

## StarletteDeprecationWarning appears

The pinned Starlette TestClient falls back to `httpx==0.28.1` because optional `httpx2` is absent. This is a dependency warning, not a functional failure. It is intentionally not suppressed or patched; review it with the next dependency upgrade.
