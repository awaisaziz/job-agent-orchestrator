import { DemoTimelineJob } from "../lib/api";
import { StatusBadge } from "./StatusBadge";

export function JobTimeline({ jobs }: { jobs: DemoTimelineJob[] }) {
  return (
    <section style={{ marginTop: 24 }}>
      <h2>Per-job timeline</h2>
      {jobs.map((job) => (
        <div key={job.job_id} style={{ border: "1px solid #e5e7eb", borderRadius: 8, padding: 12, marginTop: 12 }}>
          <h3 style={{ margin: "0 0 6px" }}>{job.title} · {job.company}</h3>
          {job.stages.map((stage) => (
            <div key={`${job.job_id}-${stage.name}`} style={{ marginBottom: 10 }}>
              <div style={{ display: "flex", alignItems: "center", gap: 8, marginBottom: 4 }}>
                <strong style={{ fontSize: 14 }}>{stage.name}</strong>
                <StatusBadge status={stage.status} />
              </div>
              <div style={{ background: "#e5e7eb", height: 8, borderRadius: 999 }}>
                <div
                  style={{
                    width: `${stage.progress_percent}%`,
                    background: stage.status === "done" ? "#16a34a" : stage.status === "running" ? "#eab308" : "#9ca3af",
                    height: 8,
                    borderRadius: 999,
                  }}
                />
              </div>
            </div>
          ))}
        </div>
      ))}
    </section>
  );
}
