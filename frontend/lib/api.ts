export type StageStatus = "completed" | "skipped";

export type DemoStageResult = {
  name: string;
  status: StageStatus;
  duration_ms: number;
};

export type DemoTimelineStage = {
  name: string;
  status: "done" | "running" | "pending";
  progress_percent: number;
};

export type DemoTimelineJob = {
  job_id: string;
  title: string;
  company: string;
  stages: DemoTimelineStage[];
};

export type DemoLogEntry = {
  id: number;
  level: string;
  stage: string;
  message: string;
  created_at: string;
};

export type DemoPipelineResponse = {
  run_id: string;
  jobs_fetched: number;
  jobs_matched: number;
  resumes_generated: number;
  applications_sent: number;
  stage_results: DemoStageResult[];
  job_timelines: DemoTimelineJob[];
  logs: DemoLogEntry[];
};

const API_BASE_URL = process.env.NEXT_PUBLIC_API_BASE_URL ?? "http://localhost:8000";

export async function runDemoPipeline(): Promise<DemoPipelineResponse> {
  const response = await fetch(`${API_BASE_URL}/api/v1/pipeline/run-demo`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    cache: "no-store",
  });

  if (!response.ok) {
    throw new Error(`Pipeline run failed with status ${response.status}`);
  }

  return (await response.json()) as DemoPipelineResponse;
}
