"use client";

import { useActionState } from "react";
import { createInspectionAction } from "@/app/(workspace)/inspections/actions";
import { titleCase } from "@/lib/format";
import type { Site } from "@/types/domain";

export function CreateInspectionForm({ sites }: { sites: Site[] }) {
  const [state, action, pending] = useActionState(createInspectionAction, {
    message: "",
  });
  return (
    <form action={action} className="site-form inspection-form">
      <div className="form-grid">
        <label>
          Site
          <select name="site_id" required defaultValue="">
            <option value="" disabled>Select an asset</option>
            {sites.map((site) => (
              <option value={site.id} key={site.id}>{site.name}</option>
            ))}
          </select>
        </label>
        <label>
          Inspection date and time
          <input name="inspected_at" type="datetime-local" required />
        </label>
        <label>
          Workflow status
          <select name="status" defaultValue="COMPLETED">
            {["SCHEDULED", "IN_PROGRESS", "COMPLETED", "CANCELLED"].map(
              (status) => <option value={status} key={status}>{titleCase(status)}</option>,
            )}
          </select>
        </label>
        <label>
          Field notes
          <textarea name="notes" placeholder="Thermal and visual inspection summary" />
        </label>
      </div>
      <div className="form-divider">
        <span className="eyebrow">Optional initial finding</span>
      </div>
      <div className="form-grid">
        <label>
          Anomaly title
          <input name="anomaly_title" placeholder="Panel hotspot" />
        </label>
        <label>
          Severity
          <select name="anomaly_severity" defaultValue="MODERATE">
            {["LOW", "MODERATE", "HIGH", "CRITICAL"].map((level) => (
              <option value={level} key={level}>{titleCase(level)}</option>
            ))}
          </select>
        </label>
        <label className="full-field">
          Finding description
          <textarea name="anomaly_description" placeholder="Location and observable evidence" />
        </label>
      </div>
      {state.message ? <p className="form-message" role="alert">{state.message}</p> : null}
      <button className="button" disabled={pending}>
        {pending ? "Recording…" : "Record inspection"}
      </button>
    </form>
  );
}
