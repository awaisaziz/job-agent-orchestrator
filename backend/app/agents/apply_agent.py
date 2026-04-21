"""Application submission agent wrapper."""

from dataclasses import dataclass, field

from app.db.models.credential_profile import CredentialProfileStatus
from app.services.application_agent.service import ApplicationAttemptResult, submit_application


@dataclass(slots=True)
class ApplyAgentInput:
    job_title: str
    company: str
    credential_profile_id: str
    credential_status: CredentialProfileStatus = CredentialProfileStatus.ACTIVE
    credential_username: str | None = None
    credential_secret: str | None = None
    platform: str = "generic"
    applicant_profile: dict[str, str] | None = None


@dataclass(slots=True)
class ApplyAgentOutput:
    result: ApplicationAttemptResult
    logs: list[str] = field(default_factory=list)


def run_apply_agent(payload: ApplyAgentInput) -> ApplyAgentOutput:
    logs = [f"apply_agent:start {payload.job_title}@{payload.company} credential_profile_id=[REDACTED]"]
    result = submit_application(
        job_title=payload.job_title,
        company=payload.company,
        credential_profile_id=payload.credential_profile_id,
        credential_status=payload.credential_status,
        credential_username=payload.credential_username,
        credential_secret=payload.credential_secret,
        platform=payload.platform,
        applicant_profile=payload.applicant_profile,
    )
    logs.append(f"apply_agent:completed attempts={result.attempts} status={result.status.value}")
    return ApplyAgentOutput(result=result, logs=logs)
