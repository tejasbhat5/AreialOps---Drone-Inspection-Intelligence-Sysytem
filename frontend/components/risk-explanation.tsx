import { recalculateRiskAction } from "@/app/(workspace)/sites/actions";
import { RiskBadge } from "@/components/ui/risk-badge";
import { formatDate, titleCase } from "@/lib/format";
import type { AnomalySeverity, RiskAssessment } from "@/types/domain";

const severities: AnomalySeverity[] = ["CRITICAL", "HIGH", "MODERATE", "LOW"];
const number = (value: number | undefined) => value ?? 0;

export function RiskExplanation({
  siteId,
  assessment,
  history,
}: {
  siteId: string;
  assessment: RiskAssessment | null;
  history: RiskAssessment[];
}) {
  if (!assessment) {
    return (
      <section className="section-block risk-explanation">
        <div className="section-heading">
          <div><span className="eyebrow">Deterministic assessment</span><h2>Risk has not been calculated</h2><p>Run the versioned formula to establish an explainable baseline.</p></div>
          <RecalculateButton siteId={siteId} />
        </div>
      </section>
    );
  }

  const factors = assessment.factor_snapshot;
  const deterministic = assessment.formula_version === "deterministic-v1";
  return (
    <section className="section-block risk-explanation">
      <div className="section-heading">
        <div>
          <span className="eyebrow">Deterministic assessment</span>
          <h2>Why this site is {assessment.level.toLowerCase()} risk</h2>
          <p>Formula {assessment.formula_version} · calculated {formatDate(assessment.calculated_at, true)}</p>
        </div>
        <div className="risk-heading-actions"><RiskBadge level={assessment.level} /><RecalculateButton siteId={siteId} /></div>
      </div>
      {deterministic ? (
        <>
          <div className="risk-equation" aria-label="Risk score equation">
            <Factor label="Severity" value={number(factors.severity_points)} detail={`cap ${number(factors.severity_cap)}`} />
            <span>+</span>
            <Factor label="Critical bonus" value={number(factors.critical_bonus)} detail="critical presence" />
            <span>+</span>
            <Factor label="Finding volume" value={number(factors.volume_points)} detail={`cap ${number(factors.volume_cap)}`} />
            <span>+</span>
            <Factor label="Inspection age" value={number(factors.recency_points)} detail={factors.days_since_completed_inspection == null ? "never completed" : `${factors.days_since_completed_inspection} days`} />
            <span>=</span>
            <div className="risk-total"><strong>{assessment.score}</strong><small>/100</small></div>
          </div>
          <div className="risk-detail-grid">
            <div>
              <span className="record-kicker">Unresolved findings</span>
              <strong className="risk-detail-value">{number(factors.unresolved_anomaly_count)}</strong>
              <div className="severity-counts">
                {severities.map((severity) => (
                  <span key={severity}><i className={`risk-${severity.toLowerCase()}`} />{titleCase(severity)} {factors.severity_counts?.[severity] ?? 0} × {factors.severity_weights?.[severity] ?? 0}</span>
                ))}
              </div>
            </div>
            <div>
              <span className="record-kicker">Latest completed inspection</span>
              <strong className="risk-detail-date">{factors.latest_completed_inspection_at ? formatDate(factors.latest_completed_inspection_at, true) : "No completed inspection"}</strong>
              <p>Only persisted operational facts contribute to the score. The AI assistant can explain it later, but cannot change it.</p>
            </div>
          </div>
        </>
      ) : (
        <p className="legacy-risk-note">This is a seeded demonstration assessment. Recalculate it to replace the legacy snapshot with the current deterministic formula.</p>
      )}
      {history.length ? (
        <div className="risk-history">
          <span className="record-kicker">Assessment history</span>
          <div>
            {history.slice(0, 8).map((item) => (
              <article key={item.id}><time>{formatDate(item.calculated_at, true)}</time><strong>{item.score}</strong><RiskBadge level={item.level} /><small>{item.formula_version}</small></article>
            ))}
          </div>
        </div>
      ) : null}
    </section>
  );
}

function Factor({ label, value, detail }: { label: string; value: number; detail: string }) {
  return <div className="risk-factor"><span>{label}</span><strong>{value}</strong><small>{detail}</small></div>;
}

function RecalculateButton({ siteId }: { siteId: string }) {
  return (
    <form action={recalculateRiskAction}>
      <input type="hidden" name="site_id" value={siteId} />
      <button className="button button-secondary">Recalculate</button>
    </form>
  );
}
