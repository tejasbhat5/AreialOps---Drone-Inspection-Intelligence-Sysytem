import type { Metadata } from "next";
import { CreateInspectionForm } from "@/components/create-inspection-form";
import { InspectionCard } from "@/components/inspection-card";
import { EmptyState } from "@/components/ui/states";
import { getInspections, getSites } from "@/lib/api";

export const metadata: Metadata = { title: "Inspections | AerialOps" };

export default async function InspectionsPage() {
  const [inspections, sites] = await Promise.all([getInspections(), getSites({}, 100)]);
  return (
    <div className="page">
      <section className="hero-row">
        <div className="page-heading">
          <span className="eyebrow">Field intelligence</span>
          <h1>From site visit to actionable evidence.</h1>
          <p>Record inspections, attach field findings, and securely ingest drone imagery and reports.</p>
        </div>
        <div className="hero-index">
          <span>Inspection records</span>
          <strong>{inspections.total}</strong>
          <small>Across {sites.total} registered assets</small>
        </div>
      </section>
      <section className="section-block">
        <div className="section-heading">
          <div><span className="eyebrow">Recent activity</span><h2>Inspection ledger</h2></div>
        </div>
        {inspections.items.length ? (
          <div className="record-list inspection-ledger">
            {inspections.items.map((inspection) => <InspectionCard inspection={inspection} key={inspection.id} />)}
          </div>
        ) : <EmptyState title="No inspections recorded" message="Create the first field record below." />}
      </section>
      <section className="section-block form-section" id="new-inspection">
        <div className="section-heading">
          <div><span className="eyebrow">New field record</span><h2>Record an inspection</h2><p>Start with verified metadata; imagery and a report can be attached next.</p></div>
        </div>
        {sites.items.length ? <CreateInspectionForm sites={sites.items} /> : <EmptyState title="A site is required" message="Register an asset before recording an inspection." action={{ href: "/sites#new-site", label: "Register site" }} />}
      </section>
    </div>
  );
}
