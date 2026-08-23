# AerialOps Interview Notes

This is the maintained question bank requested during the phased build. It is organized for later export and will continue to grow with each phase.

## Skylark Drones Role Alignment

- Explain AerialOps in 30 seconds as an AI-assisted drone inspection and geospatial intelligence platform.
- Which parts currently demonstrate full-stack ownership, and which parts are roadmap architecture?
- How does the product turn field evidence into an enterprise decision?
- How does the project map to Spectra's solar planning, monitoring, and inspection workflows?
- What would change when moving from ten sites to thousands of sites and petabytes of imagery?
- How would you collaborate across product, geospatial, computer-vision, and drone-operations teams?

## Phase 6 — Ingestion

- How would you process a 20 GB drone-image upload without blocking an API request?
- Where would you store original imagery, derived tiles, metadata, and processing results?
- Why verify magic bytes as well as MIME type and filename extension?
- How do opaque storage keys prevent path traversal and filename collisions?
- How do you avoid an orphaned file when the database transaction fails?
- Why create a durable pending job during upload?
- How would you implement retries, idempotency, leases, heartbeats, and a dead-letter path?
- What are the limitations of proxying uploads through a Next.js Server Action?
- When would you switch to signed direct-to-object-storage multipart uploads?
- How would authentication, authorization, antivirus scanning, quotas, and tenant isolation fit here?

## Phase 8 — Controlled AI Agent Foundation

- When should an LLM call a tool instead of answering from context?
- How do you prevent an agent from hallucinating site state?
- Why should agent tools call application services rather than query the database directly?
- How would you evaluate an agent that investigates inspection anomalies?
- Why combine deterministic risk logic with LLM explanations?
- How would you cap tool calls, latency, token cost, and result size?
- How would you log agent decisions without exposing sensitive enterprise data?
- Why expose a provider-neutral tool schema before integrating an LLM?
- What does the tool allowlist prevent, and where must authorization still be enforced?
- Why validate both tool inputs and outputs with Pydantic?
- Why persist user-visible tool activity but not hidden chain-of-thought?
- How does the four-call limit constrain latency and runaway execution?
- What would you measure before replacing the deterministic planner with model tool calling?
- How do structured response types keep the assistant UI reliable?
- How should an unknown site UUID or unavailable tool fail without leaking internals?

## Phase 9 — Model Tool Calling

- Why use the Responses API instead of giving the model direct database access?
- What information crosses the model-provider boundary, and what remains server-side?
- How does the application validate model-generated tool arguments?
- Why enforce both a model-round limit and an application tool-call limit?
- How does `store: false` change conversation handling?
- Why is parallel tool calling disabled for this first implementation?
- How does JSON Schema make the final model response safer for the frontend?
- What happens when the model returns malformed JSON or an unknown tool name?
- Why retain a deterministic fallback after connecting a real model?
- How would you evaluate whether model tool selection improves on the local planner?

## Product UI/UX Refinement

- How do visual hierarchy and surface contrast reduce cognitive load in an operations dashboard?
- Why should navigation labels describe outcomes rather than only name data entities?
- How do route-specific headers help users maintain context in a multi-page application?
- How do risk colors remain accessible without making the entire interface feel alarming?
- Why reserve the primary accent color for navigation state, links, focus, and major actions?
- How would you validate this information architecture with field operators and enterprise users?

## Phase 7 — Deterministic Risk

- Why should an LLM explain risk but never calculate the authoritative score?
- How do formula versions and factor snapshots make a decision reproducible?
- Why cap severity and volume contributions independently?
- Why can a site with no anomalies still receive ten risk points?
- Why use only completed inspections for the recency factor?
- How are anomaly transitions and risk updates committed atomically?
- Why is current risk denormalized onto `Site` while assessment history remains append-only?
- How would concurrent recalculations create stale-write risk, and how would you prevent it?
- How would you calibrate weights using historical maintenance outcomes?
- How would you roll out `deterministic-v2` and compare it with version one safely?
