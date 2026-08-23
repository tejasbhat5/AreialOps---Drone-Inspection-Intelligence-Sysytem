# Phase 1 — Project Setup

## What We Built

- A FastAPI application package with an application factory, validated settings, CORS, request-ID middleware, structured JSON logging, `/health`, and `/ready`.
- A Next.js App Router application using React, TypeScript, Tailwind CSS, ESLint, and Prettier.
- A typed server-side health client and visible backend-connectivity state on the landing page.
- Python and Node dependency definitions, component environment examples, `.gitignore`, and a README setup guide.
- Three backend health/readiness tests and repeatable frontend/backend quality commands.

## Why We Built It

Phase 1 proves the two deployable applications can run and communicate before database or feature complexity is introduced. Configuration, logging, and middleware are established early because every later route and service depends on them.

## Architecture

```text
Browser
  ↓ GET /
Next.js server component
  ↓ GET http://127.0.0.1:8000/health
FastAPI middleware
  ↓
Health route
  ↓
Typed JSON response
  ↓
BackendStatus React component
```

## Important Files

- `backend/app/main.py`: application construction and middleware/router wiring.
- `backend/app/core/config.py`: validated `AERIALOPS_` environment settings.
- `backend/app/core/middleware.py`: request IDs, status codes, and request-duration logs.
- `backend/app/api/routes/health.py`: liveness and readiness contracts.
- `frontend/lib/api.ts`: typed, timeout-bounded backend health request.
- `frontend/components/backend-status.tsx`: connected and unavailable UI states.
- `frontend/app/page.tsx`: Phase 1 landing page and server-side connectivity call.

## Important Code

### Application factory

`create_app()` constructs FastAPI and wires transport-level concerns. Keeping this separate from route logic makes the app testable and leaves `main.py` small as the project grows. If construction fails because configuration is invalid, startup stops immediately rather than serving a partially configured application.

### Request middleware

`RequestContextMiddleware` accepts or creates an `X-Request-ID`, measures request duration, returns the correlation ID, and emits one structured completion/failure event. If the downstream route raises, the middleware logs diagnostic context and re-raises so FastAPI's error handling remains authoritative.

### Typed health route

The health handler returns a Pydantic `HealthResponse`, so the generated OpenAPI contract and runtime output agree. Liveness deliberately avoids database work; readiness will acquire the database dependency check in Phase 2.

### Frontend API boundary

`getBackendHealth()` owns the base URL, three-second timeout, HTTP handling, and response-shape check. The page receives a discriminated union, forcing React to handle both connected and disconnected states.

### Server-side connectivity rendering

The App Router page awaits the health client on the server and passes the result to a reusable status component. This avoids exposing a server-only backend URL and gives the first response a complete operational state.

## Interview Questions and Model Answers

1. **Why use an application factory?** It centralizes construction while allowing tests or future deployments to create configured app instances without mixing business logic into the module entry point.
2. **What is the difference between liveness and readiness?** Liveness shows the process can respond; readiness shows it can serve useful traffic with required dependencies available.
3. **Why use Pydantic settings?** It validates environment configuration, provides typed defaults, and fails early for invalid values.
4. **Why add request IDs now?** They provide one correlation value across later routes, tools, provider calls, and background jobs.
5. **Why centralize frontend API calls?** It prevents every component from independently implementing URLs, timeouts, parsing, and inconsistent errors.
6. **Why does the health fetch use `cache: "no-store"`?** Operational status must reflect the current backend rather than a cached successful response.
7. **Why configure CORS if the initial fetch is server-side?** Future client-side forms and assistant calls may contact FastAPI directly, and the allowed origin should be explicit before those features arrive.
8. **Why use environment examples instead of committed `.env` files?** Examples document required configuration while real values and future secrets remain local.
9. **What happens when FastAPI is offline?** The three-second request aborts or rejects, the error is converted to a typed disconnected result, and the page renders a useful recovery message.
10. **Why pin frontend dependency versions?** The lockfile plus explicit versions makes installations repeatable and avoids silently accepting future breaking changes.

## Things I Must Understand

- [ ] Next.js App Router layouts and server components.
- [ ] FastAPI application construction and route inclusion.
- [ ] Pydantic response models and settings validation.
- [ ] CORS origin restrictions.
- [ ] Request correlation and structured logging.
- [ ] Environment-variable separation between server-only and `NEXT_PUBLIC_` values.
- [ ] TypeScript discriminated unions.
- [ ] Liveness versus readiness.
- [ ] The roles of linting, formatting, type checking, tests, and production builds.

## How To Test It

1. Start the backend from `backend`: `.venv\Scripts\python.exe -m uvicorn app.main:app --port 8000`.
2. Request `http://127.0.0.1:8000/health`; expect status 200 and the AerialOps API payload.
3. Request `/ready`; expect the database check to say `not_configured` until Phase 2.
4. Start the frontend from `frontend`: `npm run dev`.
5. Open `http://127.0.0.1:3000`; expect “FastAPI is online.”
6. Stop FastAPI and refresh; expect the unavailable state rather than a broken page.
7. Run Ruff, pytest, ESLint, TypeScript, Prettier, and the Next.js production build using the README commands.

## Current System Flow

```text
Next.js landing page
        ↓ typed no-cache HTTP request with timeout
FastAPI request-ID middleware
        ↓
GET /health
        ↓ Pydantic response
Next.js BackendStatus component
        ↓
Connected or unavailable UI state
```

Database, services, repositories, risk, agent tools, and LLM integration intentionally remain future-phase boundaries.

## Debugging Notes

- The default user `npm` launcher referenced a missing global npm module. Verification used the valid system npm executable.
- No system Python was registered. A bundled Python 3.12 runtime created the project-local `.venv`.
- Initial dependency downloads were blocked by sandbox networking. The package installs were rerun with explicit network approval.
- Prettier initially scanned `.next` build artifacts. `.prettierignore` now excludes generated output.
- Ruff found canonical-format differences and formatted the backend once; the format check now passes.
- Node 23.3 emits experimental and engine-range warnings because it is a non-LTS release between supported ranges. The project recommends Node 24 LTS; the application still linted, typed, and built successfully in the available environment.
