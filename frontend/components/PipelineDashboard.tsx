"use client";

import { startTransition, useEffect, useState } from "react";

import {
  ApplicationTrackingItem,
  DemoPipelineResponse,
  EmailStatusResponse,
  fetchApplicationTracking,
  fetchEmailStatus,
  runDemoPipeline,
  runLinkedInDemoPipeline,
} from "../lib/api";
import { JobTimeline } from "./JobTimeline";
import { LogsPanel } from "./LogsPanel";
import { StatusBadge } from "./StatusBadge";

const AVAILABLE_MODELS = ["gpt-4.1-mini", "gpt-4o-mini", "claude-3-5-sonnet", "claude-3-7-sonnet", "grok-3-mini", "grok-3"];

type RunMode = "demo" | "linkedin";

export function PipelineDashboard() {
  const [latestRun, setLatestRun] = useState<DemoPipelineResponse | null>(null);
  const [tracking, setTracking] = useState<ApplicationTrackingItem[]>([]);
  const [emailStatus, setEmailStatus] = useState<EmailStatusResponse | null>(null);
  const [pageLoading, setPageLoading] = useState(true);
  const [runLoading, setRunLoading] = useState(false);
  const [refreshLoading, setRefreshLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [selectedModel, setSelectedModel] = useState("gpt-4.1-mini");
  const [runMode, setRunMode] = useState<RunMode>("demo");
  const [requireHumanApproval, setRequireHumanApproval] = useState(true);
  const [approvedByHuman, setApprovedByHuman] = useState(false);

  useEffect(() => {
    void refreshSupportData(true);
  }, []);

  async function refreshSupportData(initialLoad = false) {
    try {
      if (initialLoad) {
        setPageLoading(true);
      } else {
        setRefreshLoading(true);
      }
      setError(null);

      const [trackingResponse, emailResponse] = await Promise.all([fetchApplicationTracking(), fetchEmailStatus()]);
      startTransition(() => {
        setTracking(trackingResponse.applications);
        setEmailStatus(emailResponse);
      });
    } catch (err) {
      setError(err instanceof Error ? err.message : "Unable to load dashboard state.");
    } finally {
      setPageLoading(false);
      setRefreshLoading(false);
    }
  }

  async function handleRunPipeline() {
    try {
      setRunLoading(true);
      setError(null);

      const runPipeline = runMode === "linkedin" ? runLinkedInDemoPipeline : runDemoPipeline;
      const response = await runPipeline(selectedModel, approvedByHuman, requireHumanApproval);
      const trackingResponse = await fetchApplicationTracking();

      startTransition(() => {
        setLatestRun(response);
        setTracking(trackingResponse.applications);
      });
    } catch (err) {
      setError(err instanceof Error ? err.message : "Unable to run the pipeline.");
    } finally {
      setRunLoading(false);
    }
  }

  return (
    <main className="page-shell">
      <section className="hero">
        <div className="hero-grid">
          <div>
            <div className="eyebrow">Operational view</div>
            <h1>Job applications, with the pipeline visible.</h1>
            <p className="hero-copy">
              Run the demo flow, inspect fit scoring, see whether a human approval gate blocked submission, and keep the
              latest tracking state in one place. The UI stays focused on actions, status, and audit-friendly context.
            </p>
            <div className="hero-points">
              <span className="pill">Ingestion to match</span>
              <span className="pill">Tailored resume history</span>
              <span className="pill">Approval-aware automation</span>
              <span className="pill">Tracking and logs</span>
            </div>
          </div>

          <aside className="control-card">
            <h2>Run a pipeline</h2>
            <p className="control-copy">Choose a source, pick the model, and decide whether the application should wait for approval.</p>

            <div className="form-grid">
              <label className="field">
                <span>Pipeline mode</span>
                <select value={runMode} onChange={(event) => setRunMode(event.target.value as RunMode)}>
                  <option value="demo">Local demo dataset</option>
                  <option value="linkedin">LinkedIn demo ingestion</option>
                </select>
              </label>

              <label className="field">
                <span>Model</span>
                <select value={selectedModel} onChange={(event) => setSelectedModel(event.target.value)}>
                  {AVAILABLE_MODELS.map((modelName) => (
                    <option key={modelName} value={modelName}>
                      {modelName}
                    </option>
                  ))}
                </select>
              </label>

              <label className="field">
                <span>Approval gate</span>
                <select
                  value={requireHumanApproval ? "required" : "not_required"}
                  onChange={(event) => setRequireHumanApproval(event.target.value === "required")}
                >
                  <option value="required">Require approval before apply</option>
                  <option value="not_required">Skip approval for demo run</option>
                </select>
              </label>

              <label className="field">
                <span>Email integration</span>
                <input value={emailStatus?.detail ?? "Loading integration state..."} readOnly />
              </label>
            </div>

            <label className="checkbox-row">
              <input
                type="checkbox"
                checked={approvedByHuman}
                onChange={(event) => setApprovedByHuman(event.target.checked)}
                disabled={!requireHumanApproval}
              />
              <span>
                Mark this run as already approved by a human reviewer.
                {!requireHumanApproval ? " Approval is disabled, so this toggle is ignored for the next run." : ""}
              </span>
            </label>

            <div className="action-row">
              <button className="button button-primary" onClick={handleRunPipeline} disabled={runLoading || pageLoading}>
                {runLoading ? "Running pipeline..." : "Run pipeline"}
              </button>
              <button className="button button-secondary" onClick={() => void refreshSupportData()} disabled={refreshLoading || pageLoading}>
                {refreshLoading ? "Refreshing..." : "Refresh tracking"}
              </button>
            </div>

            <div className="status-row">
              <StatusBadge status={latestRun?.status ?? "PENDING"} label={latestRun ? "Latest run" : "Waiting"} />
              <span className="muted">{latestRun ? `Run ${latestRun.run_id}` : "No pipeline run yet in this session."}</span>
            </div>

            {error ? <div className="notice notice-error">{error}</div> : null}
            {pageLoading ? <div className="notice notice-info">Loading tracking and integration state...</div> : null}
          </aside>
        </div>
      </section>

      <section className="dashboard-grid">
        <div className="span-12 metric-grid">
          <MetricCard
            label="Jobs ingested"
            value={latestRun?.jobs_ingested ?? tracking.length}
            subtext={latestRun ? "Current pipeline run output" : "Tracking list fallback"}
          />
          <MetricCard
            label="Matches found"
            value={latestRun?.matches_found ?? 0}
            subtext={latestRun ? `Dataset ${latestRun.dataset_version ?? "n/a"}` : "Run a pipeline to evaluate matches"}
          />
          <MetricCard
            label="ATS score"
            value={latestRun ? Math.round(latestRun.ats_score) : 0}
            subtext={latestRun ? "Compatibility score for the top target" : "Awaiting latest run"}
          />
          <MetricCard
            label="Retries used"
            value={latestRun?.retries_used ?? 0}
            subtext={latestRun?.duplicate_prevented ? "Duplicate prevention triggered" : "Recovery attempts during apply"}
          />
        </div>

        <section className="panel span-8">
          <div className="panel-header">
            <div>
              <h2 className="panel-title">Latest orchestration result</h2>
              <p className="panel-copy">The last pipeline run surfaces status, provider selection, approval outcome, and resume generation state.</p>
            </div>
            <StatusBadge status={latestRun?.status ?? "PENDING"} />
          </div>

          {latestRun ? (
            <>
              <div className="split-list">
                <div className="card-item">
                  <h3 className="card-title">Execution summary</h3>
                  <div className="inline-meta">
                    <span>Model: {latestRun.model_name}</span>
                    <span>Provider: {latestRun.llm_provider ?? "unknown"}</span>
                    <span>Resume: {latestRun.resume_generated ? "generated" : "not generated"}</span>
                  </div>
                  <div className="inline-meta">
                    <span>Approval gate: {latestRun.waiting_for_human_approval ? "waiting" : "cleared"}</span>
                    <span>Email integration: {latestRun.email_integration_configured ? "connected" : "placeholder"}</span>
                  </div>
                </div>

                <div className="card-item">
                  <h3 className="card-title">Risk and control notes</h3>
                  <div className="inline-meta">
                    <span>Duplicate prevented: {latestRun.duplicate_prevented ? "yes" : "no"}</span>
                    <span>Tracking record: {latestRun.tracking_item ? latestRun.tracking_item.application_id : "not created"}</span>
                  </div>
                  <div className="inline-meta">
                    <span>Run id: {latestRun.run_id}</span>
                  </div>
                </div>
              </div>

              <div className="split-list">
                <div className="card-item">
                  <h3 className="card-title">Matched skills</h3>
                  <div className="tag-cluster">
                    {latestRun.skill_gap.matched_skills.length ? (
                      latestRun.skill_gap.matched_skills.map((skill) => (
                        <span key={skill} className="tag">
                          {skill}
                        </span>
                      ))
                    ) : (
                      <span className="muted">No matched skills reported.</span>
                    )}
                  </div>
                </div>

                <div className="card-item">
                  <h3 className="card-title">Missing or weak signals</h3>
                  <div className="tag-cluster">
                    {latestRun.skill_gap.missing_skills.length ? (
                      latestRun.skill_gap.missing_skills.map((skill) => (
                        <span key={skill} className="tag tag-missing">
                          {skill}
                        </span>
                      ))
                    ) : (
                      <span className="muted">No obvious skill gaps for the selected job.</span>
                    )}
                  </div>
                </div>
              </div>
            </>
          ) : (
            <div className="empty-state">Run a pipeline to populate execution results, skill analysis, and provider details.</div>
          )}
        </section>

        <section className="panel span-4">
          <div className="panel-header">
            <div>
              <h2 className="panel-title">Resume history</h2>
              <p className="panel-copy">Each run keeps the base resume and the tailored revision visible.</p>
            </div>
          </div>

          {latestRun?.resume_versions.length ? (
            <div className="list-grid">
              {latestRun.resume_versions.map((version) => (
                <div className="card-item" key={`${version.resume_id}-${version.version}`}>
                  <h3 className="card-title">Version {version.version}</h3>
                  <div className="card-meta">
                    <span>{new Date(version.created_at).toLocaleString()}</span>
                  </div>
                  <p className="muted">{version.summary}</p>
                </div>
              ))}
            </div>
          ) : (
            <div className="empty-state">No resume revisions yet.</div>
          )}
        </section>

        <section className="panel span-6">
          <div className="panel-header">
            <div>
              <h2 className="panel-title">Integration state</h2>
              <p className="panel-copy">Operational context for connected services and automation prerequisites.</p>
            </div>
          </div>
          <div className="list-grid">
            <div className="card-item">
              <h3 className="card-title">Email ingestion</h3>
              <div className="inline-meta">
                <span>Provider: {emailStatus?.provider ?? "gmail"}</span>
                <span>Mode: {emailStatus?.mode ?? "loading"}</span>
              </div>
              <p className="muted">{emailStatus?.detail ?? "Loading email integration state..."}</p>
            </div>
            <div className="card-item">
              <h3 className="card-title">User action</h3>
              <p className="muted">
                Use the approval gate for truthful, reviewable workflows. The demo only proceeds automatically when that gate is turned off or explicitly approved.
              </p>
            </div>
          </div>
        </section>

        <section className="panel span-6">
          <div className="panel-header">
            <div>
              <h2 className="panel-title">Run guidance</h2>
              <p className="panel-copy">A minimal workflow so the app is easy to operate without reading code.</p>
            </div>
          </div>
          <div className="list-grid">
            <div className="card-item">
              <h3 className="card-title">1. Select source and model</h3>
              <p className="muted">Choose the local dataset or LinkedIn demo, then pick the LLM route you want to test.</p>
            </div>
            <div className="card-item">
              <h3 className="card-title">2. Set approval behavior</h3>
              <p className="muted">Keep approval required for a realistic review gate, or disable it when you only want to exercise the pipeline.</p>
            </div>
            <div className="card-item">
              <h3 className="card-title">3. Inspect outcome</h3>
              <p className="muted">Use the cards below to review ATS score, resume revisions, tracking state, retries, and logs.</p>
            </div>
          </div>
        </section>

        <div className="span-12">
          <JobTimeline jobs={tracking} />
        </div>

        <div className="span-12">
          <LogsPanel logs={latestRun?.logs ?? []} modelName={latestRun?.model_name ?? selectedModel} providerName={latestRun?.llm_provider} />
        </div>
      </section>
    </main>
  );
}

function MetricCard({ label, value, subtext }: { label: string; value: number; subtext: string }) {
  return (
    <div className="metric-card">
      <div className="metric-label">{label}</div>
      <div className="metric-value">{value}</div>
      <div className="metric-subtext">{subtext}</div>
    </div>
  );
}
