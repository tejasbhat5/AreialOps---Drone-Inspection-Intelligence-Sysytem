# Phase 6 — Inspection Ingestion and Management

## What We Built

- A complete inspection ledger and inspection-detail workflow in Next.js.
- Inspection creation with site, timezone-normalized date, workflow status, field notes, and one optional initial anomaly.
- Multipart endpoints for multiple inspection images and one inspection report.
- JPEG, PNG, and TIFF image validation using declared MIME type and file signatures.
- PDF report validation using both declared MIME type and the `%PDF-` signature.
- Per-file limits of 20 MB for images and 25 MB for reports, with at most 10 images per request.
- Opaque UUID storage keys; client filenames are retained only as display metadata.
- Local files stored outside executable and public web directories.
- Durable `InspectionImage`, `InspectionReport`, and `ProcessingJob` records.
- Pending image-analysis and report-ingestion jobs for the next processing phase.
- Evidence, finding, report-state, and job-state views on every inspection page.

## Why We Built It

An aerial-intelligence system needs a trustworthy path from field evidence to application data. Phase 6 establishes that boundary. It does not infer file type from a filename, expose raw storage paths, or pretend that a synchronous HTTP request can perform expensive AI processing.

The upload request validates and stores evidence, creates metadata, enqueues a durable logical job, and returns quickly. A later processing phase can replace the pending-job placeholder with a real worker without changing the user-facing resource model.

## Architecture

```text
Operator records inspection
        ↓
Next.js Server Action → FastAPI JSON endpoint
        ↓
InspectionService → repository → database transaction
        ↓
Canonical /inspections/{id}
        ↓
Operator selects evidence
        ↓ multipart/form-data
Next.js upload action → FastAPI upload endpoint
        ↓
UploadService
  ├─ filename policy
  ├─ MIME allowlist
  ├─ magic-byte verification
  ├─ byte/count limits
  └─ UUID storage key
        ↓
Private local storage + metadata + PENDING ProcessingJob
```

## Security Boundaries

1. The original filename is untrusted display metadata and never becomes a filesystem path.
2. Filenames containing separators or traversal sequences are rejected.
3. The backend determines the storage extension from verified content, not the supplied name.
4. Declared MIME type must agree with the detected signature.
5. Files are streamed in 1 MB chunks and stopped as soon as the configured limit is exceeded.
6. Failed database operations remove newly stored files, avoiding orphaned evidence.
7. The storage directory is ignored by Git and is outside Next.js `public` and application code.
8. A unique database constraint enforces one report per inspection.
9. Error responses contain stable safe codes and do not expose storage keys or local paths.

## Important Files

- `backend/app/services/upload_service.py`: validation, streaming storage, metadata, jobs, and cleanup.
- `backend/app/repositories/upload_repository.py`: upload and processing-job persistence queries.
- `backend/app/api/routes/inspections.py`: multipart and evidence-query endpoints.
- `backend/app/core/config.py`: storage path and bounded upload configuration.
- `backend/app/schemas/uploads.py`: public evidence response contracts.
- `frontend/app/(workspace)/inspections/page.tsx`: inspection ledger and creation composition.
- `frontend/app/(workspace)/inspections/[id]/page.tsx`: evidence and processing detail.
- `frontend/app/(workspace)/inspections/actions.ts`: validated server actions and cache refresh.
- `frontend/components/create-inspection-form.tsx`: field-record form.
- `frontend/components/upload-form.tsx`: image and report selectors.

## API Contract

```text
GET, POST  /api/inspections
GET, PATCH /api/inspections/{inspection_id}
GET, POST  /api/inspections/{inspection_id}/images
GET, POST  /api/inspections/{inspection_id}/report
GET        /api/inspections/{inspection_id}/jobs
```

Image upload responses contain created image metadata and one pending image-analysis job per image. Report upload responses contain the report and its pending ingestion job.

## Trade-offs and Future Scale

Local storage is intentionally sufficient for the resume MVP. In production, clients should upload directly to private object storage using short-lived signed URLs. The application would then validate object metadata, persist the evidence record, and publish a durable queue message. That avoids sending large files through Next.js and FastAPI processes while preserving the same domain model.

The current processing jobs are durable database records but are not yet consumed. A later phase will add worker leasing, idempotency keys, retries, attempt limits, heartbeats, and safe failure summaries.

## How To Test It

1. Open `/inspections` and confirm seeded inspections appear in date order.
2. Create an inspection with notes and an optional anomaly.
3. Confirm navigation to the canonical detail page.
4. Upload a genuine JPEG, PNG, or TIFF and verify image metadata and a pending job appear.
5. Upload a PDF report and verify its pending ingestion state.
6. Attempt a second report and verify HTTP 409 with `inspection_report_exists`.
7. Rename arbitrary text to `.png`; verify `invalid_image_type`.
8. Submit a file above its limit; verify HTTP 413 and that no file/metadata remains.
9. Verify uploaded files use opaque UUID names under private storage.
10. Run Ruff, Pytest, ESLint, TypeScript, and a production Next.js build.

## Verification Completed

- Ruff passed after import and formatting checks.
- All 25 backend tests passed.
- Upload tests verified image/report creation, pending jobs, duplicate-report conflict, and spoofed-content rejection.
- ESLint and the Next.js production build passed, including TypeScript compilation.
- Browser verification created a completed Solar Farm Alpha inspection with one high-severity finding and reached its canonical detail page.
- The detail page rendered image/report controls, evidence counts, findings, and job telemetry with no browser warnings or errors.

## Interview Questions

- Why is a file extension insufficient for validating an upload?
- Why retain the original filename but generate a different storage key?
- How do you keep filesystem and database writes consistent without a distributed transaction?
- Why create a processing job instead of analyzing images during the upload request?
- What makes a background job idempotent?
- How would direct-to-object-storage uploads change this design?
- How would you scan uploads for malware and decompression bombs?
- How would you support resumable multi-gigabyte drone datasets?
- How would you isolate one enterprise tenant's evidence from another?
- What metrics and traces would you add around ingestion latency and failure rates?

## Next Phase

Phase 7 implements the deterministic risk engine: versioned factors, inspection-recency weighting, anomaly-severity scoring, explainable factor snapshots, atomic recalculation, and UI explanations for every site risk score.
