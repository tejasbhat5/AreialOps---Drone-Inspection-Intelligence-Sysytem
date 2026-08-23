# Phase 2 — PostgreSQL and Data Model

## What We Built

- PostgreSQL configuration using the `postgresql+psycopg` SQLAlchemy dialect.
- Cached SQLAlchemy engine/session factories with request-scoped session support.
- Seven required persistence models: Site, Inspection, InspectionImage, Anomaly, InspectionReport, RiskAssessment, and ProcessingJob.
- Shared domain enums, UUID primary keys, timezone-aware timestamps, relationships, foreign keys, checks, uniqueness rules, and query-driven indexes.
- Pydantic create/read schemas that validate transport input independently of persistence.
- Alembic configuration and a frozen initial migration with PostgreSQL-native enum DDL.
- An idempotent synthetic seed command with 10 sites, 20 inspections, 28 anomalies, six reports, five image records, 10 risk assessments, and six jobs.
- A readiness endpoint that returns 200 only when the database accepts a query and 503 otherwise.
- Model, schema, seed, migration SQL, and migration upgrade/downgrade tests.

## Why We Built It

PostgreSQL is the operational source of truth. The AI and frontend will depend on stable relationships and constraints rather than loosely related documents. Alembic makes schema changes explicit and deployable, while SQLAlchemy maps relational records into Python objects without moving business rules into SQL queries.

## Architecture

```text
FastAPI dependency
      ↓
SQLAlchemy Session
      ↓
ORM model / repository (Phase 3)
      ↓
psycopg driver
      ↓
PostgreSQL
```

Schema delivery follows:

```text
SQLAlchemy metadata
      ↓ reviewed difference
Alembic revision
      ↓ alembic upgrade head
PostgreSQL schema
```

## Important Files

- `backend/app/db/base.py`: declarative base, naming convention, UUID and timestamp mixins.
- `backend/app/db/session.py`: engine, session factory, request dependency, and readiness query.
- `backend/app/models/*.py`: table mappings, relationships, constraints, and indexes.
- `backend/app/models/enums.py`: shared persisted vocabulary.
- `backend/app/schemas/*.py`: Pydantic request/response validation contracts.
- `backend/alembic/env.py`: connects Alembic to settings and model metadata.
- `backend/alembic/versions/20260822_0001_initial_schema.py`: frozen initial database revision.
- `backend/scripts/seed_demo_data.py`: stable, idempotent synthetic dataset.
- `backend/tests/test_models.py`: constraints, schemas, relationships, and seed tests.
- `backend/tests/test_migrations.py`: PostgreSQL SQL generation and migration round-trip tests.

## Important Code

### Declarative metadata and naming convention

`Base` supplies predictable names for primary keys, foreign keys, checks, uniqueness constraints, and indexes. Predictable names matter when Alembic needs to alter or remove a constraint. UUID and timestamp mixins eliminate repetition without hiding entity-specific fields.

### Relationship and foreign-key design

Every inspection belongs to a site. Images, anomalies, and a report belong to an inspection. Risk assessments belong to a site. Processing jobs point to exactly one report or image. ORM relationships make navigation convenient; database foreign keys remain the authoritative integrity mechanism if data is written outside the ORM.

### Database constraints plus Pydantic validation

Coordinates, risk ranges, positive upload sizes, resolved anomaly timestamps, non-negative attempts, and one-source job rules are protected in PostgreSQL. Pydantic repeats user-facing validation where it can return a useful 422 response. The database constraint is still necessary for race conditions and non-API writers.

### Immutable risk history and site snapshot

`RiskAssessment` records score, level, formula version, factor snapshot, and calculation time. `Site` stores only the current score/level for fast map and dashboard reads. Phase 7 will calculate both in one transaction.

### Idempotent seed IDs

The seed script generates UUIDv5 identifiers from a fixed namespace and semantic names. It checks each stable ID before inserting, so running it twice returns identical counts rather than duplicating demo data.

## Interview Questions and Model Answers

1. **Why PostgreSQL rather than MongoDB?** The domain has strong relationships, transaction requirements, integrity constraints, and aggregation needs. PostgreSQL also allows pgvector later without adding another database.
2. **Why keep Pydantic schemas separate from SQLAlchemy models?** Persistence models describe tables and relationships; Pydantic schemas describe allowed API input and output. Separating them prevents database-only fields from accidentally becoming public contracts.
3. **Why use UUID primary keys?** They can be generated without a database round trip, are difficult to enumerate, and work well across future ingestion workers. Their larger indexes are an accepted tradeoff for this project.
4. **What does Alembic solve?** It records ordered, reviewable schema changes and applies them consistently across developer, test, and production databases.
5. **Why not call `Base.metadata.create_all()` in production?** It creates missing objects but does not provide reviewed upgrades, data migrations, ordered history, or safe modification/removal behavior.
6. **Why use database constraints when Pydantic already validates?** Pydantic only protects requests that pass through that schema. Constraints protect the data against concurrency, scripts, bugs, and other writers.
7. **Why denormalize current risk onto Site?** Dashboard and map queries need the current value frequently. Historical assessments remain normalized and immutable for auditability.
8. **Why restrict site deletion?** Inspections and findings are operational history. Archiving is safer than cascading deletion of evidence.
9. **Why does Anomaly contain both site and inspection IDs?** The inspection identifies origin; the site key supports efficient site-level operational queries. The service must enforce that both reference the same site.
10. **What indexes were chosen?** Indexes match planned name lookup, site filters, map coordinates, recent site inspections, unresolved anomaly filters, risk history, and pending-job queries.
11. **How is one report per inspection enforced?** A unique constraint on `inspection_reports.inspection_id`, reinforced by a scalar ORM relationship.
12. **What happens when PostgreSQL is offline?** Liveness remains 200, but readiness returns 503. Request services will later translate connection failures safely and logs retain the request ID.

## Things I Must Understand

- [ ] Tables, rows, primary keys, foreign keys, and cardinality.
- [ ] One-to-many versus one-to-one relationships.
- [ ] ORM relationships versus database foreign-key enforcement.
- [ ] Unique and check constraints.
- [ ] Why indexes accelerate reads but cost storage and write work.
- [ ] SQLAlchemy engine, connection pool, session, flush, commit, and rollback.
- [ ] Application defaults versus database server defaults.
- [ ] Alembic revision, upgrade, downgrade, head, and autogenerate check.
- [ ] Why migrations are frozen rather than importing live models.
- [ ] Pydantic validation versus database validation.
- [ ] UUID and timezone-aware timestamp tradeoffs.
- [ ] Why demo data must be synthetic and idempotent.

## How To Test It

1. Start PostgreSQL and create the `aerialops` role/database shown in the README.
2. Copy `backend/.env.example` to `backend/.env` and adjust credentials.
3. Run `alembic upgrade head`; expect revision `20260822_0001`.
4. Run `alembic current`; expect `20260822_0001 (head)`.
5. Run `python -m scripts.seed_demo_data` twice; both runs must show identical counts.
6. Start FastAPI and request `/ready`; expect 200 with `database: ok`.
7. Stop PostgreSQL and request `/ready`; expect 503 with `database: unavailable`.
8. Run `alembic upgrade head --sql` to review PostgreSQL DDL without a server.
9. Run `ruff check .`, `ruff format --check .`, and `pytest` from `backend`.

## Current System Flow

```text
Next.js
  ↓ HTTP
FastAPI
  ↓ dependency
SQLAlchemy Session
  ↓ psycopg
PostgreSQL
  ├─ sites
  ├─ inspections
  ├─ inspection_images
  ├─ anomalies
  ├─ inspection_reports
  ├─ risk_assessments
  └─ processing_jobs
```

Repositories and services intentionally arrive in Phase 3. Routes do not yet perform domain CRUD.

## Debugging Notes

- PostgreSQL, `psql`, and Docker were not installed locally. PostgreSQL DDL was verified through Alembic offline mode, and migration behavior through an isolated SQLite test dialect. A live PostgreSQL upgrade remains a manual environment step.
- The initial model lint pass found import ordering and line-length issues; Ruff formatted and normalized them.
- Pytest's default temporary folder was sandbox-denied. The test configuration now uses the writable `backend/.pytest-tmp` directory, which is ignored by Git.
- SQLite cannot reflect PostgreSQL-style expression indexes during Alembic drift comparison. The frozen SQL and metadata both contain `uq_sites_name_lower`, and PostgreSQL offline DDL confirms it renders as `CREATE UNIQUE INDEX ... lower(name)`.
- The first absent-database readiness probe waited too long for the driver default. The development URL now uses `127.0.0.1` and a two-second connection timeout so readiness fails promptly.
