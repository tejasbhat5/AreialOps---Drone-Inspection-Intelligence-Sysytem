# Phase 4 — Frontend Foundation and Operational Views

## What We Built

- A responsive Next.js App Router workspace shell with a persistent sidebar and action header.
- Typed frontend domain contracts and a single server-only FastAPI client with timeouts and safe API errors.
- A live command-center dashboard with six operational metrics, recent inspections, anomaly severity distribution, and highest-risk sites.
- A searchable, filterable, sortable, paginated site registry.
- A validated site-registration form implemented with a React Server Action.
- Site detail pages with risk posture, coordinates, counts, inspection history, and anomaly history.
- Reusable metric, site, inspection, anomaly, risk badge, loading, empty, error, and not-found components.
- Request-time rendering for operational pages so production builds do not depend on a running API.

## Why We Built It

This phase establishes the browser-facing application boundary without duplicating backend business logic. Server Components read directly from the trusted REST API, while the small interactive form boundary uses a Server Action. The result is a real vertical slice: database records flow through repositories, services, HTTP schemas, the typed frontend client, and reusable UI components.

## Architecture

```text
Browser navigation
      ↓
Next.js Server Component
      ↓ typed, server-only API client
FastAPI route → service → repository → database
      ↓ JSON response
Next.js renders accessible HTML
      ↓
Small Client Components only where interaction is required
```

Site creation uses the reverse path:

```text
Client form → React Server Action → validation → FastAPI POST
            → revalidate dashboard/sites → redirect to site detail
```

## Important Files

- `frontend/app/(workspace)/layout.tsx`: shared shell and request-time rendering policy.
- `frontend/app/(workspace)/dashboard/page.tsx`: operational summary composition.
- `frontend/app/(workspace)/sites/page.tsx`: server-driven filtering and pagination.
- `frontend/app/(workspace)/sites/actions.ts`: validated site-creation mutation.
- `frontend/app/(workspace)/sites/[id]/page.tsx`: site-level operational record.
- `frontend/lib/api.ts`: server-only typed HTTP boundary.
- `frontend/types/domain.ts`: frontend representation of public API schemas.
- `frontend/components/*`: reusable layout, data card, badge, form, and state components.
- `frontend/app/globals.css`: responsive visual system and component styling.

## Important Decisions

### Server Components for reads

The dashboard and site pages render on the server. API credentials and internal URLs remain server-side, the client receives useful HTML, and no loading-effect boilerplate is needed. Only navigation highlighting, error retry, and form submission need Client Components.

### Request-time dynamic rendering

Operational data changes independently of deployments. The workspace layout uses `dynamic = "force-dynamic"`, and API requests use `cache: "no-store"`. This also prevents a production build from failing merely because FastAPI is not running during compilation.

### URL-owned filters

Site filters are ordinary query parameters. URLs are shareable, browser back/forward works, refresh preserves state, and the server remains the source of truth for filtering, sorting, counts, and pagination.

### Mutations through a Server Action

The create form performs quick field validation in the Server Action, then sends the authoritative request to FastAPI. Expected API failures become form state. Successful creation revalidates affected routes and redirects to the new canonical record.

### No invented operational data

Every metric, site, inspection, anomaly, and risk value shown in the UI comes from Phase 3 endpoints. Empty states explain the absence of records. The coordinate panel explicitly defers map rendering to Phase 5 rather than presenting a fake map.

## Interview Questions and Model Answers

1. **Why use Server Components for these pages?** They can fetch close to the data boundary, keep internal configuration off the browser, reduce client JavaScript, and return meaningful HTML on first response.
2. **When is a Client Component necessary?** When code needs browser state, event handlers, effects, or client-only hooks such as `usePathname` and `useActionState`.
3. **Why keep the API client server-only?** It prevents accidental import into browser bundles and centralizes base URL, timeout, error, and response behavior.
4. **Why use `cache: "no-store"`?** The current pages are operational views where freshness is more important than static reuse. A later phase could introduce deliberate tagged caching for slower-changing resources.
5. **Why force dynamic rendering?** These pages depend on a live API per request. Build-time prerendering would couple frontend compilation to backend availability and could freeze stale operational values into output.
6. **Why put filters in the URL?** URL state is shareable, bookmarkable, refresh-safe, and compatible with server rendering and native browser navigation.
7. **Why not filter the downloaded site array in React?** Server filtering works across the entire dataset, gives correct totals and pagination, avoids large downloads, and uses the database efficiently.
8. **What does a Server Action add?** It provides a server mutation entry point that integrates with React form state, progressive enhancement, revalidation, and redirects without exposing the internal API address.
9. **Where is authoritative validation?** FastAPI/Pydantic and the database remain authoritative. The Server Action adds fast, user-friendly validation but does not replace backend constraints.
10. **Why redirect after site creation?** A successful POST creates a canonical resource. Redirecting to its detail page prevents accidental resubmission and gives immediate confirmation through real persisted data.
11. **How are expected failures handled?** The API client throws a typed `ApiError`; the action converts expected mutation errors into form state, while route error boundaries handle read failures and allow retry.
12. **How does the UI avoid hydration problems?** Most content is server-rendered, Client Component boundaries are small, and browser-dependent values are not used to generate server markup.
13. **Why await `params` and `searchParams`?** In the installed Next.js version these props are promises. Awaiting them follows the current App Router contract and avoids deprecated synchronous access.
14. **How is accessibility considered?** Semantic navigation and sections, visible labels, focus styles, `aria-invalid`, linked field errors, busy states, alert messages, and reduced-motion support are included.
15. **Why use reusable cards rather than page-specific markup?** The same domain concepts recur across dashboard, list, and detail views. Shared components keep risk semantics and formatting consistent while pages own composition.

## Things I Must Understand

- [ ] Server Component versus Client Component boundaries.
- [ ] Request-time rendering, caching, and `cache: "no-store"`.
- [ ] Current asynchronous `params` and `searchParams` contracts.
- [ ] URL-driven filters and server-side pagination.
- [ ] Server Actions, `useActionState`, revalidation, and redirects.
- [ ] Expected mutation errors versus route error boundaries.
- [ ] Why frontend types mirror public schemas rather than database models.
- [ ] Accessible form validation and empty/loading/error states.
- [ ] Responsive layout choices and reduced-motion support.
- [ ] Why geospatial rendering remains a separate Phase 5 concern.

## How To Test It

1. Start the migrated and seeded backend on port 8000.
2. Start Next.js on port 3000 and open `/dashboard`.
3. Verify all six metrics match `/api/dashboard/summary`.
4. Open `/sites`; search by a seeded site name or location.
5. Apply type, status, risk, and sort filters; verify they persist in the URL.
6. Open a site card and compare counts/history with its nested API endpoints.
7. Submit invalid coordinates in the registration form and verify field errors.
8. Register a valid site; verify redirect, persistence, and updated site/dashboard totals.
9. Stop FastAPI, refresh an operational route, and verify the error boundary offers retry.
10. Test the shell and forms at desktop, tablet, and narrow mobile widths.
11. Run `npm run format:check`, `npm run typecheck`, `npm run lint`, and `npm run build`.

## Verification Completed

- Prettier, TypeScript, ESLint, and the Next.js production build passed.
- The production route table correctly marks `/dashboard`, `/sites`, and `/sites/[id]` as dynamic.
- A migrated and seeded SQLite smoke environment returned HTTP 200 for all three pages.
- Rendered dashboard text, seeded site data, and a real site detail name were confirmed end-to-end.
- The temporary smoke-test database and processes were removed after verification.

## Next Phase

Phase 5 adds geospatial visualization: Leaflet map views, risk-based site markers, shared map filtering, coordinate interaction, and spatially aware site navigation. Inspection and file uploads remain Phase 6 concerns.
