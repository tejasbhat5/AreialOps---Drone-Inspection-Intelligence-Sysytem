import type { Metadata } from "next";
import Link from "next/link";
import { InspectionCard } from "@/components/inspection-card";
import { MetricCard } from "@/components/metric-card";
import { SiteCard } from "@/components/site-card";
import { EmptyState } from "@/components/ui/states";
import { getDashboardSummary } from "@/lib/api";
import { titleCase } from "@/lib/format";

export const metadata: Metadata = { title: "Command Center | AerialOps" };

export default async function DashboardPage() {
  const summary = await getDashboardSummary();
  const { metrics } = summary;
  const severityOrder = ["CRITICAL", "HIGH", "MODERATE", "LOW"];

  return (
    <div className="page">
      <section className="hero-row">
        <div className="page-heading">
          <span className="eyebrow">Command center</span>
          <h1>Operational risk, at a glance.</h1>
          <p>
            Live site, inspection, and anomaly signals from the AerialOps
            service.
          </p>
        </div>
        <div className="hero-index">
          <span>Fleet readiness</span>
          <strong>
            {metrics.total_sites
              ? Math.round((metrics.active_sites / metrics.total_sites) * 100)
              : 0}
            %
          </strong>
          <small>
            {metrics.active_sites} of {metrics.total_sites} sites active
          </small>
        </div>
      </section>
      <section className="metrics-grid" aria-label="Operational metrics">
        <MetricCard
          label="Monitored sites"
          value={metrics.total_sites}
          detail="Total registered assets"
        />
        <MetricCard
          label="Active sites"
          value={metrics.active_sites}
          detail="Currently in operation"
          tone="positive"
        />
        <MetricCard
          label="Critical sites"
          value={metrics.critical_sites}
          detail="Immediate review required"
          tone="attention"
        />
        <MetricCard
          label="Monthly inspections"
          value={metrics.inspections_this_month}
          detail="Completed or underway"
        />
        <MetricCard
          label="Open anomalies"
          value={metrics.unresolved_anomalies}
          detail="Unresolved findings"
          tone={metrics.unresolved_anomalies ? "attention" : "positive"}
        />
        <MetricCard
          label="Average risk"
          value={`${metrics.average_risk_score.toFixed(1)}/100`}
          detail="Across monitored sites"
        />
      </section>
      <div className="dashboard-columns">
        <section className="section-block">
          <div className="section-heading">
            <div>
              <span className="eyebrow">Inspection stream</span>
              <h2>Recent field activity</h2>
            </div>
          </div>
          {summary.recent_inspections.length ? (
            <div className="record-list">
              {summary.recent_inspections.map((inspection) => (
                <InspectionCard inspection={inspection} key={inspection.id} />
              ))}
            </div>
          ) : (
            <EmptyState
              title="No inspections yet"
              message="Field activity will appear here once an inspection is recorded."
            />
          )}
        </section>
        <aside className="section-block severity-panel">
          <div className="section-heading">
            <div>
              <span className="eyebrow">Finding profile</span>
              <h2>Anomalies by severity</h2>
            </div>
          </div>
          <div className="severity-list">
            {severityOrder.map((severity) => {
              const count = summary.anomaly_counts_by_severity[severity] ?? 0;
              const max = Math.max(
                1,
                ...Object.values(summary.anomaly_counts_by_severity),
              );
              return (
                <div className="severity-row" key={severity}>
                  <div>
                    <span>{titleCase(severity)}</span>
                    <strong>{count}</strong>
                  </div>
                  <div className="severity-track">
                    <span
                      className={`severity-fill risk-${severity.toLowerCase()}`}
                      style={{ width: `${(count / max) * 100}%` }}
                    />
                  </div>
                </div>
              );
            })}
          </div>
        </aside>
      </div>
      <section className="section-block">
        <div className="section-heading">
          <div>
            <span className="eyebrow">Priority queue</span>
            <h2>Highest-risk sites</h2>
          </div>
          <Link className="text-link" href="/sites?sort=risk_desc">
            View all sites →
          </Link>
        </div>
        {summary.highest_risk_sites.length ? (
          <div className="site-grid compact-grid">
            {summary.highest_risk_sites.map((site) => (
              <SiteCard key={site.id} site={site} />
            ))}
          </div>
        ) : (
          <EmptyState
            title="No site risk to review"
            message="Register a site to begin building the operational risk view."
            action={{ href: "/sites#new-site", label: "Register first site" }}
          />
        )}
      </section>
    </div>
  );
}
