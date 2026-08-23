"use server";

import { revalidatePath } from "next/cache";
import { redirect } from "next/navigation";
import {
  ApiError,
  createInspection,
  uploadInspectionImages,
  uploadInspectionReport,
} from "@/lib/api";
import type { AnomalySeverity, InspectionStatus } from "@/types/domain";

export type FormState = { message: string; success?: boolean };

const messageFor = (error: unknown, fallback: string) =>
  error instanceof ApiError ? error.message : fallback;

export async function createInspectionAction(
  _state: FormState,
  formData: FormData,
): Promise<FormState> {
  const text = (name: string) => String(formData.get(name) ?? "").trim();
  const siteId = text("site_id");
  const inspectedAt = text("inspected_at");
  if (!siteId || !inspectedAt)
    return { message: "Choose a site and inspection date." };

  const anomalyTitle = text("anomaly_title");
  const anomalyDescription = text("anomaly_description");
  let inspection;
  try {
    inspection = await createInspection({
      site_id: siteId,
      inspected_at: new Date(inspectedAt).toISOString(),
      status: text("status") as InspectionStatus,
      notes: text("notes") || null,
      anomalies: anomalyTitle
        ? [
            {
              title: anomalyTitle,
              description:
                anomalyDescription || "Finding recorded during field inspection.",
              severity: text("anomaly_severity") as AnomalySeverity,
            },
          ]
        : [],
    });
  } catch (error) {
    return { message: messageFor(error, "The inspection could not be created.") };
  }
  revalidatePath("/dashboard");
  revalidatePath("/inspections");
  revalidatePath(`/sites/${siteId}`);
  redirect(`/inspections/${inspection.id}`);
}

export async function uploadImagesAction(
  _state: FormState,
  formData: FormData,
): Promise<FormState> {
  const inspectionId = String(formData.get("inspection_id") ?? "");
  const files = formData
    .getAll("files")
    .filter((value): value is File => value instanceof File && value.size > 0);
  if (!files.length) return { message: "Select at least one image." };
  try {
    await uploadInspectionImages(inspectionId, files);
  } catch (error) {
    return { message: messageFor(error, "The images could not be uploaded.") };
  }
  revalidatePath(`/inspections/${inspectionId}`);
  return { message: `${files.length} image${files.length === 1 ? "" : "s"} queued for analysis.`, success: true };
}

export async function uploadReportAction(
  _state: FormState,
  formData: FormData,
): Promise<FormState> {
  const inspectionId = String(formData.get("inspection_id") ?? "");
  const file = formData.get("file");
  if (!(file instanceof File) || !file.size)
    return { message: "Select a PDF report." };
  try {
    await uploadInspectionReport(inspectionId, file);
  } catch (error) {
    return { message: messageFor(error, "The report could not be uploaded.") };
  }
  revalidatePath(`/inspections/${inspectionId}`);
  return { message: "Report stored and queued for ingestion.", success: true };
}
