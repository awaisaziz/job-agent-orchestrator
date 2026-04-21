import { StatusBadge } from "./StatusBadge";

const steps = ["Ingestion", "Matching", "Resume Tailoring", "Application", "Feedback"];

export function JobTimeline() {
  return (
    <section>
      <h2>Pipeline Timeline</h2>
      <ul>
        {steps.map((step) => (
          <li key={step}>
            {step} <StatusBadge status="done" />
          </li>
        ))}
      </ul>
    </section>
  );
}
