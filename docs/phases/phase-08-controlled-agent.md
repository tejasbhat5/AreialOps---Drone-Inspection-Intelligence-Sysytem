# Phase 8 — Controlled AI Agent Foundation

## What We Built

- Eight allowlisted, read-only operational tools covering site lookup, search, inspections,
  anomalies, deterministic risk, high-risk prioritization, and site comparison.
- Pydantic validation for every tool input and output.
- A provider-neutral tool registry with safe error contracts and duration logging.
- A bounded deterministic planner capped at four tool calls per request.
- Persisted conversations and messages with structured assistant payloads and user-visible
  tool audit records.
- A structured assistant API and a responsive `/assistant` workspace.
- Direct tool-boundary tests and end-to-end API tests for comparison, named-site resolution,
  persistence, allowlisting, invalid arguments, and missing resources.

## Safety Boundary

```text
User question
    ↓
Bounded planner (maximum 4 calls)
    ↓
Allowlisted ToolRegistry
    ↓ validates Pydantic input
Application service and repository
    ↓ validates Pydantic output
Structured assistant response + visible tool audit
```

The agent cannot issue SQL, mutate sites, alter the risk formula, invoke an unregistered tool,
or expose internal exceptions. This is the same tool surface a later model provider can use,
but the current planner remains local and deterministic so the product is useful and testable
without an API key.

## Available Tools

```text
get_site_details          search_sites
get_latest_inspection     get_inspections
get_site_anomalies        find_high_risk_sites
compare_sites             calculate_site_risk
```

`calculate_site_risk` calls the authoritative deterministic risk service. Natural-language
explanation is presentation; the agent never invents or changes the score.

## API Contract

```text
POST /api/assistant/conversations
GET  /api/assistant/conversations/{conversation_id}
POST /api/assistant/query
```

Responses carry a stable response type, answer, structured data, suggested UI actions,
provider label, request/conversation IDs, and safe tool activity. Stored records contain the
same user-visible audit—not private reasoning traces.

## Verification Completed

- All 32 backend tests pass.
- Ruff, ESLint, TypeScript, and the Next.js production build pass.
- API tests prove two high-risk sites are selected and compared through exactly two tools.
- A named-site risk question resolves the name before interpreting the generic risk phrase.
- Unregistered tools, malformed UUIDs, missing sites, and unknown conversations fail safely.
- Conversation history persists the user and assistant messages plus the two-call audit.

## Interview Questions

- Why should tools call application services instead of querying the database directly?
- Why validate tool outputs when the handler is trusted application code?
- Which attacks or failures does an allowlist prevent?
- Why cap tool calls independently of any model token limit?
- Why store visible tool audit metadata but not chain-of-thought?
- How would you add tenant authorization to every tool without relying on the model?
- How would you evaluate a model planner against this deterministic baseline?
- Which metrics reveal looping, poor tool selection, excessive latency, or hallucinated answers?
- How would you make a write-capable tool safe using approval, idempotency, and audit trails?

## Next Phase

Phase 9 adds report retrieval and grounded answers: PDF text extraction, chunking, embeddings,
background indexing, citation-bearing search tools, access filtering, and retrieval evaluation.
