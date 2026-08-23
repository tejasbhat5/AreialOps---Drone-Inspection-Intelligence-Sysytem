import type { Metadata } from "next";
import Link from "next/link";
import { EmptyState } from "@/components/ui/states";
import { getReports } from "@/lib/api";
import { formatDate, titleCase } from "@/lib/format";
import { ReportSearch } from "./report-search";

export const metadata: Metadata = { title: "Reports | AerialOps" };

export default async function ReportsPage() {
  const reports = await getReports();
  const indexed = reports.filter((report) => report.ingestion_status === "COMPLETED").length;
  const passages = reports.reduce((total, report) => total + report.chunk_count, 0);

  return (
    <div className="page">
      <section className="hero-row">
        <div className="page-heading">
          <span className="eyebrow">Inspection intelligence</span>
          <h1>Reports with traceable answers.</h1>
          <p>
            Search locally indexed report passages and follow every answer back to its source
            inspection.
          </p>
        </div>
        <div className="hero-index">
          <span>Retrieval readiness</span>
          <strong>{indexed}/{reports.length}</strong>
          <small>{passages} indexed source passages</small>
        </div>
      </section>
      <ReportSearch />
      <section className="section-block">
        <div className="section-heading">
          <div>
            <span className="eyebrow">Evidence library</span>
            <h2>Inspection reports</h2>
          </div>
        </div>
        {reports.length ? (
          <div className="report-ledger">
            {reports.map((report) => (
              <article key={report.id}>
                <div>
                  <span>{report.original_filename}</span>
                  <strong>{report.site_name}</strong>
                </div>
                <dl>
                  <div><dt>Status</dt><dd>{titleCase(report.ingestion_status)}</dd></div>
                  <div><dt>Passages</dt><dd>{report.chunk_count}</dd></div>
                  <div><dt>Added</dt><dd>{formatDate(report.created_at, true)}</dd></div>
                </dl>
                <Link href={`/inspections/${report.inspection_id}`}>View inspection →</Link>
              </article>
            ))}
          </div>
        ) : (
          <EmptyState
            title="No reports uploaded"
            message="Upload a PDF from an inspection page to begin report indexing."
            action={{ href: "/inspections", label: "Open inspections" }}
          />
        )}
      </section>
    </div>
  );
}
