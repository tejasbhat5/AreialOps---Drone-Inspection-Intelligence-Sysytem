# Phase 0 — Requirements and Architecture

## What and why

Defined the product boundary, relational model, REST contracts, agent/RAG flows, failure rules, and phased delivery in `docs/architecture.md`, `data-model.md`, and `api-plan.md`. This prevents an LLM-first demo from replacing a legitimate full-stack product.

## Architecture

```text
Next.js → FastAPI routes → services → repositories → PostgreSQL
                         ↘ typed tools/RAG ← bounded agent
```

## Important files and code

- `architecture.md`: runtime components, trust boundaries, workflows, observability.
- `data-model.md`: entities, keys, constraints, indexes, lifecycle states.
- `api-plan.md`: routes, status codes, pagination, error envelope.

The key decisions are service-backed tools, deterministic authoritative risk, relational integrity, and asynchronous ingestion. If these boundaries fail, the model could bypass validation or product logic.

## Interview questions

1. **Why architecture before code?** It exposes boundaries and tradeoffs before implementation inertia.
2. **Why a modular monolith?** It is deployable and understandable while preserving internal seams.
3. **Why REST?** It gives stable typed contracts between independently runnable layers.
4. **Why PostgreSQL?** Relations, constraints, transactions, and reporting fit the domain.
5. **Main trust boundary?** All external/model input is validated before services execute it.

## Must understand and test

- [ ] Trace REST and agent flows; explain which layer owns each rule.
- [ ] Explain MVP versus production choices.
- [ ] Review Mermaid diagrams and verify every planned core entity/route has an owner.

## Current flow

```text
Requirement → API/data/agent contract → phased implementation → verification
```
