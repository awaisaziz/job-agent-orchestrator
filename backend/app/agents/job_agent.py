"""Job ingestion agent wrapper."""

from dataclasses import dataclass, field

from app.schemas.job import JobIn, JobNormalized
from app.services.ingestion.service import normalize_job


@dataclass(slots=True)
class JobAgentInput:
    raw_jobs: list[JobIn]


@dataclass(slots=True)
class JobAgentOutput:
    normalized_jobs: list[JobNormalized]
    logs: list[str] = field(default_factory=list)


def run_job_agent(payload: JobAgentInput) -> JobAgentOutput:
    logs = [f"job_agent:start count={len(payload.raw_jobs)}"]
    normalized = [normalize_job(job) for job in payload.raw_jobs]
    logs.append(f"job_agent:completed normalized={len(normalized)}")
    return JobAgentOutput(normalized_jobs=normalized, logs=logs)
