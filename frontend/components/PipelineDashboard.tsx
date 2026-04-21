"use client";

import { useEffect, useState } from "react";

import { DemoPipelineResponse, runDemoPipeline } from "../lib/api";
import { JobTimeline } from "./JobTimeline";
import { LogsPanel } from "./LogsPanel";

const AVAILABLE_MODELS = ["gpt-4.1-mini", "gpt-4o-mini", "claude-3-5-sonnet", "claude-3-7-sonnet", "grok-3-mini", "grok-3"];

export function PipelineDashboard() {
  const [data, setData] = useState<DemoPipelineResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [selectedModel, setSelectedModel] = useState("gpt-4.1-mini");

  useEffect(() => {
    async function load() {
      try {
        setLoading(true);
        setError(null);
        const response = await runDemoPipeline(selectedModel);
        setData(response);
      } catch (err) {
        setError(err instanceof Error ? err.message : "Unknown error");
      } finally {
        setLoading(false);
      }
    }

    void load();
  }, [selectedModel]);

  return (
    <main style={{ padding: 24, fontFamily: "sans-serif" }}>
      <h1>Job Agent Orchestrator</h1>
      <p>Demo execution of ingestion, matching, and resume tailoring pipeline.</p>

      <label style={{ display: "block", marginTop: 12, marginBottom: 8 }}>
        <span style={{ marginRight: 8 }}>LLM model:</span>
        <select value={selectedModel} onChange={(event) => setSelectedModel(event.target.value)}>
          {AVAILABLE_MODELS.map((modelName) => (
            <option key={modelName} value={modelName}>
              {modelName}
            </option>
          ))}
        </select>
      </label>

      {loading && <p>Running demo pipeline…</p>}
      {error && <p style={{ color: "#dc2626" }}>Failed to run pipeline: {error}</p>}

      {data && (
        <>
          <section style={{ display: "grid", gridTemplateColumns: "repeat(4, minmax(0, 1fr))", gap: 12, marginTop: 16 }}>
            <MetricCard label="Jobs fetched" value={data.jobs_fetched} />
            <MetricCard label="Jobs matched" value={data.jobs_matched} />
            <MetricCard label="Resumes generated" value={data.resumes_generated} />
            <MetricCard label="Applications sent" value={data.applications_sent} />
          </section>

          <JobTimeline jobs={data.job_timelines} />
          <LogsPanel logs={data.logs} modelName={data.model_name ?? selectedModel} providerName={data.llm_provider} />
        </>
      )}
    </main>
  );
}

function MetricCard({ label, value }: { label: string; value: number }) {
  return (
    <div style={{ border: "1px solid #e5e7eb", borderRadius: 8, padding: 12 }}>
      <div style={{ color: "#4b5563", fontSize: 13 }}>{label}</div>
      <div style={{ fontSize: 28, fontWeight: 700 }}>{value}</div>
    </div>
  );
}
