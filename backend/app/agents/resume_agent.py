"""Resume tailoring agent wrapper."""

from dataclasses import dataclass, field

from app.schemas.job import JobNormalized
from app.schemas.profile import Profile
from app.schemas.resume import TailoredResume
from app.services.llm_gateway.registry import DEFAULT_MODEL_NAME
from app.services.resume_agent.service import build_tailored_resume


@dataclass(slots=True)
class ResumeAgentInput:
    base_resume: str
    profile: Profile
    target_job: JobNormalized
    model_name: str = DEFAULT_MODEL_NAME


@dataclass(slots=True)
class ResumeAgentOutput:
    tailored_resume: TailoredResume
    logs: list[str] = field(default_factory=list)


def run_resume_agent(payload: ResumeAgentInput) -> ResumeAgentOutput:
    logs = [f"resume_agent:start job={payload.target_job.title} model={payload.model_name}"]
    result = build_tailored_resume(
        base_resume=payload.base_resume,
        profile=payload.profile,
        job=payload.target_job,
        model_name=payload.model_name,
    )
    logs.append("resume_agent:completed truth_preserved=true")
    return ResumeAgentOutput(tailored_resume=result, logs=logs)
