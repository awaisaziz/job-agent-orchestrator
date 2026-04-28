import { PipelineStatus } from "../lib/api";

const STATUS_CLASS: Record<PipelineStatus, string> = {
  COMPLETED: "completed",
  PROCESSING: "processing",
  PENDING: "pending",
  FAILED: "failed",
};

export function StatusBadge({ status, label }: { status: PipelineStatus; label?: string }) {
  return <span className={`status-badge ${STATUS_CLASS[status]}`}>{label ? `${label}: ${status}` : status}</span>;
}
