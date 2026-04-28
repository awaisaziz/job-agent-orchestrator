import { ApplicationTrackingItem } from "../lib/api";
import { StatusBadge } from "./StatusBadge";

function timelineClass(status: ApplicationTrackingItem["status"]): string {
  return status.toLowerCase();
}

export function JobTimeline({ jobs }: { jobs: ApplicationTrackingItem[] }) {
  return (
    <section className="panel">
      <div className="panel-header">
        <div>
          <h2 className="panel-title">Application tracking</h2>
          <p className="panel-copy">Each record shows the application state, fit score, retry count, and whether safety controls blocked progression.</p>
        </div>
      </div>

      {jobs.length ? (
        <div className="timeline">
          {jobs.map((job) => (
            <article key={job.application_id} className={`timeline-item ${timelineClass(job.status)}`}>
              <div className="panel-header">
                <div>
                  <h3 className="card-title">
                    {job.job_title} at {job.company}
                  </h3>
                  <div className="card-meta">
                    <span>Application id: {job.application_id}</span>
                    <span>Created: {new Date(job.created_at).toLocaleString()}</span>
                  </div>
                </div>
                <StatusBadge status={job.status} />
              </div>

              <div className="inline-meta">
                <span>ATS score: {Math.round(job.ats_score)}</span>
                <span>Retries: {job.retries_used}</span>
                <span>Duplicate blocked: {job.duplicate_blocked ? "yes" : "no"}</span>
                <span>Approval wait: {job.waiting_for_human_approval ? "yes" : "no"}</span>
              </div>

              {job.duplicate_blocked ? <div className="notice notice-error">Duplicate prevention blocked this application from re-submitting.</div> : null}
              {job.waiting_for_human_approval ? (
                <div className="notice notice-info">This application is paused at the human approval gate.</div>
              ) : null}
            </article>
          ))}
        </div>
      ) : (
        <div className="empty-state">No application tracking records yet. Run a pipeline to create the first tracked item.</div>
      )}
    </section>
  );
}
