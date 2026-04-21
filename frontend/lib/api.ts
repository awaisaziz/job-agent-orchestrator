export type PipelineStatus = "PENDING" | "PROCESSING" | "COMPLETED" | "FAILED";

export type SkillGapReport = {
  matched_skills: string[];
  missing_skills: string[];
};

export type ResumeVersionRecord = {
  resume_id: string;
  version: number;
  created_at: string;
  summary: string;
};

export type ApplicationTrackingItem = {
  application_id: string;
  job_title: string;
  company: string;
  status: PipelineStatus;
  ats_score: number;
  retries_used: number;
  duplicate_blocked: boolean;
  waiting_for_human_approval: boolean;
  created_at: string;
};

export type DemoPipelineResponse = {
  run_id: string;
  status: PipelineStatus;
  jobs_ingested: number;
  matches_found: number;
  resume_generated: boolean;
  model_name: string;
  llm_provider?: string | null;
  dataset_version?: string | null;
  logs: string[];
  ats_score: number;
  skill_gap: SkillGapReport;
  waiting_for_human_approval: boolean;
  duplicate_prevented: boolean;
  retries_used: number;
  tracking_item?: ApplicationTrackingItem | null;
  resume_versions: ResumeVersionRecord[];
  email_integration_configured: boolean;
};

export type ApplicationTrackingResponse = {
  applications: ApplicationTrackingItem[];
};

export type EmailStatusResponse = {
  provider: string;
  configured: boolean;
  mode: string;
  detail: string;
};

const API_BASE_URL = process.env.NEXT_PUBLIC_API_BASE_URL ?? "http://localhost:8000";

export async function runDemoPipeline(modelName: string, approvedByHuman: boolean): Promise<DemoPipelineResponse> {
  const response = await fetch(`${API_BASE_URL}/api/v1/pipeline/run-demo`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ model_name: modelName, require_human_approval: true, approved_by_human: approvedByHuman }),
    cache: "no-store",
  });

  if (!response.ok) {
    throw new Error(`Pipeline run failed with status ${response.status}`);
  }

  return (await response.json()) as DemoPipelineResponse;
}

export async function fetchApplicationTracking(): Promise<ApplicationTrackingResponse> {
  const response = await fetch(`${API_BASE_URL}/api/v1/pipeline/tracking/applications`, { cache: "no-store" });
  if (!response.ok) {
    throw new Error(`Tracking request failed with status ${response.status}`);
  }
  return (await response.json()) as ApplicationTrackingResponse;
}

export async function fetchEmailStatus(): Promise<EmailStatusResponse> {
  const response = await fetch(`${API_BASE_URL}/api/v1/pipeline/integrations/email/status`, { cache: "no-store" });
  if (!response.ok) {
    throw new Error(`Email status request failed with status ${response.status}`);
  }
  return (await response.json()) as EmailStatusResponse;
}
