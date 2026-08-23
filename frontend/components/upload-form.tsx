"use client";

import { useActionState } from "react";
import {
  uploadImagesAction,
  uploadReportAction,
} from "@/app/(workspace)/inspections/actions";

export function ImageUploadForm({ inspectionId }: { inspectionId: string }) {
  const [state, action, pending] = useActionState(uploadImagesAction, { message: "" });
  return (
    <form action={action} className="upload-form">
      <input type="hidden" name="inspection_id" value={inspectionId} />
      <label className="file-drop">
        <strong>Drone or thermal images</strong>
        <span>JPEG, PNG or TIFF · up to 20 MB each · maximum 10</span>
        <input name="files" type="file" accept="image/jpeg,image/png,image/tiff" multiple required />
      </label>
      {state.message ? <p className={state.success ? "form-success" : "form-message"}>{state.message}</p> : null}
      <button className="button button-secondary" disabled={pending}>{pending ? "Uploading…" : "Upload images"}</button>
    </form>
  );
}

export function ReportUploadForm({ inspectionId }: { inspectionId: string }) {
  const [state, action, pending] = useActionState(uploadReportAction, { message: "" });
  return (
    <form action={action} className="upload-form">
      <input type="hidden" name="inspection_id" value={inspectionId} />
      <label className="file-drop">
        <strong>Inspection report</strong>
        <span>PDF only · up to 25 MB · one report per inspection</span>
        <input name="file" type="file" accept="application/pdf" required />
      </label>
      {state.message ? <p className={state.success ? "form-success" : "form-message"}>{state.message}</p> : null}
      <button className="button button-secondary" disabled={pending}>{pending ? "Uploading…" : "Upload report"}</button>
    </form>
  );
}
