# Phase 9 — Model-Driven Tool Calling

## 1. What We Built

- An optional OpenAI Responses API provider configured entirely through backend environment
  variables.
- A provider-neutral model-step contract for function calls and structured final answers.
- A bounded model orchestration loop that executes only the eight Phase 8 tools.
- Sequential multi-tool execution with a maximum of three model rounds and four application
  tool calls.
- JSON Schema-constrained final answers and Pydantic validation after receipt.
- Safe mappings for timeouts, authentication failures, HTTP failures, malformed arguments,
  malformed output, and exhausted planning rounds.
- Automatic fallback to the deterministic local planner.
- A capabilities endpoint and assistant UI status that honestly disclose whether model
  planning is configured.
- Mock-transport tests that exercise the real outbound request and response contract without
  spending tokens or requiring a secret.

## 2. Why We Built It

Phase 8 proved that application capabilities were safe and directly testable before a model
was involved. Phase 9 lets a model decide which of those capabilities to use for more varied
language, while preserving the important boundary:

```text
Model chooses a named tool + arguments
Application validates and executes it
Model never receives SQL credentials or a database connection
```

The deterministic fallback keeps local development, demonstrations, and operational queries
available when no provider key exists or an external request fails.

## 3. Architecture

```text
Assistant UI
    ↓ POST /api/assistant/query
AssistantService
    ↓ builds bounded history and request ID
Agent factory
    ├─ no model configuration → deterministic planner
    └─ OpenAI configured → ModelAgentOrchestrator
                              ↓ Responses API
                         function_call item
                              ↓
                         ToolRegistry allowlist
                              ↓ Pydantic input
                         Application service
                              ↓
                         Repository / risk engine
                              ↓ Pydantic output
                         function_call_output
                              ↓ Responses API
                         JSON Schema answer
                              ↓ Pydantic validation
                         Typed AssistantResponse
```

The implementation follows the official Responses API contract for custom function tools,
model instructions, bounded output tokens, tool choice, and JSON-schema text formatting:
[OpenAI Responses API reference](https://developers.openai.com/api/reference/cli/resources/responses/methods/create).

## 4. Important Files

- `backend/app/agents/model_provider.py` — Converts the internal tool catalog into Responses
  API function definitions and safely parses function calls or structured answers.
- `backend/app/agents/model_orchestrator.py` — Owns model rounds, tool limits, validated tool
  execution, authoritative result selection, and UI actions.
- `backend/app/agents/factory.py` — Chooses model or deterministic execution from validated
  settings and exposes safe capabilities.
- `backend/app/services/assistant_service.py` — Supplies bounded conversation history,
  persists the result, and performs provider fallback.
- `backend/app/core/config.py` — Defines provider, model, timeout, output limit, and secret
  settings.
- `backend/tests/test_model_agent.py` — Tests the HTTP contract, structured parsing, safe
  errors, orchestration, and configuration gating.
- `frontend/app/(workspace)/assistant/page.tsx` — Shows the active provider mode honestly.

## 5. Important Code

### Provider adapter

The adapter sends only the user conversation, system constraints, and generated schemas for
allowlisted tools. It uses `store: false`, disables parallel calls, caps output, and never puts
the API key in the JSON body or application logs. If the HTTP or JSON contract fails, it raises
a stable internal error rather than exposing provider details.

### Orchestration loop

Each round either returns tool calls or a final structured answer. Tool calls are executed by
the same Phase 8 registry, and their validated result is returned as a `function_call_output`.
If the model keeps planning without finishing, the round limit stops it and invokes fallback.

### Grounded response mapping

The model may propose a response type, but the server reconciles it with the tools that
actually succeeded. A `compare_sites` result becomes a comparison response; deterministic
risk output becomes a risk explanation. Structured data and navigation actions come from the
tool result, not generated prose.

### Fallback

Provider timeouts, credential errors, malformed output, and planning-limit errors are logged
with stable codes. The same request ID is then processed by the local planner. The UI provider
label becomes `deterministic-fallback`, making the behavior visible without breaking the task.

## 6. Interview Questions and Model Answers

1. **What makes this an agent rather than a chatbot?** The model selects and sequences typed
   application tools, receives real results, and synthesizes a response over those results.
2. **Why not let it generate SQL?** Generated SQL bypasses domain validation, authorization,
   stable contracts, and safe limits. Tools preserve the service boundary.
3. **How are hallucinated arguments handled?** Every call is looked up in an allowlist and its
   arguments are validated with the tool's Pydantic model before execution.
4. **Why validate tool outputs too?** It prevents an application regression or unexpected
   handler value from becoming trusted model context.
5. **Why disable parallel calls?** Sequential calls make dependencies, auditing, limits, and
   failure behavior easier to understand for the MVP.
6. **Why use structured output?** The frontend needs a stable response type; JSON Schema plus
   Pydantic catches malformed provider output at the boundary.
7. **What happens on timeout?** The provider adapter emits a safe error code, the service logs
   it against the request ID, and the deterministic planner handles the request.
8. **Does the model calculate risk?** No. It must call `calculate_site_risk`, which invokes the
   authoritative deterministic formula.
9. **How is cost bounded?** Conversation history is capped, output tokens are capped, tool
   calls are capped, and model rounds are capped.
10. **How would you evaluate it?** Run a fixed dataset of intents and verify tool choice,
    argument validity, factual agreement, latency, cost, fallback rate, and response type.

## 7. Things I Must Understand

- [ ] Difference between model planning and application execution.
- [ ] Responses API input items, function-call items, and function-call outputs.
- [ ] Why provider objects live above tools rather than inside repositories.
- [ ] Pydantic validation on both sides of every tool.
- [ ] JSON Schema structured output and server-side validation.
- [ ] Tool-call, model-round, history, timeout, and output-token limits.
- [ ] Secret handling and why keys are backend-only.
- [ ] Deterministic fallback behavior and observability.
- [ ] Why hidden reasoning is neither stored nor displayed.

## 8. How To Test It

### Without a provider key

1. Leave `AERIALOPS_AGENT_PROVIDER=deterministic`.
2. Open `/assistant`; it should say **Local agent ready**.
3. Ask `Which sites are critical?` and inspect the visible tool audit.
4. Ask `Compare the two highest-risk sites.` and confirm two tool activities.

### With an OpenAI key

1. Set `AERIALOPS_AGENT_PROVIDER=openai`.
2. Set `OPENAI_API_KEY` in the backend environment; never in the frontend file.
3. Optionally set `AERIALOPS_AGENT_MODEL`.
4. Restart FastAPI and open `/assistant`; it should say **Model agent ready**.
5. Run the two queries above and confirm the provider label names the configured model.
6. Temporarily use an invalid key and confirm the request still succeeds through
   `deterministic-fallback` without exposing the provider error.

## 9. Current System Flow

```text
Next.js pages + assistant
        ↓ REST
FastAPI routes
        ↓
Services
        ├─ Sites / inspections / anomalies / uploads
        ├─ Deterministic risk engine
        └─ Assistant service
                ↓
        Agent factory
          ├─ Local planner
          └─ Responses API model planner
                    ↓ controlled calls
              ToolRegistry
                    ↓
              Domain services
                    ↓
              SQLAlchemy repositories
                    ↓
              PostgreSQL / local SQLite
```

## Next Phase

Phase 10 expands the assistant product experience: richer structured result components,
conversation restoration, explicit fallback/error presentation, site-context entry points,
and map handoff from assistant actions.
