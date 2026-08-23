# Phase 3 — Backend Services and REST API

## What We Built

- Site, inspection, anomaly, and dashboard repositories using SQLAlchemy 2-style selects.
- Application services that own lookup rules, transactions, uniqueness conflicts, status transitions, resolution timestamps, and aggregate use cases.
- Thin FastAPI routes for CRUD, nested site histories, anomaly creation, filters, and pagination.
- Consistent error envelopes for domain errors and Pydantic/FastAPI validation failures.
- Dashboard metrics and compact recent/high-risk collections sourced from database queries.
- Request filtering by site type/status/risk, inspection state/date, and anomaly severity/status.
- Twenty-two passing backend tests, including live use cases and failure paths.

## Why We Built It

Routes are transport adapters, not the application. Keeping database queries in repositories and business decisions in services lets future agent tools call the same trusted capabilities without simulating HTTP or writing SQL. It also keeps transaction behavior testable and makes error mappings consistent.

## Architecture

```text
HTTP request
    ↓
FastAPI route
    ↓ validated Pydantic schema
Application service
    ↓ business rules + transaction boundary
Repository
    ↓ SQLAlchemy select/flush
PostgreSQL
    ↓
Pydantic response
    ↓
JSON + X-Request-ID
```

Future agent path:

```text
Agent tool → same application service → same repository → PostgreSQL
```

## Important Files

- `backend/app/api/routes/sites.py`: site CRUD and nested site histories.
- `backend/app/api/routes/inspections.py`: inspection CRUD and nested anomaly creation.
- `backend/app/api/routes/anomalies.py`: cross-site anomaly queries and updates.
- `backend/app/api/routes/dashboard.py`: dashboard summary transport.
- `backend/app/api/errors.py`: expected error and validation envelopes.
- `backend/app/repositories/*`: query construction, filtering, counts, ordering, and eager loading.
- `backend/app/services/*`: business use cases and transaction decisions.
- `backend/app/schemas/pagination.py`: typed bounded page contract.
- `backend/tests/test_api.py`: end-to-end API scenarios using an isolated database.

## Important Code

### Thin route handlers

Routes declare HTTP paths, query validation, response models, and status codes. Each constructs one service and delegates the use case. If a route begins making transaction or query decisions, that logic belongs in a service or repository instead.

### Repository query composition

Repositories build explicit `select()` statements and apply only requested filters. Counts are calculated before offset/limit. Collection queries use stable secondary ordering, and inspection responses use eager anomaly loading to avoid serialization-time N+1 queries.

### Transactional inspection creation

`InspectionService.create()` verifies the site, constructs the inspection and nested anomaly graph, flushes it through the repository, and commits once. A relationship or constraint failure rolls back the transaction, preventing a saved inspection with missing anomalies.

### Controlled state transitions

Inspection transitions are allowlisted: scheduled inspections can start or cancel; in-progress inspections can complete or cancel; completed/cancelled records cannot arbitrarily re-enter workflow. Anomaly transitions are separately allowlisted. The service—not the client—sets or clears `resolved_at`.

### Error contracts

Expected domain failures raise typed exceptions with status and stable error codes. One FastAPI handler converts them into a safe envelope. Validation failures use the same outer shape with status 422. Request IDs connect the client-visible error to structured logs.

## Interview Questions and Model Answers

1. **Why keep routes thin?** Routes should translate HTTP. Services remain reusable from tests, agent tools, jobs, and other transports.
2. **Why introduce repositories?** They centralize SQLAlchemy query mechanics and keep services focused on use-case decisions. They also make allowed data access explicit for later tools.
3. **Where is the transaction boundary?** The service method. It knows which writes form one business operation and commits once or rolls back on failure.
4. **What is the difference between flush and commit?** Flush sends pending SQL inside the current transaction and obtains generated values; commit makes the transaction durable and releases its connection.
5. **Why call rollback after an integrity error?** SQLAlchemy marks the session transaction inactive after a failed flush. Explicit rollback returns it to a usable state.
6. **Why does POST return 201?** A new resource was created. Reads and successful updates return 200.
7. **When do you return 400, 404, 409, and 422?** Invalid use-case/filter request, missing resource, resource/state conflict, and schema validation failure respectively.
8. **How is pagination implemented?** A bounded page/page-size input, a filtered total count, stable ordering, offset/limit, and `has_next` in the response.
9. **How do you avoid N+1 queries?** Select only needed relationships with `selectinload` for response shapes that include nested collections.
10. **Why not expose SQLAlchemy models directly?** Pydantic response schemas define public fields and validation independently from storage internals.
11. **How does nested inspection creation remain atomic?** The inspection and anomalies share one SQLAlchemy session and one commit.
12. **Why is risk still unchanged after an inspection in this phase?** The authoritative formula is deliberately deferred to Phase 7. A temporary or random calculation would create misleading behavior and later rework.

## Things I Must Understand

- [ ] HTTP methods and 200/201/400/404/409/422 semantics.
- [ ] FastAPI dependencies, path/query/body validation, and response models.
- [ ] Route versus service versus repository responsibilities.
- [ ] SQLAlchemy `select`, scalar results, eager loading, flush, commit, and rollback.
- [ ] Atomic nested writes.
- [ ] Optimistic pre-checks plus database constraints for race safety.
- [ ] Pagination count and stable ordering.
- [ ] State-machine transition allowlists.
- [ ] Error codes versus human-readable messages.
- [ ] Request IDs and structured logs.
- [ ] Why risk recalculation waits for the deterministic risk phase.

## How To Test It

1. Apply migrations and seed data from the README.
2. Start FastAPI and open `/docs`.
3. `GET /api/sites`; verify 10 seeded records and pagination metadata.
4. Filter `/api/sites?risk_level=CRITICAL`; verify two seeded critical sites.
5. `POST /api/sites`; verify 201, then open its detail endpoint.
6. Repeat the name with different casing; verify 409 `site_name_conflict`.
7. `POST /api/inspections` with nested anomalies; verify all records and site history.
8. Resolve an anomaly with PATCH; verify `resolved_at` is server-generated.
9. Attempt an illegal inspection transition; verify 409.
10. Submit a malformed UUID or unknown request field; verify the structured 422 response.
11. Request `/api/dashboard/summary`; verify metrics match the stored records.
12. Run `ruff check .`, `ruff format --check .`, and `pytest` from `backend`.

## Current System Flow

```text
Next.js connectivity page
        ↓
FastAPI REST API
        ↓
Routes
  ├─ sites
  ├─ inspections
  ├─ anomalies
  └─ dashboard
        ↓
Application services
        ↓
Repositories
        ↓
SQLAlchemy Session
        ↓
PostgreSQL schema managed by Alembic
```

## Debugging Notes

- A repository method named `list` shadowed Python's built-in name for a later evaluated type annotation. Postponed annotations removed runtime annotation evaluation and preserved the public method name.
- A diagnostic script assumed every FastAPI route object directly exposed `.path`; the current FastAPI version uses a lazy included-router object. OpenAPI generation replaced the internal-object inspection and verified all public paths.
- The first Prettier/API checks were not involved in this backend phase. Ruff found one stale test import after schema refactoring; it was removed.
- No PostgreSQL runtime exists locally. The live Uvicorn smoke test used a temporary migrated/seeded SQLite database, then removed it. PostgreSQL-specific migration SQL remains covered separately.
