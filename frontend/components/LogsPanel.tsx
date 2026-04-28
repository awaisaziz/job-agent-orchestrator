export function LogsPanel({ logs, modelName, providerName }: { logs: string[]; modelName?: string; providerName?: string | null }) {
  return (
    <section className="panel">
      <div className="panel-header">
        <div>
          <h2 className="panel-title">Execution logs</h2>
          <p className="panel-copy">
            Active LLM: {providerName ? `${providerName} / ` : ""}
            {modelName ?? "unknown"}
          </p>
        </div>
      </div>

      {logs.length ? (
        <div className="log-list">
          {logs.map((entry, index) => (
            <div key={`${entry}-${index}`} className="log-entry">
              {entry}
            </div>
          ))}
        </div>
      ) : (
        <div className="empty-state">Run a pipeline to see orchestration logs and application events.</div>
      )}
    </section>
  );
}
