import { ApplicationTrackingItem } from "../lib/api";
import { StatusBadge } from "./StatusBadge";

export function JobTimeline({ jobs }: { jobs: ApplicationTrackingItem[] }) {
  return (
    <section style={{ marginTop: 24 }}>
      <h2>Application tracking dashboard</h2>
      {jobs.map((job) => (
        <div key={job.application_id} style={{ border: "1px solid #e5e7eb", borderRadius: 8, padding: 12, marginTop: 12 }}>
          <h3 style={{ margin: "0 0 6px" }}>
            {job.job_title} · {job.company}
          </h3>
          <div style={{ display: "flex", gap: 10, alignItems: "center" }}>
            <StatusBadge status={job.status} />
            <span>ATS score: {job.ats_score}</span>
            <span>Retries: {job.retries_used}</span>
          </div>
          {job.duplicate_blocked && <p style={{ color: "#b91c1c" }}>Duplicate prevention blocked this application.</p>}
          {job.waiting_for_human_approval && <p style={{ color: "#92400e" }}>Waiting for human approval.</p>}
        </div>
      ))}
    </section>
  );
}
