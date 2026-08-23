import Link from "next/link";
import { formatDate, titleCase } from "@/lib/format";
import type { Inspection } from "@/types/domain";

export function InspectionCard({ inspection }: { inspection: Inspection }) {
  return (
    <article className="record-card">
      <div>
        <span className="record-kicker">
          {formatDate(inspection.inspected_at, true)}
        </span>
        <h3>
          <Link href={`/inspections/${inspection.id}`}>
            {titleCase(inspection.status)} inspection
          </Link>
        </h3>
      </div>
      <span className="count-chip">
        {inspection.anomalies.length}{" "}
        {inspection.anomalies.length === 1 ? "anomaly" : "anomalies"}
      </span>
      {inspection.notes ? (
        <p>{inspection.notes}</p>
      ) : (
        <p className="muted">No field notes recorded.</p>
      )}
      <Link className="text-link" href={`/inspections/${inspection.id}`}>
        Open inspection →
      </Link>
    </article>
  );
}
