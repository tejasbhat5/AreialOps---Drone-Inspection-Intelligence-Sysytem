"use server";

import { ApiError, searchReports } from "@/lib/api";

export async function searchReportsAction(query: string) {
  const cleaned = query.trim();
  if (cleaned.length < 2 || cleaned.length > 500) {
    return { ok: false as const, message: "Enter between 2 and 500 characters." };
  }
  try {
    return { ok: true as const, response: await searchReports(cleaned) };
  } catch (error) {
    return {
      ok: false as const,
      message: error instanceof ApiError ? error.message : "Report search is unavailable.",
    };
  }
}
