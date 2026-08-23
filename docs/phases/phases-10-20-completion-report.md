# Phases 10–20 — Completion Teaching Report

This report completes the remaining phases in one delivery while retaining a phase-by-phase explanation. Detailed interview answers live in `docs/interview-guide.md`.

## Phase 10 — AI Assistant Frontend

### What/why/architecture

Built `/assistant` with persisted exchanges, suggestions, loading/error states, structured site/risk/report cards, citations, site links, and visible tool status. It makes the agent part of operations while never exposing hidden reasoning.

```text
AssistantWorkspace → server action → assistant REST API → typed response → result renderer
```

### Files and important code

- `assistant/assistant-workspace.tsx`: interaction state and response renderer.
- `assistant/actions.ts`: safe server-side API mutation.
- `types/domain.ts`: response discriminators and tool activity.

The response type drives rendering; conversation IDs maintain continuity; tool audit renders only safe labels/durations. A failed call preserves the form and displays a recoverable message.

### Interview questions

1. **Why structured UI instead of Markdown?** It produces reliable navigation and comparisons.
2. **Why a server action?** It keeps the backend URL and mutation handling server-side.
3. **Why show tool audit?** It builds user trust without revealing chain-of-thought.
4. **How are double submits prevented?** Transition state disables prompts/form.
5. **Failure behavior?** A safe API error appears without destroying history.

### Understand/test/current flow

- [ ] Explain client state, response discrimination, and safe audit.
- Test all suggested prompts, site links, failure with backend stopped, and mobile layout.

```text
Question → bounded agent → answer + structured data + audit → React cards
```

## Phase 11 — RAG

### What/why/architecture

Implemented document extraction, overlapping chunking, deterministic embeddings, vector persistence/ranking, citations, REST search, and agent report tools. This grounds report claims in stored evidence without adding another database.

```text
Report → extract → chunk → embed → report_chunks
Query → embed → cosine rank → cited excerpts → agent/UI
```

### Files and important code

- `rag/document_loader.py`, `chunker.py`, `embedding_service.py`.
- `rag/vector_repository.py`, `retrieval_service.py`.
- `models/report_chunk.py`, migration `20260823_0003`.

Vectors are normalized so dot product is cosine similarity. Every chunk retains report/inspection/site provenance. Empty or invalid reports fail indexing rather than creating fake evidence.

### Interview questions

1. **Why overlap chunks?** It preserves context across boundaries.
2. **What is cosine similarity?** Directional vector similarity independent of magnitude.
3. **Why local hash vectors?** Free, private, deterministic MVP retrieval.
4. **Main limitation?** Weaker semantics and linear scan at scale.
5. **Upgrade path?** Production embeddings plus pgvector/HNSW behind the same repository.

### Understand/test/current flow

- [ ] Explain embedding, ranking, provenance, and retrieval limitations.
- Test `/api/reports/search` and the exact Solar Farm Alpha report question; verify a source link.

## Phase 12 — Background Processing

### What/why/architecture

Made upload jobs executable with PENDING → PROCESSING → COMPLETED/FAILED, attempts, safe errors, status API, and controlled retry. Slow extraction/inference no longer belongs to the upload response.

```text
Upload transaction → PENDING job → BackgroundTask runner → adapter → terminal status
```

### Files and important code

- `jobs/runner.py`: claim, dispatch, commit/fail.
- `api/routes/jobs.py`: status and retry.
- `services/upload_service.py`: atomic source/job creation.

The runner accepts a session factory, making it worker-ready and testable. It rolls back processing failures, reloads the job, and stores a safe code/message. BackgroundTasks can still lose work on process death.

### Interview questions

1. **Why persist jobs?** Status survives the request and is inspectable.
2. **Why separate runner?** It can later run in a real worker unchanged.
3. **Why attempts?** Retry policy and diagnosis need history.
4. **Why only retry FAILED?** It avoids duplicating active/completed work.
5. **Production replacement?** Durable queue, leases, idempotency, heartbeats, dead letters.

### Understand/test/current flow

- [ ] Explain state transitions and crash limitations.
- Upload a report, poll its job, and retry a failed/unparseable report.

## Phase 13 — Computer Vision Stretch

### What/why/architecture

Added a provider-neutral analyzer interface, disabled-safe implementation, and optional Gemini adapter. It honestly labels output AI-assisted and requires human review; disabled mode invents no findings.

```text
Image job → VisionAnalyzer protocol → disabled/Gemini → typed findings → review state
```

### Files and important code

- `vision/base.py`: analyzer protocol.
- `vision/analyzer.py`: selection and provider implementation.
- `vision/schemas.py`: bounded findings/confidence/status.

Provider selection is configuration-driven. Image bytes leave the system only when vision is explicitly enabled. Malformed/provider failure marks the job FAILED safely.

### Interview questions

1. **Why not claim defect detection?** A general model is not calibrated/certified.
2. **Why disabled by default?** Privacy, cost, and honest behavior.
3. **Why an interface?** Future specialized models do not change job code.
4. **Why human review?** False positives/negatives affect maintenance decisions.
5. **How validate a real model?** Representative labelled data and per-defect metrics.

### Understand/test/current flow

- [ ] Explain privacy, calibration, and disabled behavior.
- Upload an image with vision disabled; verify completed job and no invented finding.

## Phase 14 — Testing

### What/why/architecture

Expanded backend coverage to 48 tests across schemas, models, repositories/services, API contracts, risk, migrations, uploads, tools, providers, fallback, citations, and jobs. Tests force local deterministic AI to avoid network/cost flakiness.

```text
pytest fixture → isolated DB/app dependency → request/tool/service → assertion
```

### Files and important code

- `tests/conftest.py`: isolated sessions and deterministic settings.
- `test_api.py`, `test_agent_tools.py`, `test_model_agent.py`, `test_rag.py`.

StaticPool shares in-memory SQLite across API threads. PostgreSQL offline migration SQL protects dialect-specific DDL. Failure tests assert stable codes, not internal exception text.

### Interview questions

1. **Why no real Gemini in unit tests?** Non-determinism, cost, latency, outages.
2. **Why API plus unit tests?** Contracts and business boundaries fail differently.
3. **SQLite caveat?** It does not reproduce all PostgreSQL types/concurrency.
4. **Most valuable tests?** Risk boundaries, rollback, tools, fallback, provenance.
5. **Next test layer?** PostgreSQL CI and Playwright demo workflows.

### Understand/test/current flow

- [ ] Be able to explain a fixture and one failure test.
- Run `ruff check .`, `ruff format --check .`, and `pytest`.

## Phase 15 — Docker

### What/why/architecture

Added production-shaped images and Compose for frontend, backend, and PostgreSQL. Backend waits for database health, migrates, then serves; named volumes retain DB/uploads.

```text
Browser → frontend:3000 → backend:8000 → database:5432
```

### Files and important code

- `docker-compose.yml`: service network, health dependency, volumes/env.
- `backend/Dockerfile`, `frontend/Dockerfile`, `.dockerignore` files.

Non-root runtime users reduce container privilege. Secrets are injected, not copied into images. The compose password is explicitly local-only.

### Interview questions

1. **Why multi-stage frontend build?** Build tools do not need to define the runtime layer.
2. **Why health dependency?** Migration cannot run before PostgreSQL accepts connections.
3. **Why volumes?** Container replacement should not erase data.
4. **Why `.dockerignore`?** Smaller context and no local keys/caches.
5. **Production change?** Managed database/secrets/storage and separate migration job.

### Understand/test/current flow

- [ ] Explain service DNS, ports, image layers, and volumes.
- Run `docker compose up --build`; this machine lacks Docker, so execution remains a host limitation.

## Phase 16 — UI Polish

### What/why/architecture

Applied a light professional palette, clearer numbered navigation, route context, differentiated cards, accessible risk color use, responsive layouts, and meaningful Reports/Settings workspaces.

```text
Design tokens → reusable surfaces/navigation → route-specific content hierarchy
```

### Files and important code

- `app/globals.css`: tokens, hierarchy, responsive rules.
- `components/layout/sidebar.tsx`, `topbar.tsx`: navigation/context.
- `reports/*`, `settings/page.tsx`: non-placeholder product functions.

Accent is reserved for focus/navigation/actions; risk colors communicate status locally instead of tinting the whole product. Mobile layouts collapse grids and preserve targets.

### Interview questions

1. **Why light surfaces?** Dense enterprise data needs legible hierarchy.
2. **Why constrain accent usage?** It preserves action and focus salience.
3. **How is risk accessible?** Text labels accompany color.
4. **Why numbered navigation?** It communicates workflow grouping/order.
5. **How validate UX?** Task-based testing with operators, not preference alone.

### Understand/test/current flow

- [ ] Explain hierarchy, responsive rules, and accessible status encoding.
- Inspect every route at desktop/mobile widths and keyboard through forms.

## Phase 17 — README and Documentation

### What/why/architecture

Replaced the stale Phase 3 README with a professional product, architecture, setup, Docker, tests, demo, limitation, and future-work guide. Documentation is part of reproducibility and interview ownership.

### Files/code/questions

- `README.md`, architecture/data/API docs, and all phase reports.
- Mermaid diagrams are source-controlled and renderer-portable.

1. **What belongs in README?** The shortest path to understand/run/evaluate.
2. **Why list limitations?** It distinguishes engineering judgment from hype.
3. **Why diagrams?** They compress boundaries and data flow.
4. **How prevent drift?** Update docs in the same change and verify commands.
5. **Audience?** Evaluator first, then developer/operator.

### Understand/test/current flow

- [ ] Follow setup from a clean environment and check every link/command.

## Phase 18 — Interview Guide

### What/why/architecture

Created 30-second, 2-minute, and 5-minute explanations; 60 technical questions with model answers; AI-generated-project trap questions; and a readiness checklist.

### Files/code/questions

- `docs/interview-guide.md`: primary study file.
- `docs/interview-notes.md`: accumulated phase question bank preserved.

1. **How should you use model answers?** Rewrite them in your own words.
2. **What proves ownership?** Trace code and reproduce/debug behavior live.
3. **Should you hide AI assistance?** No; describe assistance and validation honestly.
4. **Best demo order?** Domain workflow, risk, agent tools, RAG citation.
5. **What not to claim?** Production readiness or certified vision detection.

### Understand/test/current flow

- [ ] Rehearse each pitch aloud and answer questions without opening the guide.

## Phase 19 — Repository Walkthrough

### What/why/architecture

Documented important modules by purpose, inputs, outputs, dependencies, failure modes, and connection to the system. This makes “walk me through this file” answerable.

### Files/code/questions

- `docs/repository-walkthrough.md`: frontend, backend, domain, agent, RAG, jobs, operations.

1. **Where does HTTP stop?** At the route; services receive domain inputs.
2. **Where are transactions?** Service boundaries that coordinate writes.
3. **Where are model calls?** Provider adapters under bounded orchestration.
4. **Where is provenance?** Report chunks and retrieval citation schemas.
5. **Where would a queue connect?** Call `process_job` with a worker session factory.

### Understand/test/current flow

- [ ] Pick one module per layer and trace its callers/dependencies/failures.

## Phase 20 — Final Engineering Review

### What/why/architecture

Performed a strict scored review, fixed critical agent/RAG/job/UI/documentation gaps, and recorded production priorities. Verification covered backend lint/format/tests, migration, frontend type/lint/build, and live Gemini demo scenarios.

### Files/code/questions

- `docs/final-engineering-review.md`: scores, fixed issues, prioritized gaps.
- Critical model fix: four rounds with synthesis-only final turn.
- Critical grounding fix: response type/data prefer report-tool evidence when report search ran.

1. **Strongest area?** Controlled service-backed agent architecture.
2. **Weakest production area?** Identity and durable storage/processing are absent.
3. **Why score RAG lower?** Architecture is complete; embedding quality/indexing is MVP-level.
4. **What was actually run?** 48 tests, Ruff, TypeScript, ESLint, Next production build, migrations, live Gemini tools/RAG.
5. **What could not be run?** Compose, because Docker is not installed locally.

### Understand/test/current flow

- [ ] Review every score and reproduce the commands/demo scenarios.

```text
Code + migrations + docs → static checks/tests/build → live API/agent smoke → reviewed MVP
```
