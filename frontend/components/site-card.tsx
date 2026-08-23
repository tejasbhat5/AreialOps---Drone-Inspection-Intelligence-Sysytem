import Link from "next/link";
import { RiskBadge } from "@/components/ui/risk-badge";
import { formatCoordinate, titleCase } from "@/lib/format";
import type { Site } from "@/types/domain";

export function SiteCard({ site }: { site: Site }) {
  return (
    <article className="site-card">
      <div className="card-topline">
        <span className="site-type">{titleCase(site.site_type)}</span>
        <RiskBadge
          level={site.current_risk_level}
          score={site.current_risk_score}
        />
      </div>
      <div>
        <h3>
          <Link href={`/sites/${site.id}`}>{site.name}</Link>
        </h3>
        <p>{site.location}</p>
      </div>
      <dl className="site-meta">
        <div>
          <dt>Status</dt>
          <dd>{titleCase(site.status)}</dd>
        </div>
        <div>
          <dt>Coordinates</dt>
          <dd>
            {formatCoordinate(site.latitude)},{" "}
            {formatCoordinate(site.longitude)}
          </dd>
        </div>
      </dl>
      <Link className="text-link" href={`/sites/${site.id}`}>
        Open site record <span aria-hidden="true">→</span>
      </Link>
    </article>
  );
}
