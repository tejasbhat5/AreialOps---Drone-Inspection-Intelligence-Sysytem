# Phase 7 — Deterministic and Explainable Risk

## What We Built

- A pure, versioned risk formula implemented independently of any LLM.
- Automatic recalculation after inspection creation, risk-relevant inspection changes, anomaly creation, severity changes, resolution, and reopening.
- Atomic persistence of a historical `RiskAssessment` and the site's denormalized current score/level.
- A complete factor snapshot containing inputs, weights, caps, recency bands, classification thresholds, and pre-cap totals.
- Current-risk, risk-history, and explicit-recalculation REST endpoints.
- A site-detail explanation showing the score equation, unresolved severity counts, inspection age, formula version, and assessment history.
- Legacy `seed-v1` handling that invites recalculation without discarding historical data.
- Map-marker synchronization when a site's risk score or level changes.

## Authoritative Formula

```text
severity_points = min(60, sum(unresolved anomaly weights))
critical_bonus = 15 when at least one unresolved CRITICAL anomaly exists
volume_points = min(15, unresolved_anomaly_count × 3)
recency_points = age band of latest COMPLETED inspection

score = min(100, severity_points + critical_bonus + volume_points + recency_points)
```

Severity weights:

```text
LOW=2, MODERATE=6, HIGH=12, CRITICAL=20
```

Inspection recency:

```text
0–30 days=0, 31–60=3, 61–90=6, over 90 or never completed=10
```

Classification:

```text
0–30 LOW, 31–60 MODERATE, 61–80 HIGH, 81–100 CRITICAL
```

## Why the LLM Does Not Score Risk

Operational prioritization must be reproducible, testable, auditable, and stable across repeated requests. An LLM can later translate the stored factor snapshot into natural language, but it cannot alter the authoritative score. The same persisted facts, formula version, and calculation time produce the same result.

## Transaction Flow

```text
Inspection or anomaly command
        ↓
Validate transition and update domain record
        ↓ flush within same SQLAlchemy session
RiskService reads persisted operational facts
        ↓
Calculate deterministic score + factor snapshot
        ↓
Insert immutable RiskAssessment history record
        +
Update Site.current_risk_score/current_risk_level
        ↓
Single commit
```

If scoring or persistence fails, the domain mutation and risk update roll back together. The UI cannot observe a newly resolved anomaly with an old authoritative risk snapshot.

## Factor Snapshot

Each `deterministic-v1` assessment stores:

- Unresolved anomaly count and counts for every severity.
- Severity weights, raw points, capped points, and cap.
- Critical bonus and configured bonus weight.
- Volume multiplier, points, and cap.
- Latest completed inspection timestamp.
- Days since that inspection and selected recency points.
- Every recency band and classification threshold.
- Score before and after the 100-point cap.
- Formula version.

This deliberately duplicates configuration into history. Changing constants in a future `deterministic-v2` implementation will not make old decisions impossible to reconstruct.

## API Contract

```text
GET  /api/sites/{site_id}/risk
GET  /api/sites/{site_id}/risk/history?limit=20
POST /api/sites/{site_id}/risk/recalculate
```

`GET /risk` returns `null` for a valid site that has never been assessed. Explicit recalculation establishes a baseline; a site with no completed inspection receives the documented 10 recency points.

## Important Files

- `backend/app/services/risk_service.py`: formula, classification, factor snapshot, and atomic site/assessment update.
- `backend/app/repositories/risk_repository.py`: authoritative anomaly/inspection inputs and assessment history.
- `backend/app/services/inspection_service.py`: inspection-triggered recalculation.
- `backend/app/services/anomaly_service.py`: anomaly-triggered recalculation.
- `backend/app/api/routes/sites.py`: current, history, and explicit recalculation routes.
- `backend/tests/test_risk_service.py`: deterministic boundaries, caps, critical bonus, and recency tests.
- `frontend/components/risk-explanation.tsx`: equation, factor evidence, legacy state, and history UI.
- `frontend/components/map/site-map.tsx`: marker identity includes risk state to prevent stale Leaflet projections.

## Verification Completed

- All 28 backend tests passed.
- Formula tests cover every classification and recency boundary.
- A four-critical-finding scenario verifies severity capping, critical bonus, volume, recency, and a reproducible score of 93.
- API tests verify a 24-point assessment from one HIGH and one MODERATE finding.
- Resolving the HIGH finding changes that test site from 24 to 9; reopening restores 24 and preserves all three assessments in history.
- A never-inspected site explicitly recalculates to 10/LOW.
- Ruff, ESLint, TypeScript, and the Next.js production build passed.
- Browser verification migrated Solar Farm Alpha from the legacy 92/CRITICAL seed assessment to a reproducible 68/HIGH assessment: 44 severity + 15 critical bonus + 9 volume + 0 recency.
- Browser verification confirmed both historical versions remain visible and the Leaflet marker updates to High with no console warnings or errors.

## Interview Questions

- Why should an LLM not own an authoritative operational-risk score?
- What makes this calculation deterministic and reproducible?
- Why store configuration inside each factor snapshot instead of only in code?
- Why maintain both assessment history and a denormalized current score on `Site`?
- How do you keep an anomaly transition and risk update atomic?
- Which changes should trigger recalculation, and which should not?
- How would you migrate from `deterministic-v1` to a new formula?
- How would you backfill risk for millions of sites without overloading the database?
- How would you prevent two concurrent recalculations from publishing stale snapshots?
- How would you evaluate whether the weights correlate with real maintenance outcomes?
- When would a rules engine or learned ranking model replace this formula?
- How can an LLM explain the result without becoming the source of truth?

## Next Phase

Phase 8 builds the controlled AI-agent foundation: typed application tools, validated tool inputs and outputs, safe lookup failures, bounded orchestration, tool audit logs, and direct tool tests before connecting any model provider.
