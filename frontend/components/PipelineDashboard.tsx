"use client";

import { useEffect, useState } from "react";

import { ApplicationTrackingItem, DemoPipelineResponse, EmailStatusResponse, fetchApplicationTracking, fetchEmailStatus, runDemoPipeline } from "../lib/api";
import { JobTimeline } from "./JobTimeline";
import { LogsPanel } from "./LogsPanel";

const AVAILABLE_MODELS = ["gpt-4.1-mini", "gpt-4o-mini", "claude-3-5-sonnet", "claude-3-7-sonnet", "grok-3-mini", "grok-3"];

export function PipelineDashboard() {
  const [data, setData] = useState<DemoPipelineResponse | null>(null);
  const [tracking, setTracking] = useState<ApplicationTrackingItem[]>([]);
  const [emailStatus, setEmailStatus] = useState<EmailStatusResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [selectedModel, setSelectedModel] = useState("gpt-4.1-mini");
  const [approvedByHuman, setApprovedByHuman] = useState(false);

  useEffect(() => {
    async function load() {
      try {
        setLoading(true);
        setError(null);
        const [pipelineResponse, trackingResponse, emailResponse] = await Promise.all([
          runDemoPipeline(selectedModel, approvedByHuman),
          fetchApplicationTracking(),
          fetchEmailStatus(),
        ]);
        setData(pipelineResponse);
        setTracking(trackingResponse.applications);
        setEmailStatus(emailResponse);
      } catch (err) {
        setError(err instanceof Error ? err.message : "Unknown error");
      } finally {
        setLoading(false);
      }
    }

    void load();
  }, [selectedModel, approvedByHuman]);

  return (
    <main style={{ padding: 24, fontFamily: "sans-serif" }}>
      <h1>Job Agent Orchestrator</h1>
      <p>Demo execution with ATS scoring, approvals, retries, duplicate prevention, and tracking.</p>

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

      <label style={{ display: "block", marginBottom: 12 }}>
        <input type="checkbox" checked={approvedByHuman} onChange={(event) => setApprovedByHuman(event.target.checked)} /> Human approved apply
      </label>

      {loading && <p>Running demo pipeline…</p>}
      {error && <p style={{ color: "#dc2626" }}>Failed to run pipeline: {error}</p>}

      {data && (
        <>
          <section style={{ display: "grid", gridTemplateColumns: "repeat(4, minmax(0, 1fr))", gap: 12, marginTop: 16 }}>
            <MetricCard label="Jobs ingested" value={data.jobs_ingested} />
            <MetricCard label="Matches" value={data.matches_found} />
            <MetricCard label="ATS score" value={data.ats_score} />
            <MetricCard label="Retries used" value={data.retries_used} />
          </section>

          <section style={{ marginTop: 20 }}>
            <h2>Skill gap detection</h2>
            <p>Matched: {data.skill_gap.matched_skills.join(", ") || "none"}</p>
            <p>Missing: {data.skill_gap.missing_skills.join(", ") || "none"}</p>
          </section>

          <section style={{ marginTop: 20 }}>
            <h2>Resume version history</h2>
            {data.resume_versions.map((version) => (
              <div key={`${version.resume_id}-${version.version}`}>v{version.version}: {version.summary}</div>
            ))}
          </section>

          <section style={{ marginTop: 20 }}>
            <h2>Email integration backend</h2>
            <p>{emailStatus?.detail ?? "Loading email status..."}</p>
          </section>

          <JobTimeline jobs={tracking} />
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
