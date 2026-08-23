# AerialOps Interview Guide

## 30-second explanation

AerialOps is a full-stack inspection-intelligence platform for infrastructure operators. A Next.js UI displays sites, inspections, anomalies, risk, and maps from a FastAPI/PostgreSQL backend. Its AI assistant is an actual bounded agent: Gemini or a local planner selects typed tools that call application services. Risk remains deterministic, report answers use retrieved citations, and provider failures fall back safely.

## 2-minute explanation

The product solves fragmented field-inspection data. Operators create sites and inspections, attach reports and images, record anomalies, and see a reproducible 0–100 risk score. React Server Components fetch typed REST data and client components handle interactive forms, chat, and Leaflet.

The backend is separated into routes, services, repositories, and SQLAlchemy models. That keeps HTTP, business rules, and persistence independently testable. Uploads are verified by signatures, stored under generated keys, and produce durable jobs. Report jobs extract text, chunk it, create deterministic local embeddings, and store source metadata for cited retrieval.

The agent receives only allowlisted JSON-schema tools. A tool validates model arguments, calls an application service, and returns structured data. The model never receives database credentials or raw SQL access. Tool calls and model rounds are capped; timeouts and malformed provider output fall back to the deterministic planner. This is an honest MVP: local storage, process-local jobs, and assistive—not certified—vision are documented limitations.

## 5-minute technical walkthrough

Start at `/dashboard`: Next.js calls `lib/api.ts`, FastAPI routes call services, repositories issue SQLAlchemy queries, and PostgreSQL returns domain data. Explain `Site → Inspection → Anomaly` plus reports, chunks, images, jobs, and append-only risk assessments. Then create an inspection: Pydantic validates it, one service transaction saves its anomalies and recalculates risk, and the UI immediately reads the updated aggregates.

Next open `/assistant`. The request is persisted with a request/conversation ID. The provider selects from a registry of typed tools. A “compare highest risk” query first ranks sites and then compares structured records. The orchestrator limits four tool calls and four model rounds; its last round is synthesis-only. The response contains an enum response type, data, safe actions, and visible tool activity—never hidden reasoning.

Finally show `/reports`. An uploaded report creates a PENDING job. Background processing marks it PROCESSING, extracts and chunks text, embeds chunks, stores them, then marks both report and job COMPLETED. Search embeds the question, performs cosine ranking, and returns excerpts with report/inspection/site IDs. Close with tradeoffs: BackgroundTasks and JSON embeddings keep the MVP understandable; durable workers, object storage, pgvector, authentication, and retrieval evaluations are the production path.

## Question bank with model answers

1. **Why this architecture?** It separates UI, HTTP, business rules, and persistence so each can change and be tested independently.
2. **Why Next.js?** It provides routing, server rendering, server actions, and a strong typed React production model.
3. **Server versus client components?** Data-first pages render on the server; stateful forms, chat, and Leaflet use client components.
4. **Why an API client abstraction?** It centralizes base URLs, JSON/error handling, timeouts, and response types.
5. **How are loading failures represented?** Route loading/error boundaries and explicit form states keep failures visible and recoverable.
6. **Why reusable cards and badges?** They keep risk semantics and layout consistent across dashboard, sites, and inspections.
7. **How is the UI responsive?** Grid breakpoints collapse navigation and multi-column panels while preserving touch targets.
8. **Why Leaflet?** It is lightweight, open source, and sufficient for point visualization without vendor lock-in.
9. **How do coordinates reach the map?** PostgreSQL numeric columns → SQLAlchemy/Pydantic → REST JSON → typed React props → Leaflet markers.
10. **Are demo coordinates real assets?** No. They are synthetic demonstration locations and are explicitly labelled as such.
11. **Why FastAPI?** Typed request validation, dependency injection, OpenAPI, and good async upload support fit this API.
12. **Why thin routes?** Routes translate HTTP; services own business rules, preventing duplicated logic across REST and agent tools.
13. **Why repositories?** They isolate query composition and make persistence behavior easier to optimize and test.
14. **Why Pydantic?** It rejects malformed external and model-generated data before business logic runs.
15. **Why consistent error envelopes?** Clients can handle stable codes while safe messages and request IDs support diagnosis.
16. **Why 422 for validation?** FastAPI uses it when syntax is valid HTTP/JSON but fields violate the declared schema.
17. **Why PostgreSQL instead of MongoDB?** The domain has strong relations, transactions, constraints, filters, and reporting queries.
18. **Why UUIDs?** They avoid centralized ID allocation and make identifiers harder to enumerate, though authorization is still required.
19. **Which indexes matter?** Foreign keys and status/date/risk filter columns used by lists, dashboards, and job polling.
20. **Why Alembic?** It versions schema changes and makes deployment upgrades repeatable and reviewable.
21. **How is inspection creation atomic?** The inspection, anomalies, and risk update share one transaction; any failure rolls it back.
22. **Why append risk assessments?** Historical snapshots make operational decisions reproducible and auditable.
23. **Why denormalize current risk on Site?** Dashboards and maps read it frequently; the assessment table retains history.
24. **How is risk calculated?** Bounded severity, critical bonus, finding volume, and inspection recency sum to a capped 0–100 score.
25. **Why not let the LLM calculate risk?** Risk must be deterministic, testable, explainable, and consistent across requests.
26. **How would you tune weights?** Version a new formula, replay historical outcomes, compare calibration, then roll it out gradually.
27. **What makes this an agent?** A model/planner selects and sequences real application tools, observes results, then synthesizes typed output.
28. **Why not raw SQL from the model?** It bypasses authorization and business rules and creates injection, leakage, and mutation risk.
29. **How are tools controlled?** An allowlisted registry exposes JSON schemas; Pydantic validates arguments and results.
30. **What if the model invents a site ID?** Service lookup returns a typed not-found tool error; the agent clarifies or falls back safely.
31. **How does multi-tool behavior work?** Tool results are appended to provider context until evidence is sufficient or a bound is reached.
32. **Why cap tool calls and rounds?** It limits latency, spend, loops, and the blast radius of bad model planning.
33. **Why is the last round synthesis-only?** It guarantees the model must answer from gathered evidence instead of endlessly exploring tools.
34. **What happens on provider timeout?** The provider raises a categorized error, logs metadata, and the local planner serves supported operations.
35. **Do you store chain-of-thought?** No. Only user-visible answers, structured results, and tool audit metadata are persisted.
36. **How are secrets protected?** Keys live only in ignored backend environment files and are never sent to browser variables or logs.
37. **What is RAG?** Retrieval selects relevant stored report chunks and supplies source-grounded context for an answer.
38. **How does chunking work?** Text is split into bounded overlapping word windows so concepts near boundaries remain retrievable.
39. **What is an embedding here?** A deterministic normalized signed-hash vector representing tokens for local similarity ranking.
40. **Why local embeddings?** They are free, private, reproducible, and sufficient to demonstrate architecture; semantic quality is limited.
41. **How is similarity computed?** Query and chunk vectors are normalized, so their dot product is cosine similarity.
42. **What makes a report answer grounded?** Returned citations contain the exact excerpt plus report, inspection, and site provenance.
43. **Why not pgvector yet?** For demo volume JSON vectors and Python ranking are simpler; the repository boundary enables a later pgvector swap.
44. **How would retrieval scale?** Use a production embedding model, pgvector HNSW/IVFFlat, tenant filters, and offline relevance evaluations.
45. **Why background processing?** Parsing, embedding, and image inference should not hold an upload request open.
46. **What is the job lifecycle?** PENDING → PROCESSING → COMPLETED or FAILED, with attempts and safe error metadata.
47. **Limitation of BackgroundTasks?** Work is process-local and can be lost on restart; it lacks leases, worker scaling, and dead-letter handling.
48. **Production job replacement?** A durable queue and idempotent workers with leases, heartbeats, retries, and dead-letter inspection.
49. **How are uploads secured?** Generated storage keys, filename checks, size limits, MIME/signature checks, and database constraints.
50. **What upload security is missing?** Authentication, tenant authorization, malware scanning, quotas, object storage, and content-disposition controls.
51. **What does vision claim?** Only general AI-assisted findings pending human review—not certified industrial defect detection.
52. **Why a vision interface?** Disabled, Gemini, or future specialized analyzers can be swapped without changing the job workflow.
53. **What backend tests matter most?** Risk boundaries, atomic writes, invalid transitions, tools, fallback behavior, RAG citations, and API errors.
54. **How do tests avoid real Gemini spend?** An autouse fixture forces the deterministic provider and removes provider keys.
55. **Why Docker Compose?** It reproduces the frontend/API/PostgreSQL topology and migration startup in one command.
56. **How would you observe production?** Structured logs plus metrics for latency/errors/tool calls/jobs, traces across services, and alerting.
57. **How would one million inspections change it?** Partition/optimize queries, object storage, async workers, vector indexes, caching, and archival policies.
58. **What if PostgreSQL bottlenecks?** Profile first, add indexes/query fixes, cache read aggregates, use replicas, then partition if evidence warrants it.
59. **How would tenancy work?** Add tenant IDs, enforce service/repository scopes and database row policies, and authorize every file/tool access.
60. **Biggest honest limitation?** It is a polished MVP, not production: identity, durable jobs, object storage, and retrieval evaluation remain.

## Questions that catch AI-generated projects

- **Walk me through `model_orchestrator.py`.** Explain context construction, bounded provider rounds, registry execution, grounded response typing, and fallback—not every line.
- **Which decisions did you personally make?** Say which tradeoffs you accepted: deterministic risk, allowlisted tools, local embeddings, BackgroundTasks, and disabled-by-default vision.
- **Which parts were AI-assisted?** Be honest: AI accelerated implementation/review, while you validated behavior, ran tests, and must be able to defend every retained decision.
- **How would you debug a failed tool?** Follow request ID → agent log → tool activity/error code → service/repository test → reproduce with the direct tool.
- **What would you remove first?** Vision is deliberately secondary; protect the core site/inspection/risk/agent/RAG flows.
- **What was a real debugging lesson?** Provider loops need application-enforced bounds and a synthesis-only final turn; prompt wording alone is insufficient.

## Understand-before-claiming checklist

- Trace one dashboard request and one agent request end to end.
- Reproduce the risk score by hand from a factor snapshot.
- Explain a database transaction rollback and an Alembic upgrade.
- Explain cosine similarity and the limits of local hash embeddings.
- Demonstrate deterministic provider fallback with the key removed.
- Explain why BackgroundTasks and local disk are not production durability.
- Run the test/lint/build commands yourself and interpret a failure.
