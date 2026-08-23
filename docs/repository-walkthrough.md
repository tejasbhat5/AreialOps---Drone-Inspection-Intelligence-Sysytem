# Repository Walkthrough

## Request path

```text
frontend/app → frontend/lib/api.ts → backend/app/api/routes
→ backend/app/services → backend/app/repositories → SQLAlchemy/PostgreSQL
```

## Frontend

`frontend/app/(workspace)` contains the meaningful product routes. Server pages fetch initial data; colocated client components own interaction. Inputs are route/search parameters or server-action form data; outputs are typed UI trees. Failures surface through API errors, form messages, and route states.

`frontend/lib/api.ts` is the REST boundary. It receives a path/options, applies the configured base URL and timeout, parses the standard error contract, and returns domain types. A broken backend becomes a safe `ApiError`, not an unhandled fetch detail.

`frontend/types/domain.ts` mirrors public API contracts. Its purpose is compile-time UI safety, not runtime validation. Backend Pydantic remains authoritative.

`frontend/components/maps/site-risk-map.tsx` converts site coordinates/risk into Leaflet markers and popups. It depends on browser DOM APIs, so it is loaded as a client-side map. Bad coordinates are rejected upstream; provider-tile failure should not destroy non-map workflows.

`frontend/app/(workspace)/assistant/assistant-workspace.tsx` manages conversation state, suggested operations, loading/errors, structured site/risk/report rendering, citations, and tool audit. It never renders hidden model reasoning.

## Backend foundation

`backend/app/main.py` composes middleware, error handlers, and routers. It contains no domain business logic. Request middleware assigns request IDs, measures duration, and emits structured completion logs.

`backend/app/core/config.py` validates environment configuration. Provider keys remain server-side; deterministic and disabled defaults let the product run without paid services.

`backend/app/db/session.py` owns engine/session factories and dependency lifecycle. Services receive a session; transactions are explicitly committed or rolled back.

`backend/app/models` defines relational state and constraints. `schemas` defines external contracts. Confusing the two would leak persistence details into API compatibility.

## Domain modules

`services/site_service.py`, `inspection_service.py`, and `anomaly_service.py` enforce existence checks, transitions, and transaction boundaries. Repositories compose selects/aggregates. Route handlers translate HTTP only.

`services/risk_service.py` receives a site, unresolved anomalies, and completed-inspection recency; it returns/stores a versioned score and factor snapshot. Failure rolls back the domain mutation that triggered recalculation.

`services/upload_service.py` validates filenames, signatures, declared content types, counts, and sizes; writes opaque storage keys; and creates source metadata plus a PENDING job. If a database write fails it removes newly stored files.

`jobs/runner.py` claims one job, records attempt/start status, dispatches by job type, and records completion or a safe FAILED result. It depends only on a session factory and adapters, making migration to a worker process straightforward. The current process-local scheduler is not durable.

## Agent modules

`tools/operational_tools.py` adapts typed tool requests to existing services. Inputs are Pydantic schemas; outputs are structured records or safe tool errors. No tool accepts raw SQL.

`tools/registry.py` is the allowlist and execution boundary. It validates arguments, measures duration, categorizes failure, and exposes provider-neutral schemas.

`agents/model_provider.py` translates the internal tool/synthesis protocol to Gemini/OpenAI-compatible provider HTTP. It owns timeouts and malformed-output categorization, but no business decisions.

`agents/model_orchestrator.py` runs at most four model rounds/four tools and forces final synthesis. It grounds response type/actions in successful tool results. Provider failure is caught by the assistant service, which invokes `deterministic_agent.py`.

`repositories/conversation_repository.py` persists visible messages, structured payloads, and tool audit. It deliberately excludes chain-of-thought.

## Retrieval and vision

`rag/document_loader.py` extracts PDF/text; `chunker.py` creates overlapping windows; `embedding_service.py` creates normalized local vectors; `vector_repository.py` persists/ranks chunks; `retrieval_service.py` returns cited results. Inputs are report text/query; outputs always retain provenance. Empty/unparseable reports fail their job safely.

`vision/base.py` defines the analyzer contract. `analyzer.py` selects disabled or Gemini behavior. `schemas.py` constrains findings and communicates that a human review is needed. A disabled provider returns no invented defect.

## Database and operations

`backend/migrations` is the executable schema history; never edit an applied revision in production. `scripts/seed_demo_data.py` creates idempotent synthetic records for all major flows.

`docker-compose.yml` connects PostgreSQL, backend, and frontend. Backend startup migrates before serving; uploaded files and database state use named volumes.

`backend/tests` uses isolated SQLite for fast domain/API tests while migration SQL is checked for PostgreSQL. The most important suites cover risk, transitions, agent tools/providers, RAG, uploads, and standard failures.

## High-value failure traces

- Agent timeout: request ID → provider error log → deterministic fallback → visible provider label.
- Upload failure: validation/storage → transaction rollback → stored-file cleanup → stable API error.
- Report failure: job ID → FAILED/error code → report status → controlled retry.
- Stale UI: browser request → API error contract → backend request log → service/repository query.
