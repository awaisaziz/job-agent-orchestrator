export function LogsPanel({ logs, modelName, providerName }: { logs: string[]; modelName?: string; providerName?: string | null }) {
  return (
    <section style={{ marginTop: 24 }}>
      <h2>Logs</h2>
      <p style={{ marginTop: 4, color: "#4b5563", fontSize: 13 }}>
        Active LLM: {providerName ? `${providerName} / ` : ""}
        {modelName ?? "unknown"}
      </p>
      <div style={{ display: "grid", gap: 8 }}>
        {logs.map((entry, index) => (
          <div key={`${entry}-${index}`} style={{ border: "1px solid #e5e7eb", borderRadius: 8, padding: 10 }}>
            <div>{entry}</div>
          </div>
        ))}
      </div>
    </section>
  );
}
