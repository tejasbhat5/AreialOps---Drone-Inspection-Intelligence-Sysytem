import type { Metadata } from "next";
import Link from "next/link";
import { notFound } from "next/navigation";
import { AnomalyCard } from "@/components/anomaly-card";
import { InspectionCard } from "@/components/inspection-card";
import { SiteMapLoader } from "@/components/map/site-map-loader";
import { RiskBadge } from "@/components/ui/risk-badge";
import { RiskExplanation } from "@/components/risk-explanation";
import { EmptyState } from "@/components/ui/states";
import {
  ApiError,
  getSite,
  getSiteAnomalies,
  getSiteInspections,
  getSiteRisk,
  getSiteRiskHistory,
} from "@/lib/api";
import { formatCoordinate, formatDate, titleCase } from "@/lib/format";

type Params = Promise<{ id: string }>;

export async function generateMetadata({
  params,
}: {
  params: Params;
}): Promise<Metadata> {
  try {
    const site = await getSite((await params).id);
    return { title: `${site.name} | AerialOps` };
  } catch {
    return { title: "Site | AerialOps" };
  }
}

export default async function SiteDetailPage({ params }: { params: Params }) {
  const { id } = await params;
  let site;
  try {
    site = await getSite(id);
  } catch (error) {
    if (error instanceof ApiError && error.status === 404) notFound();
    throw error;
  }
  const [inspections, anomalies, risk, riskHistory] = await Promise.all([
    getSiteInspections(id),
    getSiteAnomalies(id),
    getSiteRisk(id),
    getSiteRiskHistory(id),
  ]);
  return (
    <div className="page">
      <Link className="back-link" href="/sites">
        ← Site registry
      </Link>
      <section className="site-hero">
        <div>
          <span className="eyebrow">{titleCase(site.site_type)}</span>
          <h1>{site.name}</h1>
          <p>{site.location}</p>
        </div>
        <div className="risk-panel">
          <span>Current risk posture</span>
          <strong>
            {site.current_risk_score}
            <small>/100</small>
          </strong>
          <RiskBadge level={site.current_risk_level} />
        </div>
      </section>
      <section className="snapshot-grid" aria-label="Operational snapshot">
        <article>
          <span>Status</span>
          <strong>{titleCase(site.status)}</strong>
          <small>Operating state</small>
        </article>
        <article>
          <span>Inspections</span>
          <strong>{site.inspection_count}</strong>
          <small>Recorded site visits</small>
        </article>
        <article>
          <span>Open anomalies</span>
          <strong>{site.unresolved_anomaly_count}</strong>
          <small>Awaiting resolution</small>
        </article>
        <article>
          <span>Last updated</span>
          <strong className="date-value">{formatDate(site.updated_at)}</strong>
          <small>Record freshness</small>
        </article>
      </section>
      <RiskExplanation siteId={id} assessment={risk} history={riskHistory} />
      <section className="section-block map-section site-location-map">
        <div className="section-heading">
          <div>
            <span className="eyebrow">Geospatial reference</span>
            <h2>
              {formatCoordinate(site.latitude)}°,{" "}
              {formatCoordinate(site.longitude)}°
            </h2>
          </div>
          <p className="map-coordinate-note">
            Stored WGS84 latitude and longitude
          </p>
        </div>
        <SiteMapLoader sites={[site]} compact />
      </section>
      <div className="detail-columns">
        <section className="section-block">
          <div className="section-heading">
            <div>
              <span className="eyebrow">Field history</span>
              <h2>Inspections</h2>
            </div>
            <span className="count-chip">{inspections.total} total</span>
          </div>
          {inspections.items.length ? (
            <div className="record-list">
              {inspections.items.map((inspection) => (
                <InspectionCard inspection={inspection} key={inspection.id} />
              ))}
            </div>
          ) : (
            <EmptyState
              title="No inspections recorded"
              message="This site's field history will appear once its first inspection is created."
            />
          )}
        </section>
        <section className="section-block">
          <div className="section-heading">
            <div>
              <span className="eyebrow">Finding register</span>
              <h2>Anomalies</h2>
            </div>
            <span className="count-chip">{anomalies.total} total</span>
          </div>
          {anomalies.items.length ? (
            <div className="record-list">
              {anomalies.items.map((anomaly) => (
                <AnomalyCard anomaly={anomaly} key={anomaly.id} />
              ))}
            </div>
          ) : (
            <EmptyState
              title="No anomalies recorded"
              message="Inspection findings linked to this site will appear here."
            />
          )}
        </section>
      </div>
    </div>
  );
}
