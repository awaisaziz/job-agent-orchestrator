"""Application agent service with retry-safe stub and action logging."""

from dataclasses import dataclass, field

from app.db.models.credential_profile import CredentialProfileStatus
from app.schemas.job import JobIn
from app.schemas.pipeline import PipelineStatus
from app.services.credentials.utility import redact_sensitive_values
from app.services.linkedin.service import fill_linkedin_easy_apply


@dataclass(slots=True)
class ApplicationAction:
    action: str
    detail: str


@dataclass(slots=True)
class ApplicationAttemptResult:
    status: PipelineStatus
    attempts: int
    logs: list[ApplicationAction] = field(default_factory=list)


def submit_application(
    job_title: str,
    company: str,
    credential_profile_id: str,
    credential_status: CredentialProfileStatus = CredentialProfileStatus.ACTIVE,
    credential_username: str | None = None,
    credential_secret: str | None = None,
    max_retries: int = 2,
    platform: str = "generic",
    applicant_profile: dict[str, str] | None = None,
) -> ApplicationAttemptResult:
    """Retry-safe submission interface with stubbed Playwright call for demo."""

    logs: list[ApplicationAction] = []
    if credential_status == CredentialProfileStatus.REVOKED:
        logs.append(
            ApplicationAction(
                action="guard",
                detail=f"Credential profile {credential_profile_id} is revoked and cannot be used.",
            )
        )
        return ApplicationAttemptResult(status=PipelineStatus.FAILED, attempts=0, logs=logs)

    redaction_inputs = [credential_profile_id, credential_username, credential_secret]

    if platform == "linkedin":
        linkedin_result = fill_linkedin_easy_apply(
            job=JobIn(
                source="linkedin",
                raw_title=job_title,
                raw_company=company,
                raw_description="",
                raw_location="Remote",
                raw_apply_link="https://www.linkedin.com/jobs",
            ),
            applicant_profile=applicant_profile or {},
        )
        logs.extend(
            ApplicationAction(action="linkedin", detail=detail)
            for detail in linkedin_result.logs
        )
        return ApplicationAttemptResult(
            status=linkedin_result.status,
            attempts=1,
            logs=logs,
        )
    for attempt in range(1, max_retries + 1):
        logs.append(
            ApplicationAction(
                action="navigate",
                detail=redact_sensitive_values(
                    f"Attempt {attempt}: open {company} careers page using credential profile "
                    f"{credential_profile_id} and username {credential_username or 'n/a'}",
                    redaction_inputs,
                ),
            )
        )
        logs.append(ApplicationAction(action="playwright_stub", detail="Playwright submit flow skipped in demo mode"))
        if attempt == 1:
            logs.append(
                ApplicationAction(
                    action="result",
                    detail=redact_sensitive_values(
                        f"Simulated success for {job_title} with credential profile {credential_profile_id}",
                        redaction_inputs,
                    ),
                )
            )
            return ApplicationAttemptResult(status=PipelineStatus.COMPLETED, attempts=attempt, logs=logs)
    logs.append(ApplicationAction(action="result", detail="All retries exhausted"))
    return ApplicationAttemptResult(status=PipelineStatus.FAILED, attempts=max_retries, logs=logs)
