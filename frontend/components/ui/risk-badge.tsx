import type { RiskLevel } from "@/types/domain";
import { titleCase } from "@/lib/format";

export function RiskBadge({
  level,
  score,
}: {
  level: RiskLevel;
  score?: number;
}) {
  return (
    <span className={`badge risk-${level.toLowerCase()}`}>
      <span className="badge-dot" aria-hidden="true" />
      {titleCase(level)}
      {score === undefined ? "" : ` · ${score}`}
    </span>
  );
}
