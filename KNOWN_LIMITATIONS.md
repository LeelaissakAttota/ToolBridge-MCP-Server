# Known Limitations

ToolBridge v1.0.0 is production-ready for its documented local or trusted single-host deployment profile, subject to these limitations.

1. The API and dashboard have no inbound authentication, authorization, tenant isolation, or application rate limiting. Docker publishes both only to host loopback; direct public exposure is unsupported.
2. Operational metrics, recent safe logs, uptime, provider usage, and caches are process-local and reset on restart. They are not an audit ledger.
3. No external metrics backend, distributed tracing, alert delivery, or scheduled provider probing is included.
4. Provider cost is an estimate based on configured rates and returned token usage, not a billing authority. Streaming usage can remain zero when a provider omits it.
5. External stock, currency, website, and LLM behavior depends on third-party availability, terms, licensing, privacy, quota, cost, and response contracts.
6. Website destination validation has a DNS-rebinding time-of-check/time-of-use risk. Use an explicit allowlist and outbound firewall for sensitive deployments.
7. SQL runtime support is SQLite-only. PostgreSQL has a replaceable port but no production adapter in v1.0.0.
8. SQL and CSV access have no tenant or data-governance layer beyond configured path and read-only controls.
9. LLM and website output is untrusted. The release does not include autonomous agents, memory, or tool chaining.
10. FastMCP strict schema compatibility uses one isolated SDK internal pinned to MCP SDK `1.29.0`.
11. Starlette `1.4.1` emits one `StarletteDeprecationWarning` in tests because its TestClient falls back to compatible `httpx==0.28.1` when optional `httpx2` is absent. It has no observed functional impact and is not suppressed.
12. Live provider contract tests are opt-in and require separately approved credentials, network access, terms, quota, and cost.
13. CI builds and smoke-tests the image but does not publish it or deploy to an environment. Release publishing and deployment remain owner-controlled.
14. The Compose release uses one host and a shared network namespace; horizontal scaling, orchestration, and zero-downtime rollout are not included.

See `ROADMAP.md` for separately approved post-v1 possibilities.
