"use client";

import dynamic from "next/dynamic";
import type { Site } from "@/types/domain";

const SiteMap = dynamic(() => import("@/components/map/site-map"), {
  ssr: false,
  loading: () => (
    <div className="map-loading" aria-label="Loading interactive map">
      <span>Loading geospatial view…</span>
    </div>
  ),
});

export function SiteMapLoader({
  sites,
  compact = false,
}: {
  sites: Site[];
  compact?: boolean;
}) {
  return <SiteMap sites={sites} compact={compact} />;
}
