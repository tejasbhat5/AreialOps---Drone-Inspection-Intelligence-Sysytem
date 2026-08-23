import type { Metadata } from "next";
import Link from "next/link";
import { CreateSiteForm } from "@/components/create-site-form";
import { SiteMapLoader } from "@/components/map/site-map-loader";
import { SiteCard } from "@/components/site-card";
import { EmptyState } from "@/components/ui/states";
import { getMapSites, getSites } from "@/lib/api";
import { titleCase } from "@/lib/format";
import type {
  RiskLevel,
  SiteFilters,
  SiteStatus,
  SiteType,
} from "@/types/domain";

export const metadata: Metadata = { title: "Sites | AerialOps" };
type SearchParams = Promise<Record<string, string | string[] | undefined>>;
const one = (value: string | string[] | undefined) =>
  Array.isArray(value) ? value[0] : value;

export default async function SitesPage({
  searchParams,
}: {
  searchParams: SearchParams;
}) {
  const raw = await searchParams;
  const filters: SiteFilters = {
    query: one(raw.query),
    site_type: one(raw.site_type) as SiteType | undefined,
    status: one(raw.status) as SiteStatus | undefined,
    risk_level: one(raw.risk_level) as RiskLevel | undefined,
    sort: one(raw.sort) as SiteFilters["sort"],
    page: Number(one(raw.page) ?? 1) || 1,
  };
  const [result, mapSites] = await Promise.all([
    getSites(filters),
    getMapSites(filters),
  ]);
  const hasFilters = Boolean(
    filters.query || filters.site_type || filters.status || filters.risk_level,
  );
  return (
    <div className="page">
      <section className="hero-row">
        <div className="page-heading">
          <span className="eyebrow">Site registry</span>
          <h1>Every asset. One operating picture.</h1>
          <p>
            Search, filter, and inspect the infrastructure under management.
          </p>
        </div>
        <div className="hero-index">
          <span>Registered assets</span>
          <strong>{result.total}</strong>
          <small>Matching current view</small>
        </div>
      </section>
      <section className="filter-panel">
        <form className="filters">
          <label className="search-field">
            Search sites
            <input
              name="query"
              defaultValue={filters.query}
              placeholder="Name or location"
            />
          </label>
          <Select
            name="site_type"
            label="Asset type"
            value={filters.site_type}
            options={[
              "SOLAR_FARM",
              "WIND_FARM",
              "RAIL",
              "BRIDGE",
              "MINE",
              "TRANSMISSION",
              "INDUSTRIAL",
              "CONSTRUCTION",
              "OTHER",
            ]}
          />
          <Select
            name="status"
            label="Status"
            value={filters.status}
            options={["ACTIVE", "MAINTENANCE", "INACTIVE", "ARCHIVED"]}
          />
          <Select
            name="risk_level"
            label="Risk"
            value={filters.risk_level}
            options={["CRITICAL", "HIGH", "MODERATE", "LOW"]}
          />
          <Select
            name="sort"
            label="Sort"
            value={filters.sort ?? "name"}
            includeAll={false}
            options={["name", "risk_desc", "created_at_desc"]}
          />
          <button className="button button-secondary">Apply filters</button>
          {hasFilters ? (
            <Link className="text-link clear-filter" href="/sites">
              Clear
            </Link>
          ) : null}
        </form>
      </section>
      <section className="section-block map-section">
        <div className="section-heading map-heading">
          <div>
            <span className="eyebrow">Geospatial operations</span>
            <h2>Filtered site map</h2>
            <p>
              The map follows the same search, type, status, and risk filters as
              the registry.
            </p>
          </div>
          <div className="map-legend" aria-label="Marker risk legend">
            {(["LOW", "MODERATE", "HIGH", "CRITICAL"] as const).map((level) => (
              <span key={level}>
                <i className={`risk-${level.toLowerCase()}`} />
                {titleCase(level)}
              </span>
            ))}
          </div>
        </div>
        {mapSites.items.length ? (
          <>
            <SiteMapLoader sites={mapSites.items} />
            {mapSites.truncated ? (
              <p className="map-notice">
                Showing the first 500 of {mapSites.total} matching sites. Narrow
                the filters for a complete view.
              </p>
            ) : null}
          </>
        ) : (
          <EmptyState
            title="No coordinates to display"
            message="Adjust the filters or register a site to populate the map."
          />
        )}
      </section>
      <section className="section-block">
        <div className="section-heading">
          <div>
            <span className="eyebrow">Registry results</span>
            <h2>
              {result.total} {result.total === 1 ? "site" : "sites"}
            </h2>
          </div>
        </div>
        {result.items.length ? (
          <>
            <div className="site-grid">
              {result.items.map((site) => (
                <SiteCard key={site.id} site={site} />
              ))}
            </div>
            <Pagination result={result} raw={raw} />
          </>
        ) : (
          <EmptyState
            title={
              hasFilters
                ? "No sites match these filters"
                : "No sites registered"
            }
            message={
              hasFilters
                ? "Adjust or clear the current filters to widen the search."
                : "Register your first infrastructure site to start monitoring it."
            }
            action={
              hasFilters
                ? { href: "/sites", label: "Clear filters" }
                : undefined
            }
          />
        )}
      </section>
      <section className="section-block form-section" id="new-site">
        <div className="section-heading">
          <div>
            <span className="eyebrow">New asset</span>
            <h2>Register a site</h2>
            <p>
              Add the base location record. Inspection history can follow in the
              next workflow.
            </p>
          </div>
        </div>
        <CreateSiteForm />
      </section>
    </div>
  );
}

function Select({
  name,
  label,
  value,
  options,
  includeAll = true,
}: {
  name: string;
  label: string;
  value?: string;
  options: string[];
  includeAll?: boolean;
}) {
  return (
    <label>
      {label}
      <select name={name} defaultValue={value ?? ""}>
        {includeAll ? <option value="">All</option> : null}
        {options.map((option) => (
          <option value={option} key={option}>
            {titleCase(option)}
          </option>
        ))}
      </select>
    </label>
  );
}

function Pagination({
  result,
  raw,
}: {
  result: { page: number; has_next: boolean };
  raw: Record<string, string | string[] | undefined>;
}) {
  const href = (page: number) => {
    const params = new URLSearchParams();
    Object.entries(raw).forEach(([key, value]) => {
      const normalized = one(value);
      if (normalized && key !== "page") params.set(key, normalized);
    });
    params.set("page", String(page));
    return `/sites?${params}`;
  };
  if (result.page === 1 && !result.has_next) return null;
  return (
    <nav className="pagination" aria-label="Sites pagination">
      {result.page > 1 ? (
        <Link className="button button-secondary" href={href(result.page - 1)}>
          ← Previous
        </Link>
      ) : (
        <span />
      )}
      <span>Page {result.page}</span>
      {result.has_next ? (
        <Link className="button button-secondary" href={href(result.page + 1)}>
          Next →
        </Link>
      ) : (
        <span />
      )}
    </nav>
  );
}
