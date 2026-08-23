"use server";

import { redirect } from "next/navigation";
import { revalidatePath } from "next/cache";
import { ApiError, createSite, recalculateSiteRisk } from "@/lib/api";
import type { SiteStatus, SiteType } from "@/types/domain";

export type CreateSiteState = {
  message: string;
  errors?: Record<string, string>;
};

export async function createSiteAction(
  _state: CreateSiteState,
  formData: FormData,
): Promise<CreateSiteState> {
  const text = (name: string) => String(formData.get(name) ?? "").trim();
  const fields = {
    name: text("name"),
    site_type: text("site_type"),
    location: text("location"),
    latitude: text("latitude"),
    longitude: text("longitude"),
    status: text("status"),
  };
  const errors: Record<string, string> = {};
  if (!fields.name) errors.name = "Enter a site name.";
  if (!fields.location) errors.location = "Enter a location.";
  const latitude = Number(fields.latitude);
  const longitude = Number(fields.longitude);
  if (!Number.isFinite(latitude) || latitude < -90 || latitude > 90)
    errors.latitude = "Use a latitude from -90 to 90.";
  if (!Number.isFinite(longitude) || longitude < -180 || longitude > 180)
    errors.longitude = "Use a longitude from -180 to 180.";
  if (Object.keys(errors).length)
    return { message: "Check the highlighted fields.", errors };

  let site;
  try {
    site = await createSite({
      name: fields.name,
      site_type: fields.site_type as SiteType,
      location: fields.location,
      latitude,
      longitude,
      status: fields.status as SiteStatus,
    });
  } catch (error) {
    return {
      message:
        error instanceof ApiError
          ? error.message
          : "The site could not be created.",
    };
  }
  revalidatePath("/dashboard");
  revalidatePath("/sites");
  redirect(`/sites/${site.id}`);
}

export async function recalculateRiskAction(formData: FormData) {
  const siteId = String(formData.get("site_id") ?? "");
  if (!siteId) return;
  await recalculateSiteRisk(siteId);
  revalidatePath("/dashboard");
  revalidatePath("/sites");
  revalidatePath(`/sites/${siteId}`);
}
