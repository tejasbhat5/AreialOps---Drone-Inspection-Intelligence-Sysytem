import { RiskBadge } from "@/components/ui/risk-badge";
import { formatDate, titleCase } from "@/lib/format";
import type { Anomaly } from "@/types/domain";

export function AnomalyCard({ anomaly }: { anomaly: Anomaly }) {
  return (
    <article className="record-card anomaly-card">
      <div>
        <span className="record-kicker">
          Logged {formatDate(anomaly.created_at)}
        </span>
        <h3>{anomaly.title}</h3>
      </div>
      <RiskBadge level={anomaly.severity} />
      <p>{anomaly.description}</p>
      <span className="record-status">{titleCase(anomaly.status)}</span>
    </article>
  );
}
