"use client";

import { useActionState } from "react";
import {
  createSiteAction,
  type CreateSiteState,
} from "@/app/(workspace)/sites/actions";
import { titleCase } from "@/lib/format";
import type { SiteStatus, SiteType } from "@/types/domain";

const initialState: CreateSiteState = { message: "" };
const siteTypes: SiteType[] = [
  "SOLAR_FARM",
  "WIND_FARM",
  "RAIL",
  "BRIDGE",
  "MINE",
  "TRANSMISSION",
  "INDUSTRIAL",
  "CONSTRUCTION",
  "OTHER",
];
const statuses: SiteStatus[] = ["ACTIVE", "MAINTENANCE", "INACTIVE"];

export function CreateSiteForm() {
  const [state, action, pending] = useActionState(
    createSiteAction,
    initialState,
  );
  return (
    <form action={action} className="site-form">
      <div className="form-grid">
        <Field
          label="Site name"
          name="name"
          placeholder="North Ridge Solar"
          error={state.errors?.name}
        />
        <Field
          label="Location"
          name="location"
          placeholder="Pune, Maharashtra"
          error={state.errors?.location}
        />
        <label>
          Asset type
          <select name="site_type" defaultValue="SOLAR_FARM">
            {siteTypes.map((type) => (
              <option key={type} value={type}>
                {titleCase(type)}
              </option>
            ))}
          </select>
        </label>
        <label>
          Operating status
          <select name="status" defaultValue="ACTIVE">
            {statuses.map((status) => (
              <option key={status} value={status}>
                {titleCase(status)}
              </option>
            ))}
          </select>
        </label>
        <Field
          label="Latitude"
          name="latitude"
          type="number"
          step="0.000001"
          placeholder="18.520430"
          error={state.errors?.latitude}
        />
        <Field
          label="Longitude"
          name="longitude"
          type="number"
          step="0.000001"
          placeholder="73.856744"
          error={state.errors?.longitude}
        />
      </div>
      {state.message ? (
        <p className="form-message" role="alert">
          {state.message}
        </p>
      ) : null}
      <button className="button" disabled={pending}>
        {pending ? "Registering…" : "Register site"}
      </button>
    </form>
  );
}

function Field({
  label,
  name,
  error,
  ...input
}: {
  label: string;
  name: string;
  error?: string;
} & React.InputHTMLAttributes<HTMLInputElement>) {
  return (
    <label>
      {label}
      <input
        name={name}
        aria-invalid={Boolean(error)}
        aria-describedby={error ? `${name}-error` : undefined}
        {...input}
      />
      {error ? (
        <small className="field-error" id={`${name}-error`}>
          {error}
        </small>
      ) : null}
    </label>
  );
}
