export type PipelineStatus = "PENDING" | "PROCESSING" | "COMPLETED" | "FAILED";
export type WorkflowStatus =
  | "saved"
  | "fetched"
  | "normalized"
  | "matched"
  | "tailored"
  | "pending_approval"
  | "approved"
  | "applied"
  | "failed"
  | "rejected"
  | "interview"
  | "closed";

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
  last_synced_at?: string | null;
};

export type ResumeArtifact = {
  resume_id: number;
  version: number;
  kind: string;
  artifact_path?: string | null;
  source_filename?: string | null;
  created_at: string;
};

export type ProfileSummary = {
  user_id: number;
  full_name: string;
  email: string;
  skills: string[];
  target_locations: string[];
  base_resume: ResumeArtifact;
  parsed_summary: string;
};

export type ProfileIntakeRequest = {
  email: string;
  full_name?: string;
  location?: string;
  resume_filename: string;
  resume_text: string;
};

export type ProfileIntakeResponse = {
  profile: ProfileSummary;
};

export type SearchResultItem = {
  result_id: number;
  source: string;
  title: string;
  company: string;
  snippet: string;
  description: string;
  location?: string | null;
  apply_url?: string | null;
  source_url?: string | null;
  skills: string[];
  fit_score?: number | null;
  ats_score?: number | null;
  status: WorkflowStatus;
  selected: boolean;
  url_verified: boolean;
  url_status?: string | null;
  final_apply_url?: string | null;
};

export type JobSearchResponse = {
  search_id: number;
  status: WorkflowStatus;
  position: string;
  location?: string | null;
  results: SearchResultItem[];
};

export type MatchResultItem = {
  result_id: number;
  fit_score: number;
  matched_skills: string[];
  missing_skills: string[];
};

export type MatchJobsResponse = {
  search_id: number;
  results: MatchResultItem[];
};

export type ApplicationQueueItem = {
  application_id: number;
  search_result_id: number;
  company: string;
  title: string;
  source: string;
  fit_score?: number | null;
  ats_score?: number | null;
  status: WorkflowStatus;
  waiting_for_human_approval: boolean;
  duplicate_blocked: boolean;
  retries_used: number;
  apply_url?: string | null;
  tailored_resume?: ResumeArtifact | null;
  updated_at: string;
};

export type PrepareApplicationsResponse = {
  search_id: number;
  applications: ApplicationQueueItem[];
};

export type TailorResumeResult = {
  application_id: number;
  resume_version_id: number;
  ats_score: number;
  matched_skills: string[];
  missing_skills: string[];
  artifact_path: string;
  status: WorkflowStatus;
};

export type TailorResumeResponse = {
  results: TailorResumeResult[];
};

export type SubmitApplicationResult = {
  application_id: number;
  status: WorkflowStatus;
  attempted_actions: string[];
  failure_reason?: string | null;
};

export type SubmitApplicationsResponse = {
  results: SubmitApplicationResult[];
};

export type ApplicationListResponse = {
  applications: ApplicationQueueItem[];
};

export type SearchWorkspaceResponse = {
  search_id: number;
  status: WorkflowStatus;
  position: string;
  location?: string | null;
  profile: ProfileSummary;
  results: SearchResultItem[];
  applications: ApplicationQueueItem[];
};

export type EmailSyncResponse = {
  processed_messages: number;
  inserted_events: number;
  rate_limited: boolean;
  detail: string;
  last_synced_at?: string | null;
};

export type FrontendConfigResponse = {
  default_model: string;
  enabled_models: string[];
  environment: string;
};

const API_BASE_URL = process.env.NEXT_PUBLIC_API_BASE_URL ?? "http://localhost:8000";

async function readJsonOrThrow<T>(response: Response, fallbackMessage: string): Promise<T> {
  if (!response.ok) {
    throw new Error(`${fallbackMessage} (${response.status})`);
  }

  return (await response.json()) as T;
}

export async function runDemoPipeline(
  modelName: string,
  approvedByHuman: boolean,
  requireHumanApproval: boolean,
): Promise<DemoPipelineResponse> {
  const response = await fetch(`${API_BASE_URL}/api/v1/pipeline/run-demo`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      model_name: modelName,
      require_human_approval: requireHumanApproval,
      approved_by_human: approvedByHuman,
    }),
    cache: "no-store",
  });

  return readJsonOrThrow<DemoPipelineResponse>(response, "Pipeline run failed");
}

export async function runLinkedInDemoPipeline(
  modelName: string,
  approvedByHuman: boolean,
  requireHumanApproval: boolean,
): Promise<DemoPipelineResponse> {
  const response = await fetch(`${API_BASE_URL}/api/v1/pipeline/run-linkedin-demo`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      model_name: modelName,
      require_human_approval: requireHumanApproval,
      approved_by_human: approvedByHuman,
    }),
    cache: "no-store",
  });

  return readJsonOrThrow<DemoPipelineResponse>(response, "LinkedIn demo run failed");
}

export async function fetchApplicationTracking(): Promise<ApplicationTrackingResponse> {
  const response = await fetch(`${API_BASE_URL}/api/v1/pipeline/tracking/applications`, { cache: "no-store" });
  return readJsonOrThrow<ApplicationTrackingResponse>(response, "Tracking request failed");
}

export async function fetchEmailStatus(): Promise<EmailStatusResponse> {
  const response = await fetch(`${API_BASE_URL}/api/v1/pipeline/integrations/email/status`, { cache: "no-store" });
  return readJsonOrThrow<EmailStatusResponse>(response, "Email status request failed");
}

export async function intakeProfile(payload: ProfileIntakeRequest): Promise<ProfileIntakeResponse> {
  const response = await fetch(`${API_BASE_URL}/api/v1/profile/intake`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
    cache: "no-store",
  });

  return readJsonOrThrow<ProfileIntakeResponse>(response, "Profile intake failed");
}

export async function searchJobs(payload: {
  user_id: number;
  position: string;
  location?: string;
  email: string;
}): Promise<JobSearchResponse> {
  const response = await fetch(`${API_BASE_URL}/api/v1/search/jobs`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
    cache: "no-store",
  });

  return readJsonOrThrow<JobSearchResponse>(response, "Job search failed");
}

export async function matchJobs(searchId: number): Promise<MatchJobsResponse> {
  const response = await fetch(`${API_BASE_URL}/api/v1/match/jobs`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ search_id: searchId }),
    cache: "no-store",
  });

  return readJsonOrThrow<MatchJobsResponse>(response, "Job matching failed");
}

export async function fetchSearchWorkspace(searchId: number): Promise<SearchWorkspaceResponse> {
  const response = await fetch(`${API_BASE_URL}/api/v1/jobs/searches/${searchId}`, { cache: "no-store" });
  return readJsonOrThrow<SearchWorkspaceResponse>(response, "Search workspace request failed");
}

export async function prepareApplications(searchId: number, resultIds: number[]): Promise<PrepareApplicationsResponse> {
  const response = await fetch(`${API_BASE_URL}/api/v1/applications/prepare`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ search_id: searchId, result_ids: resultIds }),
    cache: "no-store",
  });

  return readJsonOrThrow<PrepareApplicationsResponse>(response, "Preparing selected jobs failed");
}

export async function tailorApplications(applicationIds: number[], modelName: string): Promise<TailorResumeResponse> {
  const response = await fetch(`${API_BASE_URL}/api/v1/resumes/tailor`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ application_ids: applicationIds, model_name: modelName }),
    cache: "no-store",
  });

  return readJsonOrThrow<TailorResumeResponse>(response, "Resume tailoring failed");
}

export async function approveApplications(applicationIds: number[]): Promise<PrepareApplicationsResponse> {
  const response = await fetch(`${API_BASE_URL}/api/v1/applications/approve`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ application_ids: applicationIds }),
    cache: "no-store",
  });

  return readJsonOrThrow<PrepareApplicationsResponse>(response, "Application approval failed");
}

export async function submitApplications(applicationIds: number[]): Promise<SubmitApplicationsResponse> {
  const response = await fetch(`${API_BASE_URL}/api/v1/applications/submit`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ application_ids: applicationIds }),
    cache: "no-store",
  });

  return readJsonOrThrow<SubmitApplicationsResponse>(response, "Application submission failed");
}

export async function fetchApplications(userId?: number): Promise<ApplicationListResponse> {
  const url = new URL(`${API_BASE_URL}/api/v1/applications`);
  if (typeof userId === "number") {
    url.searchParams.set("user_id", String(userId));
  }
  const response = await fetch(url, { cache: "no-store" });
  return readJsonOrThrow<ApplicationListResponse>(response, "Application list request failed");
}

export async function fetchWorkflowEmailStatus(userId?: number): Promise<EmailStatusResponse> {
  const url = new URL(`${API_BASE_URL}/api/v1/integrations/email/status`);
  if (typeof userId === "number") {
    url.searchParams.set("user_id", String(userId));
  }
  const response = await fetch(url, { cache: "no-store" });
  return readJsonOrThrow<EmailStatusResponse>(response, "Workflow email status request failed");
}

export async function syncWorkflowEmail(userId: number): Promise<EmailSyncResponse> {
  const response = await fetch(`${API_BASE_URL}/api/v1/integrations/email/sync`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ user_id: userId }),
    cache: "no-store",
  });

  return readJsonOrThrow<EmailSyncResponse>(response, "Email sync failed");
}

export async function fetchFrontendConfig(): Promise<FrontendConfigResponse> {
  const response = await fetch(`${API_BASE_URL}/api/v1/config/frontend`, { cache: "no-store" });
  return readJsonOrThrow<FrontendConfigResponse>(response, "Frontend config request failed");
}
