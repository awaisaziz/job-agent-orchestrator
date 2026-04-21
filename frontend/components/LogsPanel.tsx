import { DemoLogEntry } from "../lib/api";

export function LogsPanel({
  logs,
  modelName,
  providerName,
}: {
  logs: DemoLogEntry[];
  modelName?: string;
  providerName?: string | null;
}) {
  return (
    <section style={{ marginTop: 24 }}>
      <h2>Logs</h2>
      <p style={{ marginTop: 4, color: "#4b5563", fontSize: 13 }}>
        Active LLM: {providerName ? `${providerName} / ` : ""}
        {modelName ?? "unknown"}
      </p>
      <div style={{ display: "grid", gap: 8 }}>
        {logs.map((entry) => (
          <div key={entry.id} style={{ border: "1px solid #e5e7eb", borderRadius: 8, padding: 10 }}>
            <div style={{ fontSize: 12, color: "#4b5563" }}>
              [{entry.level.toUpperCase()}] {entry.stage} · {new Date(entry.created_at).toLocaleString()}
            </div>
            <div style={{ marginTop: 4 }}>{entry.message}</div>
            <div style={{ marginTop: 8, display: "flex", gap: 8 }}>
              <button type="button">Retry Stage</button>
              <button type="button">Mark Complete</button>
            </div>
          </div>
        ))}
      </div>
    </section>
  );
}
