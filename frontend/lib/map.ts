import type { Site } from "@/types/domain";

export type SiteMapPoint = Site & { latitude: number; longitude: number };

export function toSiteMapPoint(site: Site): SiteMapPoint | null {
  const latitude = Number(site.latitude);
  const longitude = Number(site.longitude);
  if (
    !Number.isFinite(latitude) ||
    !Number.isFinite(longitude) ||
    latitude < -90 ||
    latitude > 90 ||
    longitude < -180 ||
    longitude > 180
  ) {
    return null;
  }
  return { ...site, latitude, longitude };
}

export function validSiteMapPoints(sites: Site[]) {
  return sites
    .map(toSiteMapPoint)
    .filter((site): site is SiteMapPoint => site !== null);
}
