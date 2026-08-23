# Final Engineering Review

Review date: 2026-08-23. Scores reflect a portfolio MVP, not a production certification.

| Area | Score | Evidence / remaining gap |
|---|---:|---|
| Frontend | 8.5/10 | Complete meaningful routes, typed API, responsive hierarchy; no browser E2E suite. |
| Backend | 9/10 | Thin routes, service/repository boundaries, validation and safe errors. |
| Database | 8.5/10 | Constraints, indexes, migrations, seed; production currently expects PostgreSQL but tests use SQLite. |
| Architecture | 9/10 | Clear boundaries and deliberate MVP tradeoffs. |
| REST API | 8.5/10 | Consistent contracts/status codes/pagination; no auth/version prefix. |
| Agent architecture | 9/10 | Allowlisted tools, bounded orchestration, local fallback, no raw SQL. |
| Tool calling | 9/10 | Typed single/multi-tool flows and synthesis-only terminal round. |
| RAG | 7.5/10 | Complete cited pipeline; local hash vectors lack production semantic quality/indexing. |
| Geospatial | 8/10 | Leaflet map, risk markers, filters/popups; no PostGIS/spatial queries. |
| Testing | 8.5/10 | Broad backend unit/API/provider/failure coverage; limited frontend automation. |
| Observability | 8/10 | Structured IDs, durations, tools/jobs/provider errors; no metrics/tracing backend. |
| Documentation | 9/10 | Architecture, phases, README, walkthrough, interview guide and limitations. |
| Interview readiness | 9/10 | Demonstrable flows and honest tradeoffs; owner must rehearse them. |

## Critical problems addressed

- Provider exploration could exhaust three rounds and time out. The model now has four bounded rounds and receives no tools on its final synthesis turn.
- Report content had no grounded retrieval path. Reports now have chunks, embeddings, provenance, search endpoints, citations, and agent tools.
- Upload jobs were metadata only. A runner now executes status transitions and safe failure recording.
- Report and settings navigation were absent. Both are meaningful working pages.
- Deployment and completion documentation were missing. Compose, Dockerfiles, README, interview guide, and module walkthrough now exist.

## Important improvements before production

1. Rotate any development API key ever copied into a tracked/template file and use a secret manager.
2. Add authentication, role/tenant authorization, audit retention, and rate limits.
3. Move files to object storage and work to durable idempotent workers.
4. Upgrade retrieval to a production embedding model + pgvector and build labelled retrieval evaluations.
5. Add Playwright workflows for the six demo scenarios and CI with PostgreSQL.

## Optional improvements

- PostGIS for corridor/polygon/intersection queries—not merely map points.
- Redis caching only after profiling dashboard/agent reads.
- Specialized calibrated vision after collecting representative labelled data.
- OpenTelemetry traces and SLO dashboards.

## Final quality questions

1. Without “AI”, “agent”, or “drone,” is it legitimate full-stack software? **Yes:** it has relational workflows, uploads, deterministic domain logic, maps, jobs, APIs, tests, and deployment.
2. Does the agent perform application actions? **Yes:** it selects and sequences allowlisted service-backed tools over real records.
3. Can the owner explain it without AI? **Only after rehearsing** the interview guide and tracing the demonstrated flows personally.
