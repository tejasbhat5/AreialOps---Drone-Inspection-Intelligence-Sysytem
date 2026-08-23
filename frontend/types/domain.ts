export type SiteType =
  | "SOLAR_FARM"
  | "WIND_FARM"
  | "RAIL"
  | "BRIDGE"
  | "MINE"
  | "TRANSMISSION"
  | "INDUSTRIAL"
  | "CONSTRUCTION"
  | "OTHER";

export type SiteStatus = "ACTIVE" | "INACTIVE" | "MAINTENANCE" | "ARCHIVED";
export type RiskLevel = "LOW" | "MODERATE" | "HIGH" | "CRITICAL";
export type InspectionStatus =
  "SCHEDULED" | "IN_PROGRESS" | "COMPLETED" | "CANCELLED";
export type AnomalySeverity = RiskLevel;
export type AnomalyStatus =
  "OPEN" | "ACKNOWLEDGED" | "RESOLVED" | "FALSE_POSITIVE";

export type Site = {
  id: string;
  name: string;
  site_type: SiteType;
  location: string;
  latitude: string | number;
  longitude: string | number;
  status: SiteStatus;
  current_risk_score: number;
  current_risk_level: RiskLevel;
  created_at: string;
  updated_at: string;
};

export type SiteDetail = Site & {
  inspection_count: number;
  unresolved_anomaly_count: number;
};

export type Anomaly = {
  id: string;
  site_id: string;
  inspection_id: string;
  title: string;
  description: string;
  severity: AnomalySeverity;
  status: AnomalyStatus;
  resolved_at: string | null;
  created_at: string;
  updated_at: string;
};

export type Inspection = {
  id: string;
  site_id: string;
  inspected_at: string;
  status: InspectionStatus;
  notes: string | null;
  anomalies: Anomaly[];
  created_at: string;
  updated_at: string;
};

export type InspectionCreate = {
  site_id: string;
  inspected_at: string;
  status: InspectionStatus;
  notes: string | null;
  anomalies: Array<{
    title: string;
    description: string;
    severity: AnomalySeverity;
  }>;
};

export type ImageReviewStatus =
  | "NOT_ANALYZED"
  | "PENDING_REVIEW"
  | "APPROVED"
  | "REJECTED";
export type JobStatus = "PENDING" | "PROCESSING" | "COMPLETED" | "FAILED";
export type JobType = "REPORT_INGESTION" | "IMAGE_ANALYSIS";

export type InspectionImage = {
  id: string;
  inspection_id: string;
  original_filename: string;
  content_type: string;
  size_bytes: number;
  review_status: ImageReviewStatus;
  ai_findings: Record<string, unknown> | null;
  created_at: string;
};

export type InspectionReport = {
  id: string;
  inspection_id: string;
  original_filename: string;
  content_type: string;
  size_bytes: number;
  ingestion_status: "NOT_STARTED" | JobStatus;
  created_at: string;
};

export type ProcessingJob = {
  id: string;
  job_type: JobType;
  status: JobStatus;
  report_id: string | null;
  image_id: string | null;
  attempts: number;
  error_code: string | null;
  error_message: string | null;
  started_at: string | null;
  completed_at: string | null;
  created_at: string;
  updated_at: string;
};

export type RiskFactors = {
  formula_version?: string;
  source?: string;
  unresolved_anomaly_count?: number;
  severity_counts?: Record<AnomalySeverity, number>;
  severity_weights?: Record<AnomalySeverity, number>;
  severity_raw_points?: number;
  severity_points?: number;
  severity_cap?: number;
  critical_bonus?: number;
  critical_bonus_weight?: number;
  volume_points?: number;
  volume_points_per_anomaly?: number;
  volume_cap?: number;
  latest_completed_inspection_at?: string | null;
  days_since_completed_inspection?: number | null;
  recency_points?: number;
  recency_bands?: Record<string, number>;
  classification_thresholds?: Record<RiskLevel, [number, number]>;
  score_before_cap?: number;
  score_cap?: number;
};

export type RiskAssessment = {
  id: string;
  site_id: string;
  score: number;
  level: RiskLevel;
  formula_version: string;
  factor_snapshot: RiskFactors;
  calculated_at: string;
};

export type Page<T> = {
  items: T[];
  page: number;
  page_size: number;
  total: number;
  has_next: boolean;
};

export type DashboardSummary = {
  metrics: {
    total_sites: number;
    active_sites: number;
    critical_sites: number;
    inspections_this_month: number;
    unresolved_anomalies: number;
    average_risk_score: number;
  };
  recent_inspections: Inspection[];
  highest_risk_sites: Site[];
  anomaly_counts_by_severity: Record<string, number>;
};

export type SiteCreate = Pick<
  Site,
  "name" | "site_type" | "location" | "latitude" | "longitude" | "status"
>;

export type SiteFilters = {
  query?: string;
  site_type?: SiteType;
  status?: SiteStatus;
  risk_level?: RiskLevel;
  sort?: "name" | "risk_desc" | "created_at_desc";
  page?: number;
};

export type AssistantSite = {
  id: string;
  name: string;
  site_type: SiteType;
  status: SiteStatus;
  location: string;
  latitude: number;
  longitude: number;
  risk_score: number;
  risk_level: RiskLevel;
  unresolved_anomalies: number;
  latest_inspection_at: string | null;
};

export type ToolActivity = {
  tool_name: string;
  label: string;
  status: "COMPLETED" | "FAILED";
  duration_ms: number;
  error_code: string | null;
};

export type AssistantResponse = {
  request_id: string;
  conversation_id: string;
  response_type:
    | "answer"
    | "high_risk_sites"
    | "site_comparison"
    | "inspection_timeline"
    | "anomaly_summary"
    | "risk_explanation"
    | "report_summary"
    | "clarification"
    | "error";
  answer: string;
  data: Record<string, unknown> | null;
  actions: Array<{ type: string; site_id?: string; site_ids: string[] }>;
  tool_activity: ToolActivity[];
  provider: "deterministic-local" | string;
};

export type AssistantCapabilities = {
  active_provider: "openai" | "deterministic-local" | string;
  model: string | null;
  model_configured: boolean;
  deterministic_fallback: boolean;
  max_tool_calls: number;
  max_model_rounds: number;
};

export type ReportRecord = {
  id: string;
  inspection_id: string;
  site_id: string;
  site_name: string;
  original_filename: string;
  ingestion_status: "NOT_STARTED" | JobStatus;
  chunk_count: number;
  created_at: string;
};

export type ReportCitation = {
  report_id: string;
  inspection_id: string;
  site_id: string;
  site_name: string;
  report_filename: string;
  chunk_index: number;
  excerpt: string;
  score: number;
};

export type ReportSearchResponse = {
  query: string;
  citations: ReportCitation[];
  total: number;
};
