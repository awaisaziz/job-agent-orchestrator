"""Application submission agent wrapper."""

from dataclasses import dataclass, field

from app.services.application_agent.service import ApplicationAttemptResult, submit_application


@dataclass(slots=True)
class ApplyAgentInput:
    job_title: str
    company: str


@dataclass(slots=True)
class ApplyAgentOutput:
    result: ApplicationAttemptResult
    logs: list[str] = field(default_factory=list)


def run_apply_agent(payload: ApplyAgentInput) -> ApplyAgentOutput:
    logs = [f"apply_agent:start {payload.job_title}@{payload.company}"]
    result = submit_application(job_title=payload.job_title, company=payload.company)
    logs.append(f"apply_agent:completed attempts={result.attempts} status={result.status.value}")
    return ApplyAgentOutput(result=result, logs=logs)
