# Roadmap

This roadmap records delivered outcomes and separately approved post-v1 work.

## Release roadmap

| Phase | Outcome | Status |
| --- | --- | --- |
| 1. Foundation | Python 3.12, FastAPI/FastMCP baseline, configuration, Git | Complete |
| 2. MCP Core | Registry, discovery, strict validation, execution, errors, logging, tests | Complete |
| 3. Provider Router | Cerebras, NVIDIA, OpenRouter, retry/failover/health | Complete |
| 4. Tool Framework | Common lifecycle, metrics, Stock Price tool | Complete |
| 5. Core MCP Tools | Website, SQLite, CSV, currency, and LLM analysis | Complete |
| 6. Dashboard & Production Readiness | Read-only operations UI, health/readiness, metrics, lifecycle | Complete |
| 7. Deployment & v1.0.0 Release | Docker, Compose, CI validation, release docs, tagged version 1.0.0 | Complete and published to `origin/main` |
| Post-v1 Provider Plugin Platform | Unlimited self-registering adapters, model discovery/ranking, health, budgets, dashboard | Complete in v1.1.0 working tree; awaiting approval |

## v1.1.0 exit criteria

- provider adapters self-register and infrastructure discovers them without provider-name switches
- built-in adapters remain backward compatible and adding a provider does not change router/MCP/tool code
- every enabled provider is initialized, health-checked, and model-discovered at startup
- normalized capabilities cover chat, reasoning, streaming, embeddings, image/audio generation, tool/function use, vision, long context, JSON, web search, and code generation
- dynamic ranking considers capability, availability, health, latency, configured cost/free status, reasoning quality, and context; explicit priority remains optional
- daily, monthly, and per-request budgets provide soft deprioritization and hard failover
- dashboard exposes providers, models, capabilities, selection reason, health, availability, latency, request/error/success data, discovery/cache age, and budget/cost state
- MCP Core, all seven tool contracts, existing HTTP paths, and v1.0 deployment architecture remain compatible
- offline unit, integration, API/MCP, dashboard, and startup suites pass

## Future roadmap - not approved

- inbound authentication, authorization, tenant isolation, and public topology
- persistent/distributed health, metrics, budgets, audit, traces, probes, and alerts
- additional provider adapters (OpenAI, Anthropic, Gemini, Cohere, Groq, DeepSeek, Mistral, Hugging Face, Together, Perplexity, AWS Bedrock, Azure OpenAI, Ollama, LM Studio, and others)
- provider-native embeddings, image, audio, vision, search, and tool-call request/response contracts beyond routing metadata
- signed image publication, vulnerability/SBOM/provenance automation, promotion, and rollback orchestration
- PostgreSQL adapter, governed multi-tenant data access, and horizontal scaling

These are proposals, not commitments.
