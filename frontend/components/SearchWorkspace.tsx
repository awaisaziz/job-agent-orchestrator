"use client";

import Link from "next/link";
import { useEffect, useMemo, useState, useTransition } from "react";

import {
  ApplicationQueueItem,
  EmailStatusResponse,
  FrontendConfigResponse,
  SearchResultItem,
  SearchWorkspaceResponse,
  approveApplications,
  fetchFrontendConfig,
  fetchSearchWorkspace,
  fetchWorkflowEmailStatus,
  prepareApplications,
  submitApplications,
  syncWorkflowEmail,
  tailorApplications,
} from "../lib/api";

type WorkspaceProps = {
  searchId: number;
};

export function SearchWorkspace({ searchId }: WorkspaceProps) {
  const [workspace, setWorkspace] = useState<SearchWorkspaceResponse | null>(null);
  const [emailStatus, setEmailStatus] = useState<EmailStatusResponse | null>(null);
  const [frontendConfig, setFrontendConfig] = useState<FrontendConfigResponse | null>(null);
  const [selectedResultIds, setSelectedResultIds] = useState<number[]>([]);
  const [sourceFilter, setSourceFilter] = useState<string>("all");
  const [statusFilter, setStatusFilter] = useState<string>("all");
  const [selectedModel, setSelectedModel] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);
  const [pendingAction, startTransition] = useTransition();

  useEffect(() => {
    void refreshWorkspace();
  }, [searchId]);

  async function refreshWorkspace() {
    try {
      setLoading(true);
      setError(null);
      const workspaceResponse = await fetchSearchWorkspace(searchId);
      const [emailResponse, configResponse] = await Promise.all([
        fetchWorkflowEmailStatus(workspaceResponse.profile.user_id),
        fetchFrontendConfig(),
      ]);
      setWorkspace(workspaceResponse);
      setEmailStatus(emailResponse);
      setFrontendConfig(configResponse);
      setSelectedModel((current) => current || configResponse.default_model);
      setSelectedResultIds((current) => {
        const next = current.filter((id) => workspaceResponse.results.some((item) => item.result_id === id));
        return next.length ? next : workspaceResponse.results.slice(0, 2).map((item) => item.result_id);
      });
    } catch (err) {
      setError(err instanceof Error ? err.message : "Unable to load the search workspace.");
    } finally {
      setLoading(false);
    }
  }

  const visibleResults = useMemo(() => {
    if (!workspace) {
      return [];
    }
    return workspace.results.filter((item) => {
      const sourceMatch = sourceFilter === "all" || item.source === sourceFilter;
      const statusMatch = statusFilter === "all" || item.status === statusFilter;
      return sourceMatch && statusMatch;
    });
  }, [workspace, sourceFilter, statusFilter]);

  const availableSources = useMemo(
    () => (workspace ? Array.from(new Set(workspace.results.map((item) => item.source))).sort() : []),
    [workspace],
  );

  const selectedApplications = useMemo(() => {
    if (!workspace) {
      return [];
    }
    return workspace.applications.filter((application) => selectedResultIds.includes(application.search_result_id));
  }, [workspace, selectedResultIds]);

  async function runAction(action: () => Promise<void>) {
    startTransition(() => {
      void (async () => {
        try {
          setError(null);
          await action();
          await refreshWorkspace();
        } catch (err) {
          setError(err instanceof Error ? err.message : "Workflow action failed.");
        }
      })();
    });
  }

  function toggleResult(resultId: number) {
    setSelectedResultIds((current) =>
      current.includes(resultId) ? current.filter((id) => id !== resultId) : [...current, resultId],
    );
  }

  function selectAllResults() {
    if (!workspace) {
      return;
    }
    setSelectedResultIds(workspace.results.map((item) => item.result_id));
  }

  if (loading && !workspace) {
    return <main className="page-shell"><div className="empty-state">Loading workspace...</div></main>;
  }

  if (!workspace) {
    return <main className="page-shell"><div className="notice notice-error">{error ?? "Search workspace is unavailable."}</div></main>;
  }

  const uniqueProfileSkills = Array.from(new Set(workspace.profile.skills.map((skill) => skill.trim()).filter(Boolean)));

  return (
    <main className="page-shell">
      <section className="hero">
        <div className="hero-grid">
          <div>
            <div className="eyebrow">Search workspace</div>
            <h1>{workspace.position} opportunities, matched and queued.</h1>
            <p className="hero-copy">
              {frontendConfig?.job_search_mode === "jsearch"
                ? "Review real job listings pulled from JSearch (Google for Jobs), select the roles you want, then drive them through tailoring, approval, and submission. All links are verified."
                : "Review real jobs found by searching public job boards (Remotive, Arbeitnow, RemoteOK), select the roles you want, then drive them through tailoring, approval, and apply."}
            </p>
            <div className="hero-points">
              <span className="pill">Profile: {workspace.profile.full_name}</span>
              <span className="pill">Jobs found: {workspace.results.length}</span>
              <span className="pill">Queued: {workspace.applications.length}</span>
              <span className="pill">Email: {workspace.profile.email}</span>
              {workspace.profile.phone ? <span className="pill">Phone: {workspace.profile.phone}</span> : null}
              <span className="pill">Default model: {frontendConfig?.default_model ?? "Loading..."}</span>
              {frontendConfig ? (
                <span className="pill">{frontendConfig.job_search_mode === "jsearch" ? "JSearch" : "Web search"}</span>
              ) : null}
            </div>
          </div>

          <aside className="control-card">
            <h2>Workflow controls</h2>
            <p className="control-copy">Use the selected jobs as the working set for preparation, tailoring, approval, and apply.</p>
            <div className="form-grid">
              <label className="field">
                <span>Source filter</span>
                <select value={sourceFilter} onChange={(event) => setSourceFilter(event.target.value)}>
                  <option value="all">All sources</option>
                  {availableSources.map((source) => (
                    <option key={source} value={source}>
                      {formatSourceLabel(source)}
                    </option>
                  ))}
                </select>
              </label>
              <label className="field">
                <span>Status filter</span>
                <select value={statusFilter} onChange={(event) => setStatusFilter(event.target.value)}>
                  <option value="all">All statuses</option>
                  <option value="matched">Matched</option>
                  <option value="tailored">Tailored</option>
                  <option value="approved">Approved</option>
                  <option value="applied">Applied</option>
                  <option value="failed">Failed</option>
                </select>
              </label>
              <label className="field">
                <span>Tailoring model</span>
                <select value={selectedModel} onChange={(event) => setSelectedModel(event.target.value)}>
                  {(frontendConfig?.enabled_models ?? []).map((model) => (
                    <option key={model} value={model}>
                      {model}
                    </option>
                  ))}
                </select>
              </label>
              <label className="field">
                <span>Email sync</span>
                <input
                  readOnly
                  value={emailStatus ? `${emailStatus.mode}${emailStatus.last_synced_at ? ` | ${new Date(emailStatus.last_synced_at).toLocaleString()}` : ""}` : "Loading"}
                />
              </label>
            </div>

            <div className="action-row">
              <button className="button button-secondary" onClick={selectAllResults}>
                Select all
              </button>
              <button className="button button-secondary" onClick={() => setSelectedResultIds(visibleResults.map((item) => item.result_id))}>
                Select visible
              </button>
              <button className="button button-secondary" onClick={() => setSelectedResultIds([])}>
                Clear selection
              </button>
              <button className="button button-ghost" onClick={() => void refreshWorkspace()} disabled={pendingAction}>
                Refresh
              </button>
            </div>

            <div className="workflow-actions">
              <button
                className="button button-primary"
                disabled={pendingAction || selectedResultIds.length === 0}
                onClick={() => runAction(() => prepareApplications(workspace.search_id, selectedResultIds).then(() => undefined))}
              >
                {pendingAction ? "Working..." : "Prepare selected"}
              </button>
              <button
                className="button button-primary"
                disabled={pendingAction || selectedApplications.length === 0}
                onClick={() =>
                  runAction(() => tailorApplications(selectedApplications.map((item) => item.application_id), selectedModel).then(() => undefined))
                }
              >
                Tailor selected
              </button>
              <button
                className="button button-primary"
                disabled={pendingAction || selectedApplications.length === 0}
                onClick={() => runAction(() => approveApplications(selectedApplications.map((item) => item.application_id)).then(() => undefined))}
              >
                Approve selected
              </button>
              <button
                className="button button-primary"
                disabled={pendingAction || selectedApplications.length === 0}
                onClick={() => runAction(() => submitApplications(selectedApplications.map((item) => item.application_id)).then(() => undefined))}
              >
                Submit selected
              </button>
              <button
                className="button button-secondary"
                disabled={pendingAction}
                onClick={() => runAction(() => syncWorkflowEmail(workspace.profile.user_id).then(() => undefined))}
              >
                Sync inbox status
              </button>
            </div>

            {error ? <div className="notice notice-error">{error}</div> : null}
          </aside>
        </div>
      </section>

      <section className="dashboard-grid">
        <div className="span-12 metric-grid">
          <MetricCard label="Matches" value={workspace.results.length} subtext="Unified multi-source result set" />
          <MetricCard label="Selected" value={selectedResultIds.length} subtext="Jobs in the current working set" />
          <MetricCard label="Prepared" value={workspace.applications.length} subtext="Applications currently tracked" />
          <MetricCard
            label="Applied"
            value={workspace.applications.filter((item) => item.status === "applied").length}
            subtext="Submitted jobs stored locally"
          />
        </div>

        <section className="panel span-4">
          <div className="panel-header">
            <div>
              <h2 className="panel-title">Profile intake</h2>
              <p className="panel-copy">Uploaded resume remains the source of truth for all tailoring and scoring.</p>
            </div>
          </div>
          <div className="list-grid">
            <div className="card-item">
              <h3 className="card-title">{workspace.profile.full_name}</h3>
              <div className="card-meta">
                <span>{workspace.profile.email}</span>
                {workspace.profile.phone ? <span>{workspace.profile.phone}</span> : null}
                <span>{workspace.profile.base_resume.source_filename ?? "resume upload"}</span>
              </div>
              <p className="muted">{workspace.profile.parsed_summary}</p>
              <div className="tag-cluster">
                {uniqueProfileSkills.map((skill, index) => (
                  <span key={`profile-${skill}-${index}`} className="tag">
                    {skill}
                  </span>
                ))}
              </div>
            </div>
            <div className="card-item">
              <h3 className="card-title">Email tracking</h3>
              <p className="muted">{emailStatus?.detail ?? "Loading inbox integration state..."}</p>
            </div>
          </div>
        </section>

        <section className="panel span-8">
          <div className="panel-header">
            <div>
              <h2 className="panel-title">Relevant jobs</h2>
              <p className="panel-copy">
                Search expands the requested title with OR-style related roles so you also see similar jobs, not only exact-title matches.
                Fit scores appear after backend matching.
              </p>
            </div>
          </div>
          <div className="results-grid">
            {visibleResults.map((job) => (
              <JobCard key={job.result_id} item={job} selected={selectedResultIds.includes(job.result_id)} onToggle={toggleResult} />
            ))}
          </div>
        </section>

        <section className="panel span-12">
          <div className="panel-header">
            <div>
              <h2 className="panel-title">Application workspace</h2>
              <p className="panel-copy">Prepared jobs stay visible with approval state, ATS score, retries, and generated PDF artifact path.</p>
            </div>
          </div>
          {workspace.applications.length ? (
            <div className="workspace-table">
              {workspace.applications.map((item) => (
                <ApplicationCard key={item.application_id} item={item} selected={selectedResultIds.includes(item.search_result_id)} />
              ))}
            </div>
          ) : (
            <div className="empty-state">Prepare selected jobs to start the tailoring and approval workflow.</div>
          )}
        </section>

        <section className="panel span-12">
          <div className="panel-header">
            <div>
              <h2 className="panel-title">Next search</h2>
              <p className="panel-copy">Start a different role search without losing this workspace.</p>
            </div>
            <Link className="button button-secondary" href="/">
              Back to landing page
            </Link>
          </div>
        </section>
      </section>
    </main>
  );
}

const SOURCE_LABELS: Record<string, string> = {
  jsearch: "JSearch (Google Jobs)",
  remotive: "Remotive",
  arbeitnow: "Arbeitnow",
  remoteok: "RemoteOK",
  linkedin: "LinkedIn",
  indeed: "Indeed",
  company_site: "Company site",
};

function formatSourceLabel(source: string): string {
  return SOURCE_LABELS[source] ?? source.replace(/_/g, " ").replace(/\b\w/g, (c) => c.toUpperCase());
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

function JobCard({
  item,
  selected,
  onToggle,
}: {
  item: SearchResultItem;
  selected: boolean;
  onToggle: (resultId: number) => void;
}) {
  const uniqueSkills = Array.from(new Set(item.skills.map((skill) => skill.trim()).filter(Boolean)));

  return (
    <article className={`result-card ${selected ? "selected" : ""}`}>
      <label className="result-select">
        <input type="checkbox" checked={selected} onChange={() => onToggle(item.result_id)} />
        <span>Select</span>
      </label>
      <div className="inline-meta">
        <span className="status-chip">{formatSourceLabel(item.source)}</span>
        <span className={`status-chip status-${item.status}`}>{item.status.replace("_", " ")}</span>
      </div>
      <h3 className="card-title">{item.title}</h3>
      <div className="card-meta">
        <span>{item.company}</span>
        <span>{item.location ?? "Remote"}</span>
        <span>{typeof item.fit_score === "number" ? `Fit ${(item.fit_score * 100).toFixed(0)}%` : "Pending match"}</span>
      </div>
      <p className="muted">{item.snippet}</p>
      <div className="tag-cluster">
        {uniqueSkills.map((skill, index) => (
          <span key={`${item.result_id}-${skill}-${index}` } className="tag">
            {skill}
          </span>
        ))}
      </div>
      <div className="action-row">
        {item.apply_url ? (
          <a className="button button-secondary" href={item.final_apply_url || item.apply_url} target="_blank" rel="noreferrer">
            Open listing
          </a>
        ) : null}
        <UrlStatusBadge urlStatus={item.url_status} urlVerified={item.url_verified} />
      </div>
    </article>
  );
}

function ApplicationCard({ item, selected }: { item: ApplicationQueueItem; selected: boolean }) {
  return (
    <article className={`application-card ${selected ? "selected" : ""}`}>
      <div className="panel-header">
        <div>
          <h3 className="card-title">{item.title}</h3>
          <div className="card-meta">
            <span>{item.company}</span>
            <span>{formatSourceLabel(item.source)}</span>
            <span>{item.updated_at ? new Date(item.updated_at).toLocaleString() : "Pending"}</span>
          </div>
        </div>
        <span className={`status-chip status-${item.status}`}>{item.status.replace("_", " ")}</span>
      </div>
      <div className="inline-meta">
        <span>{typeof item.fit_score === "number" ? `Fit ${(item.fit_score * 100).toFixed(0)}%` : "Fit pending"}</span>
        <span>{typeof item.ats_score === "number" ? `ATS ${Math.round(item.ats_score)}` : "ATS pending"}</span>
        <span>{item.waiting_for_human_approval ? "Awaiting approval" : "Approval cleared"}</span>
        <span>Retries {item.retries_used}</span>
      </div>
      {item.tailored_resume?.artifact_path ? <p className="muted">PDF artifact: {item.tailored_resume.artifact_path}</p> : null}
      {item.apply_url ? (
        <a className="button button-secondary" href={item.apply_url} target="_blank" rel="noreferrer">
          Open apply URL
        </a>
      ) : null}
    </article>
  );
}

function UrlStatusBadge({ urlStatus, urlVerified }: { urlStatus?: string | null; urlVerified?: boolean }) {
  if (!urlStatus) return null;
  const styles: Record<string, { color: string; label: string }> = {
    verified: { color: "#22c55e", label: "✓ Verified" },
    redirect: { color: "#eab308", label: "↗ Redirect" },
    requires_login: { color: "#ef4444", label: "🔒 Login required" },
    dead: { color: "#6b7280", label: "✗ Dead link" },
    timeout: { color: "#f97316", label: "⏱ Timeout" },
  };
  const s = styles[urlStatus] ?? { color: "#6b7280", label: urlStatus };
  return (
    <span
      style={{
        fontSize: "0.75rem",
        fontWeight: 600,
        color: s.color,
        padding: "0.15rem 0.5rem",
        borderRadius: "4px",
        border: `1px solid ${s.color}40`,
        background: `${s.color}10`,
      }}
    >
      {s.label}
    </span>
  );
}
