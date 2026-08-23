import type { Metadata } from "next";
import Link from "next/link";
import { notFound } from "next/navigation";
import { AnomalyCard } from "@/components/anomaly-card";
import { ImageUploadForm, ReportUploadForm } from "@/components/upload-form";
import { EmptyState } from "@/components/ui/states";
import {
  ApiError,
  getInspection,
  getInspectionImages,
  getInspectionJobs,
  getInspectionReport,
  getSite,
} from "@/lib/api";
import { formatDate, titleCase } from "@/lib/format";

export const metadata: Metadata = { title: "Inspection | AerialOps" };
type Params = Promise<{ id: string }>;

export default async function InspectionDetailPage({ params }: { params: Params }) {
  const { id } = await params;
  let inspection;
  try {
    inspection = await getInspection(id);
  } catch (error) {
    if (error instanceof ApiError && error.status === 404) notFound();
    throw error;
  }
  const [site, images, report, jobs] = await Promise.all([
    getSite(inspection.site_id),
    getInspectionImages(id),
    getInspectionReport(id),
    getInspectionJobs(id),
  ]);
  return (
    <div className="page">
      <Link className="back-link" href="/inspections">← Inspection ledger</Link>
      <section className="site-hero">
        <div><span className="eyebrow">{titleCase(inspection.status)} inspection</span><h1>{site.name}</h1><p>{formatDate(inspection.inspected_at, true)} · {site.location}</p></div>
        <div className="risk-panel"><span>Evidence package</span><strong>{images.length + (report ? 1 : 0)}<small> files</small></strong><span className="count-chip">{jobs.filter((job) => job.status === "PENDING").length} queued</span></div>
      </section>
      <section className="snapshot-grid">
        <article><span>Status</span><strong className="date-value">{titleCase(inspection.status)}</strong><small>Workflow state</small></article>
        <article><span>Images</span><strong>{images.length}</strong><small>Verified uploads</small></article>
        <article><span>Findings</span><strong>{inspection.anomalies.length}</strong><small>Recorded anomalies</small></article>
        <article><span>Report</span><strong className="date-value">{report ? titleCase(report.ingestion_status) : "Not uploaded"}</strong><small>Ingestion state</small></article>
      </section>
      <section className="section-block">
        <div className="section-heading"><div><span className="eyebrow">Field notes</span><h2>Inspection summary</h2></div><Link className="text-link" href={`/sites/${site.id}`}>Open site →</Link></div>
        <p className="long-copy">{inspection.notes || "No field notes were recorded."}</p>
      </section>
      <div className="detail-columns upload-columns">
        <section className="section-block"><div className="section-heading"><div><span className="eyebrow">Visual evidence</span><h2>Inspection imagery</h2></div><span className="count-chip">{images.length}</span></div><ImageUploadForm inspectionId={id} />{images.length ? <div className="file-list">{images.map((image) => <article key={image.id}><div><strong>{image.original_filename}</strong><span>{(image.size_bytes / 1024).toFixed(1)} KB · {image.content_type}</span></div><span className="record-status">{titleCase(image.review_status)}</span></article>)}</div> : <EmptyState title="No imagery uploaded" message="Attach drone, visual, or thermal images for this inspection." />}</section>
        <section className="section-block"><div className="section-heading"><div><span className="eyebrow">Document evidence</span><h2>Inspection report</h2></div></div>{report ? <div className="file-list"><article><div><strong>{report.original_filename}</strong><span>{(report.size_bytes / 1024).toFixed(1)} KB · PDF</span></div><span className="record-status">{titleCase(report.ingestion_status)}</span></article></div> : <ReportUploadForm inspectionId={id} />}</section>
      </div>
      <div className="detail-columns">
        <section className="section-block"><div className="section-heading"><div><span className="eyebrow">Finding register</span><h2>Anomalies</h2></div></div>{inspection.anomalies.length ? <div className="record-list">{inspection.anomalies.map((item) => <AnomalyCard anomaly={item} key={item.id} />)}</div> : <EmptyState title="No findings" message="This inspection currently has no recorded anomalies." />}</section>
        <section className="section-block"><div className="section-heading"><div><span className="eyebrow">Pipeline telemetry</span><h2>Processing jobs</h2></div></div>{jobs.length ? <div className="job-list">{jobs.map((job) => <article key={job.id}><span className={`job-dot job-${job.status.toLowerCase()}`} /><div><strong>{titleCase(job.job_type)}</strong><small>{titleCase(job.status)} · {formatDate(job.created_at, true)}</small></div></article>)}</div> : <EmptyState title="No processing jobs" message="Jobs appear when evidence is uploaded." />}</section>
      </div>
    </div>
  );
}
