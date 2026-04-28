"""Job search agent wrapper."""

from dataclasses import dataclass, field

from app.services.job_search.service import SearchCandidate, search_jobs


@dataclass(slots=True)
class JobSearchAgentInput:
    position: str
    location: str | None = None


@dataclass(slots=True)
class JobSearchAgentOutput:
    results: list[SearchCandidate]
    logs: list[str] = field(default_factory=list)


def run_job_search_agent(payload: JobSearchAgentInput) -> JobSearchAgentOutput:
    logs = [f"job_search_agent:start position={payload.position}"]
    results = search_jobs(position=payload.position, location=payload.location)
    logs.append(f"job_search_agent:completed results={len(results)}")
    return JobSearchAgentOutput(results=results, logs=logs)
