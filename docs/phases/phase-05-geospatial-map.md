# Phase 5 — Geospatial Map

## What We Built

- Leaflet 1.9.4 and React-Leaflet 5 integrated into the Next.js application.
- A client-only map boundary that prevents browser-dependent Leaflet code from executing during server rendering.
- A filtered site-registry map using the same URL filters as the site cards.
- Risk-based custom markers for low, moderate, high, and critical sites.
- Automatic viewport fitting for one or many coordinates.
- Marker popups and a selected-site panel with name, location, asset type, status, coordinates, risk, and detail navigation.
- A focused map on every site detail page.
- Configurable raster tile URL, visible OpenStreetMap attribution, and no tile prefetching.
- Coordinate validation at the frontend map boundary, even though backend and database validation already protect stored data.

## Why We Built It

Infrastructure risk is inherently spatial. A list answers “what?”, while a map also answers “where?” and reveals regional concentration. The map uses the same canonical site records and filters as the registry, so it is another projection of application data rather than a separate source of truth.

Uploads were not added here because the original plan assigns reports and inspection images to Phase 6. Keeping that boundary prevents geospatial rendering, multipart validation, storage, and background ingestion from becoming one oversized phase.

## Architecture

```text
Site filter form
     ↓ query parameters
Next.js /sites Server Component
     ↓ typed HTTP request
FastAPI GET /api/sites
     ↓
SiteService → SiteRepository → PostgreSQL
     ↓ validated JSON (latitude/longitude as decimal values)
Next.js serializes matching Site records
     ↓ Client Component boundary
React-Leaflet → Leaflet map
     ├─ OpenStreetMap raster tiles
     ├─ risk marker per Site
     └─ marker selection → canonical /sites/{id}
```

## Coordinate Flow End to End

```text
1. User registers latitude and longitude
   ↓
2. Server Action performs friendly numeric/range checks
   ↓
3. FastAPI validates Decimal latitude [-90, 90]
   and longitude [-180, 180]
   ↓
4. PostgreSQL stores fixed-precision NUMERIC values
   ↓
5. Repository selects the Site record
   ↓
6. Pydantic serializes coordinates in the REST response
   ↓
7. Next.js typed API client receives string | number
   ↓
8. toSiteMapPoint converts to finite JavaScript numbers
   and rejects invalid ranges defensively
   ↓
9. Leaflet receives [latitude, longitude]
   ↓
10. Marker renders and viewport fits valid points
```

The order is always latitude then longitude. GeoJSON commonly uses longitude then latitude, so a future GeoJSON integration must convert deliberately rather than reusing the Leaflet tuple blindly.

## Important Files

- `frontend/components/map/site-map.tsx`: Leaflet map, markers, popups, selection state, and viewport synchronization.
- `frontend/components/map/site-map-loader.tsx`: client-only dynamic import and loading state.
- `frontend/lib/map.ts`: decimal conversion and coordinate boundary checks.
- `frontend/lib/api.ts`: paged retrieval of up to 500 matching sites for the map.
- `frontend/app/(workspace)/sites/page.tsx`: shared server filters and registry map composition.
- `frontend/app/(workspace)/sites/[id]/page.tsx`: single-site geospatial view.
- `frontend/app/layout.tsx`: global Leaflet stylesheet import.
- `frontend/app/globals.css`: map layout, markers, Leaflet theme, responsiveness, and accessible contrast.
- `frontend/.env.example`: configurable public tile URL.

## Important Code

### 1. Client-only Leaflet boundary

`site-map-loader.tsx` is a small Client Component that dynamically imports the real map with server rendering disabled. Leaflet expects browser objects such as `window` and `document`; importing it in a normal Server Component could fail during builds or server rendering. The loading surface preserves layout while the map bundle loads.

### 2. Defensive coordinate conversion

`toSiteMapPoint()` converts API decimals to JavaScript numbers, rejects non-finite values, and repeats legal latitude/longitude range checks. Backend validation is authoritative, but this boundary prevents one malformed legacy record from crashing the entire map.

### 3. Shared filter data flow

The `/sites` page passes the same `SiteFilters` to both the paginated card query and `getMapSites()`. Map retrieval follows API pagination in batches of 100 and stops at 500 markers. If more records match, the UI explicitly reports truncation and asks the operator to narrow the filters.

### 4. Automatic viewport synchronization

React-Leaflet’s `MapContainer` creation options are immutable after initialization. The `FitToSites` child uses `useMap()` to access the actual Leaflet instance: one site gets a focused `setView`, while multiple sites use `fitBounds` with padding and a maximum zoom.

### 5. Safe custom risk markers

Leaflet `divIcon` avoids default marker image-path problems in bundled applications. Only an allowlisted risk enum becomes a CSS class; no site-controlled text is interpolated into marker HTML. Actual site content is rendered by React inside the popup and selected-site panel.

## Map Filtering

Filters remain server-owned query parameters:

- `query`: site name or location
- `site_type`: asset category
- `status`: operating status
- `risk_level`: stored risk band
- `sort`: card order; it does not change spatial meaning

Submitting filters creates a shareable URL. FastAPI and the database filter before data reaches the browser. Both the map and the card list therefore describe the same result set, while pagination affects only the cards.

## Tile Provider Decision

Local development defaults to standard OpenStreetMap raster tiles. Attribution stays visible, requests are made only for the human-visible viewport, and no offline/prefetch capability exists. The URL is configurable because the public OSM service is best-effort and is not a production SLA. A production deployment should select a provider or self-hosted tile service appropriate to expected traffic and terms.

## Interview Questions and Model Answers

1. **Why is Leaflet loaded only in the browser?** Leaflet depends on DOM and browser globals. A client-only dynamic boundary prevents those imports from executing during Next.js server rendering or builds.
2. **Why use React-Leaflet instead of manipulating Leaflet directly?** It provides React lifecycle and context integration while still exposing the underlying map through hooks for imperative operations such as fitting bounds.
3. **Why does `FitToSites` exist?** `MapContainer` initialization props do not update the existing map instance. The child uses `useMap()` and synchronizes the viewport when coordinate props change.
4. **What coordinate order does Leaflet use?** `[latitude, longitude]`. GeoJSON positions use `[longitude, latitude]`, so conversions must be explicit.
5. **Why validate coordinates again on the frontend?** It is a defensive rendering boundary. Backend validation protects new writes, but malformed legacy or integration data should not crash the full map.
6. **How are map filters implemented?** Query parameters are parsed by the Server Component and sent to the existing FastAPI filter endpoint. The database filters records before Next.js passes them to Leaflet.
7. **Why not filter all sites only in React?** Client-only filtering requires downloading the whole dataset, can disagree with pagination totals, and duplicates backend rules. Server filtering remains authoritative and scalable.
8. **How do marker colors remain trustworthy?** They come from the stored deterministic risk level, not a frontend calculation. Phase 7 will own recalculation; the map only presents the current backend value.
9. **Why use a custom `divIcon`?** It supports risk styling without bundler-sensitive default marker image assets. The generated HTML contains only an enum-derived CSS class, not user text.
10. **What happens with thousands of sites?** The current operational cap is 500 and truncation is disclosed. At larger scale, add server bounding-box queries, marker clustering or vector tiles, and possibly PostGIS after measuring need.
11. **Why is PostGIS not required yet?** Current behavior retrieves known point coordinates and renders them. Advanced server-side radius, polygon, nearest-neighbor, or spatial-index queries would justify PostGIS.
12. **What tile-service concerns matter in production?** Attribution, provider terms, traffic limits, caching policy, privacy, availability, and cost. The map must not assume a community tile server has a commercial SLA.

## Things I Must Understand

- [ ] Latitude versus longitude and valid numeric ranges.
- [ ] Leaflet tuple order versus GeoJSON coordinate order.
- [ ] Server Components versus browser-only Client Components.
- [ ] Dynamic imports with server rendering disabled.
- [ ] React-Leaflet `MapContainer`, context, `useMap`, markers, and popups.
- [ ] Immutable initialization options versus imperative map updates.
- [ ] Database/server filtering versus client presentation.
- [ ] Bounds fitting for one point and multiple points.
- [ ] Risk marker CSS derived from an allowlisted enum.
- [ ] Tile attribution, usage policy, caching, and production-provider selection.
- [ ] When marker clustering, bounding-box APIs, or PostGIS become justified.

## How To Test It

1. Migrate and seed the database, then start FastAPI on port 8000.
2. Start Next.js on port 3000 and open `/sites`.
3. Confirm all seeded sites appear as risk-colored markers and in the registry.
4. Compare the marker colors with each site’s risk badge.
5. Click a marker; verify the popup and selected-site panel show the correct record.
6. Follow “Open site record”; verify it opens the matching canonical site page.
7. Apply a critical-risk filter; verify only critical markers and cards remain and the filter is present in the URL.
8. Combine name/location, type, status, and risk filters; verify the map and registry stay aligned.
9. Open a site detail page and verify its focused marker and printed coordinates match the API response.
10. Test zoom, pan, keyboard marker focus, popup close, and narrow-screen layout.
11. Run formatting, TypeScript, ESLint, and the production build.

## Current System Flow

```text
Next.js operational UI
  ├─ Dashboard Server Component
  ├─ Site Registry Server Component
  │    ├─ URL filters
  │    ├─ paginated Site cards
  │    └─ client-only Leaflet map
  │          ├─ risk markers
  │          ├─ OpenStreetMap tiles
  │          └─ selected Site navigation
  └─ Site Detail Server Component
       ├─ operational snapshot
       ├─ focused Leaflet map
       ├─ inspections
       └─ anomalies
          ↓ typed REST calls
FastAPI routes
          ↓
Application services
          ↓
Repositories
          ↓
SQLAlchemy → PostgreSQL
```

## Verification Completed

- Package audit reported zero known vulnerabilities after adding Leaflet dependencies.
- Prettier, TypeScript, ESLint, and the Next.js production build passed.
- Three direct assertions covered decimal conversion, out-of-range latitude, and nonnumeric input.
- A migrated and seeded SQLite environment provided 10 mapped sites.
- The critical-risk API filter returned two records; the filtered map page and matching site detail returned HTTP 200 with canonical data.
- The production route table keeps operational routes request-time dynamic.

## Debugging Notes

### Registry access was blocked in the sandbox

- **What failed:** npm could not connect to the registry and returned `EACCES`.
- **Why:** network access was restricted in the default execution sandbox.
- **Diagnosis:** the error named the registry URL, socket operation, and denied connection rather than a dependency-resolution conflict.
- **Change:** reran the exact bounded install with approved network access.
- **Why it works:** npm could reach the registry, installed the declared packages, updated the lockfile, and completed an audit.

### React lint rejected a state update inside an effect

- **What failed:** `react-hooks/set-state-in-effect` flagged synchronous selection repair.
- **Why:** the effect created an avoidable follow-up render.
- **Diagnosis:** the render already chose the first valid point when the stored selection was absent.
- **Change:** removed the redundant state-repair effect and retained the render-time fallback.
- **Why it works:** selection remains valid without an extra render cycle.

### A previous development process still owned port 3000

- **What failed:** a second `next dev` attempted port 3001, then detected the same workspace already running on 3000.
- **Why:** the Phase 4 Next.js child process survived its terminal interrupt.
- **Diagnosis:** Next reported the PID, project directory, and active local URL.
- **Change:** reused the verified same-workspace server and its hot reload for preview, then stopped it during cleanup.
- **Why it works:** only one compiler owns the `.next` development state, avoiding lock and port conflicts.

### The map remained on its loading state at `127.0.0.1`

- **What failed:** the server-rendered page appeared, but the dynamically imported Leaflet map never replaced “Loading geospatial view…”.
- **Why:** Next.js started with `localhost` as its trusted development origin while the in-app browser used `127.0.0.1`. Next blocked the map’s dev-only JavaScript chunks as cross-origin requests.
- **Diagnosis:** browser DOM inspection showed no `.leaflet-container` and no console exception, while the Next.js terminal explicitly reported blocked `/_next/static/chunks` and HMR requests from `127.0.0.1`.
- **Change:** added `allowedDevOrigins: ["127.0.0.1"]` to `frontend/next.config.ts` and reloaded after the development server applied the configuration.
- **Why it works:** the local browser origin is now explicitly trusted for development assets. Browser verification found one Leaflet container, 10 registry markers, a working popup, and selected-site changes after marker clicks.

## Next Phase

Phase 6 adds inspection creation and management, report and image uploads, strict multipart validation, opaque server-generated storage keys, durable metadata, and safe local/object-storage boundaries.
