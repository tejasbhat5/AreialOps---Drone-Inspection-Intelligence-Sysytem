import "server-only";

import type {
  Anomaly,
  AssistantCapabilities,
  AssistantResponse,
  DashboardSummary,
  Inspection,
  InspectionCreate,
  InspectionImage,
  InspectionReport,
  Page,
  ProcessingJob,
  RiskAssessment,
  ReportRecord,
  ReportSearchResponse,
  Site,
  SiteCreate,
  SiteDetail,
  SiteFilters,
} from "@/types/domain";

export type HealthResponse = {
  status: "ok";
  service: "aerialops-api";
  version: string;
};

export type BackendHealth =
  | { connected: true; data: HealthResponse }
  | { connected: false; message: string };

const API_BASE_URL = process.env.API_BASE_URL ?? "http://127.0.0.1:8000";

type ApiErrorBody = {
  error?: { code?: string; message?: string; details?: unknown };
};

export class ApiError extends Error {
  constructor(
    message: string,
    public readonly status: number,
    public readonly details?: unknown,
  ) {
    super(message);
    this.name = "ApiError";
  }
}

async function apiFetch<T>(path: string, init?: RequestInit): Promise<T> {
  let response: Response;
  try {
    response = await fetch(`${API_BASE_URL}${path}`, {
      ...init,
      cache: "no-store",
      headers: { "Content-Type": "application/json", ...init?.headers },
      signal: init?.signal ?? AbortSignal.timeout(5_000),
    });
  } catch (error) {
    throw new ApiError(
      error instanceof Error && error.name === "TimeoutError"
        ? "The AerialOps API timed out."
        : "The AerialOps API is unavailable.",
      503,
    );
  }

  if (!response.ok) {
    const body = (await response.json().catch(() => ({}))) as ApiErrorBody;
    throw new ApiError(
      body.error?.message ?? `The API returned HTTP ${response.status}.`,
      response.status,
      body.error?.details,
    );
  }

  return (await response.json()) as T;
}

async function apiUpload<T>(path: string, formData: FormData): Promise<T> {
  let response: Response;
  try {
    response = await fetch(`${API_BASE_URL}${path}`, {
      method: "POST",
      body: formData,
      cache: "no-store",
      signal: AbortSignal.timeout(30_000),
    });
  } catch {
    throw new ApiError("The upload service is unavailable.", 503);
  }
  if (!response.ok) {
    const body = (await response.json().catch(() => ({}))) as ApiErrorBody;
    throw new ApiError(
      body.error?.message ?? `Upload failed with HTTP ${response.status}.`,
      response.status,
      body.error?.details,
    );
  }
  return (await response.json()) as T;
}

function queryString(values: Record<string, string | number | undefined>) {
  const params = new URLSearchParams();
  for (const [key, value] of Object.entries(values)) {
    if (value !== undefined && value !== "") params.set(key, String(value));
  }
  const query = params.toString();
  return query ? `?${query}` : "";
}

export const getDashboardSummary = () =>
  apiFetch<DashboardSummary>("/api/dashboard/summary");

export const getSites = (filters: SiteFilters = {}, pageSize = 24) =>
  apiFetch<Page<Site>>(
    `/api/sites${queryString({ ...filters, page_size: pageSize })}`,
  );

export async function getMapSites(filters: SiteFilters = {}) {
  const mapFilters = { ...filters };
  delete mapFilters.page;
  const items: Site[] = [];
  let page = 1;
  let response: Page<Site>;

  do {
    response = await getSites({ ...mapFilters, page }, 100);
    items.push(...response.items);
    page += 1;
  } while (response.has_next && items.length < 500);

  return { items, total: response.total, truncated: response.has_next };
}

export const getSite = (siteId: string) =>
  apiFetch<SiteDetail>(`/api/sites/${siteId}`);

export const getSiteInspections = (siteId: string) =>
  apiFetch<Page<Inspection>>(`/api/sites/${siteId}/inspections?page_size=20`);

export const getSiteAnomalies = (siteId: string) =>
  apiFetch<Page<Anomaly>>(`/api/sites/${siteId}/anomalies?page_size=20`);

export const getSiteRisk = (siteId: string) =>
  apiFetch<RiskAssessment | null>(`/api/sites/${siteId}/risk`);

export const getSiteRiskHistory = (siteId: string) =>
  apiFetch<RiskAssessment[]>(`/api/sites/${siteId}/risk/history?limit=20`);

export const recalculateSiteRisk = (siteId: string) =>
  apiFetch<RiskAssessment>(`/api/sites/${siteId}/risk/recalculate`, {
    method: "POST",
  });

export const createSite = (data: SiteCreate) =>
  apiFetch<Site>("/api/sites", { method: "POST", body: JSON.stringify(data) });

export const getInspections = (pageSize = 50) =>
  apiFetch<Page<Inspection>>(`/api/inspections?page_size=${pageSize}`);

export const getInspection = (inspectionId: string) =>
  apiFetch<Inspection>(`/api/inspections/${inspectionId}`);

export const createInspection = (data: InspectionCreate) =>
  apiFetch<Inspection>("/api/inspections", {
    method: "POST",
    body: JSON.stringify(data),
  });

export const getInspectionImages = (inspectionId: string) =>
  apiFetch<InspectionImage[]>(`/api/inspections/${inspectionId}/images`);

export const getInspectionReport = (inspectionId: string) =>
  apiFetch<InspectionReport | null>(`/api/inspections/${inspectionId}/report`);

export const getInspectionJobs = (inspectionId: string) =>
  apiFetch<ProcessingJob[]>(`/api/inspections/${inspectionId}/jobs`);

export const uploadInspectionImages = (inspectionId: string, files: File[]) => {
  const data = new FormData();
  files.forEach((file) => data.append("files", file));
  return apiUpload(`/api/inspections/${inspectionId}/images`, data);
};

export const uploadInspectionReport = (inspectionId: string, file: File) => {
  const data = new FormData();
  data.append("file", file);
  return apiUpload(`/api/inspections/${inspectionId}/report`, data);
};

export const queryAssistant = (
  message: string,
  conversationId?: string,
  currentSiteId?: string,
) =>
  apiFetch<AssistantResponse>("/api/assistant/query", {
    method: "POST",
    signal: AbortSignal.timeout(65_000),
    body: JSON.stringify({
      message,
      conversation_id: conversationId,
      context: { current_site_id: currentSiteId },
    }),
  });

export const getAssistantCapabilities = () =>
  apiFetch<AssistantCapabilities>("/api/assistant/capabilities");

export const getReports = () => apiFetch<ReportRecord[]>("/api/reports");

export const searchReports = (query: string, siteId?: string) =>
  apiFetch<ReportSearchResponse>("/api/reports/search", {
    method: "POST",
    body: JSON.stringify({ query, site_id: siteId, limit: 5 }),
  });

export async function getBackendHealth(): Promise<BackendHealth> {
  try {
    const response = await fetch(`${API_BASE_URL}/health`, {
      cache: "no-store",
      signal: AbortSignal.timeout(3_000),
    });

    if (!response.ok) {
      return {
        connected: false,
        message: `Backend returned HTTP ${response.status}.`,
      };
    }

    const data = (await response.json()) as HealthResponse;
    if (data.status !== "ok" || data.service !== "aerialops-api") {
      return {
        connected: false,
        message: "Backend returned an unexpected health response.",
      };
    }

    return { connected: true, data };
  } catch {
    return {
      connected: false,
      message: "Backend is offline. Start FastAPI on port 8000 and refresh.",
    };
  }
}
