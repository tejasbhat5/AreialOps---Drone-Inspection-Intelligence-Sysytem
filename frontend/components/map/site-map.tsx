"use client";

import { useEffect, useMemo, useState } from "react";
import Link from "next/link";
import { divIcon, latLngBounds } from "leaflet";
import { MapContainer, Marker, Popup, TileLayer, useMap } from "react-leaflet";
import { RiskBadge } from "@/components/ui/risk-badge";
import { formatCoordinate, titleCase } from "@/lib/format";
import { validSiteMapPoints, type SiteMapPoint } from "@/lib/map";
import type { Site } from "@/types/domain";

const TILE_URL =
  process.env.NEXT_PUBLIC_MAP_TILE_URL ??
  "https://tile.openstreetmap.org/{z}/{x}/{y}.png";

export default function SiteMap({
  sites,
  compact = false,
}: {
  sites: Site[];
  compact?: boolean;
}) {
  const points = useMemo(() => validSiteMapPoints(sites), [sites]);
  const [selectedId, setSelectedId] = useState(points[0]?.id);
  const selected = points.find((site) => site.id === selectedId) ?? points[0];

  if (!points.length)
    return (
      <div className="map-loading">
        <span>No valid coordinates to map.</span>
      </div>
    );

  return (
    <div className={`site-map-layout${compact ? "map-compact" : ""}`}>
      <MapContainer
        center={[points[0].latitude, points[0].longitude]}
        zoom={compact ? 12 : 5}
        scrollWheelZoom
        className="site-map-canvas"
        aria-label="Interactive map of infrastructure sites"
      >
        <TileLayer
          attribution='&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors'
          url={TILE_URL}
        />
        <FitToSites sites={points} compact={compact} />
        {points.map((site) => (
          <Marker
            key={`${site.id}:${site.current_risk_level}:${site.current_risk_score}`}
            position={[site.latitude, site.longitude]}
            icon={riskIcon(site.current_risk_level)}
            title={`${site.name}: ${titleCase(site.current_risk_level)} risk`}
            alt={`${site.name} map marker`}
            eventHandlers={{
              click: () => setSelectedId(site.id),
              keypress: () => setSelectedId(site.id),
            }}
          >
            <Popup>
              <strong>{site.name}</strong>
              <br />
              {site.location}
              <br />
              Risk: {titleCase(site.current_risk_level)} (
              {site.current_risk_score}/100)
            </Popup>
          </Marker>
        ))}
      </MapContainer>
      {!compact && selected ? <SiteSelection site={selected} /> : null}
    </div>
  );
}

function FitToSites({
  sites,
  compact,
}: {
  sites: SiteMapPoint[];
  compact: boolean;
}) {
  const map = useMap();
  useEffect(() => {
    if (sites.length === 1)
      map.setView([sites[0].latitude, sites[0].longitude], compact ? 12 : 10);
    else
      map.fitBounds(
        latLngBounds(sites.map((site) => [site.latitude, site.longitude])),
        { padding: [36, 36], maxZoom: 11 },
      );
  }, [compact, map, sites]);
  return null;
}

function SiteSelection({ site }: { site: SiteMapPoint }) {
  return (
    <aside className="map-selection" aria-live="polite">
      <span className="eyebrow">Selected site</span>
      <h3>{site.name}</h3>
      <p>{site.location}</p>
      <RiskBadge
        level={site.current_risk_level}
        score={site.current_risk_score}
      />
      <dl>
        <div>
          <dt>Asset type</dt>
          <dd>{titleCase(site.site_type)}</dd>
        </div>
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
      <Link className="button button-secondary" href={`/sites/${site.id}`}>
        Open site record →
      </Link>
    </aside>
  );
}

function riskIcon(level: Site["current_risk_level"]) {
  return divIcon({
    className: "risk-map-marker-wrap",
    html: `<span class="risk-map-marker risk-${level.toLowerCase()}"><span></span></span>`,
    iconSize: [28, 28],
    iconAnchor: [14, 14],
    popupAnchor: [0, -15],
  });
}
