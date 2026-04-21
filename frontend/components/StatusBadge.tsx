export function StatusBadge({ status }: { status: "PENDING" | "PROCESSING" | "COMPLETED" | "FAILED" }) {
  const colors: Record<string, string> = {
    COMPLETED: "#16a34a",
    PROCESSING: "#eab308",
    PENDING: "#6b7280",
    FAILED: "#dc2626",
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
