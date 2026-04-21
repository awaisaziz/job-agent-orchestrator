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
  model_name?: string;
  llm_provider?: string | null;
};

const API_BASE_URL = process.env.NEXT_PUBLIC_API_BASE_URL ?? "http://localhost:8000";

function mapPipelineErrorMessage(rawMessage: string, modelName: string): string {
  const message = rawMessage.toLowerCase();

  if (message.includes("api_key") && message.includes("not configured")) {
    return `The selected model (${modelName}) needs a provider API key that is not configured. Add the provider key in backend environment variables and retry.`;
  }

  return rawMessage;
}

export async function runDemoPipeline(modelName: string): Promise<DemoPipelineResponse> {
  const response = await fetch(`${API_BASE_URL}/api/v1/pipeline/run-demo`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ model_name: modelName }),
    cache: "no-store",
  });

  if (!response.ok) {
    let errorMessage = `Pipeline run failed with status ${response.status}`;

    try {
      const errorBody = (await response.json()) as { detail?: string };
      if (errorBody.detail) {
        errorMessage = mapPipelineErrorMessage(errorBody.detail, modelName);
      }
    } catch {
      // Ignore JSON parsing issues and keep default error message.
    }

    throw new Error(errorMessage);
  }

  return (await response.json()) as DemoPipelineResponse;
}
