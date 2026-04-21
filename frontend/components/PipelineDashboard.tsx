import { JobTimeline } from "./JobTimeline";
import { LogsPanel } from "./LogsPanel";

export function PipelineDashboard() {
  return (
    <main style={{ padding: 24, fontFamily: "sans-serif" }}>
      <h1>Job Agent Orchestrator</h1>
      <p>Mock pipeline run for demo purposes.</p>
      <JobTimeline />
      <LogsPanel />
    </main>
  );
}
