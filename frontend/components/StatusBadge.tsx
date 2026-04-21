export function StatusBadge({ status }: { status: "done" | "running" | "pending" }) {
  const colors: Record<string, string> = {
    done: "#16a34a",
    running: "#eab308",
    pending: "#6b7280",
  };

  return (
    <span
      style={{
        backgroundColor: colors[status],
        color: "white",
        borderRadius: 12,
        padding: "2px 8px",
        fontSize: 12,
      }}
    >
      {status}
    </span>
  );
}
