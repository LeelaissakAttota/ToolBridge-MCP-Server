# Known Limitations

ToolBridge v1.1.0 is production-ready for its documented local or trusted single-host deployment profile, subject to these limitations.

1. The API and dashboard have no per-client authentication, authorization, tenant isolation, or application rate limiting. `/mcp` supports only an optional single shared bearer token (`TOOLBRIDGE_MCP_AUTH_TOKEN`). Docker publishes both only to host loopback; direct public exposure is unsupported.
2. Operational metrics, recent safe logs, uptime, provider usage, and caches are process-local and reset on restart. They are not an audit ledger.
3. No external metrics backend, distributed tracing, alert delivery, or scheduled provider probing is included.
4. Provider cost is an estimate based on configured rates and returned token usage, not a billing authority. Streaming usage can remain zero when a provider omits it.
5. External stock, currency, website, and LLM behavior depends on third-party availability, terms, licensing, privacy, quota, cost, and response contracts.
6. Website connections are pinned to the validated public IP, and redirects are re-validated per hop. Behind a proxy or VPN that returns synthetic DNS answers (for example 198.18.0.0/15 "fake-IP" modes), every site is rejected as non-public. Use an explicit allowlist and outbound firewall for sensitive deployments.
7. SQL backends are SQLite (default) and PostgreSQL (`TOOLBRIDGE_PHASE5__SQL_QUERY__BACKEND=postgres`, asyncpg). PostgreSQL uses one configured database, a read-only transaction, `statement_timeout`, bound parameters, and a row cap. It does not add tenant isolation, a connection pool, or a hosted data platform. Each query opens and closes its own short connection. A least-privilege `SELECT`-only role is still required.
8. SQL and CSV access have no tenant or data-governance layer beyond configured path and read-only controls.
9. LLM and website output is untrusted. The release does not include autonomous agents, memory, or tool chaining.
10. FastMCP strict schema compatibility uses one isolated SDK internal pinned to MCP SDK `1.29.0`.
11. API tests use a small in-repo ASGI client (`tests/asgi_client.py`, built on `httpx.ASGITransport`) instead of Starlette's deprecated httpx-backed `TestClient`, so the suite runs without deprecation warnings.
12. Live provider contract tests are opt-in and require separately approved credentials, network access, terms, quota, and cost.
13. CI builds and smoke-tests the image but does not publish it or deploy to an environment. Release publishing and deployment remain owner-controlled.
14. The Compose release uses one host and a shared network namespace; horizontal scaling, orchestration, and zero-downtime rollout are not included.
15. Model catalogs are discovered at enabled-provider startup and have no background refresh scheduler; restart to force a refresh.
16. Daily/monthly/per-request budgets and health scores are process-local estimates. They reset on restart and do not coordinate multiple workers.
17. Capability metadata enables safe selection, but provider-native embedding, image, audio, vision, web-search, and tool-call payload APIs are not added to the text generation contract.

See `ROADMAP.md` for separately approved post-v1 possibilities.
