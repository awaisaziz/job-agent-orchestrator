"""Application agent service — real auto-apply with Playwright + email.

Replaces the previous stub with real submission logic:
- Classifies apply pages (email, form, ATS portal, login-required, CAPTCHA)
- Sends email applications for email_apply pages
- Fills forms for simple_form pages
- Skips ATS portals and login-required pages (marks as requires_manual)
"""

from dataclasses import dataclass, field
import logging

from app.db.models.credential_profile import CredentialProfileStatus
from app.schemas.pipeline import PipelineStatus

logger = logging.getLogger(__name__)


@dataclass(slots=True)
class ApplicationAction:
    action: str
    detail: str


@dataclass(slots=True)
class ApplicationAttemptResult:
    status: PipelineStatus
    attempts: int
    logs: list[ApplicationAction] = field(default_factory=list)
    error: str | None = None
    method: str = "none"  # email, form, skipped
    page_type: str = "unknown"


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
    fail_until_attempt: int = 0,
    apply_url: str | None = None,
    resume_path: str | None = None,
) -> ApplicationAttemptResult:
    """Real submission interface — classifies page and applies via email or form."""

    logs: list[ApplicationAction] = []

    if credential_status == CredentialProfileStatus.REVOKED:
        logs.append(ApplicationAction(
            action="guard",
            detail=f"Credential profile {credential_profile_id} is revoked.",
        ))
        return ApplicationAttemptResult(
            status=PipelineStatus.FAILED, attempts=0, logs=logs,
        )

    profile = applicant_profile or {}
    full_name = profile.get("full_name", "Candidate")
    email = profile.get("email", "")

    # If no apply URL, we can't do anything real
    if not apply_url:
        logs.append(ApplicationAction(
            action="guard", detail="No apply URL provided — cannot auto-apply",
        ))
        return ApplicationAttemptResult(
            status=PipelineStatus.FAILED, attempts=0, logs=logs,
            error="No apply URL",
        )

    logs.append(ApplicationAction(
        action="auto_apply",
        detail=f"Starting auto-apply for {job_title} at {company}",
    ))

    try:
        from app.core.config import settings
        from app.services.auto_apply.service import auto_apply

        result = auto_apply(
            apply_url=apply_url,
            job_title=job_title,
            company=company,
            full_name=full_name,
            email=email,
            phone=profile.get("phone"),
            resume_path=resume_path,
            screenshots_dir=str(settings.auto_apply_screenshots_dir),
            resend_api_key=settings.resend_api_key,
            resend_from_email=settings.resend_from_email,
        )

        for action_detail in result.actions:
            logs.append(ApplicationAction(action="auto_apply", detail=action_detail))

        if result.success:
            logs.append(ApplicationAction(
                action="result",
                detail=f"Applied via {result.method} for {job_title} at {company}",
            ))
            return ApplicationAttemptResult(
                status=PipelineStatus.COMPLETED, attempts=1, logs=logs,
                method=result.method, page_type=result.page_type,
            )
        else:
            logs.append(ApplicationAction(
                action="result",
                detail=f"Auto-apply skipped/failed: {result.error or 'unknown'}",
            ))
            return ApplicationAttemptResult(
                status=PipelineStatus.FAILED, attempts=1, logs=logs,
                error=result.error, method=result.method, page_type=result.page_type,
            )

    except ImportError:
        # Playwright not installed — graceful degradation
        logs.append(ApplicationAction(
            action="fallback",
            detail="Playwright not installed — auto-apply unavailable. Install with: pip install playwright && playwright install chromium",
        ))
        return ApplicationAttemptResult(
            status=PipelineStatus.FAILED, attempts=0, logs=logs,
            error="Playwright not installed",
        )
    except Exception as exc:
        logger.exception("Auto-apply failed for %s at %s", job_title, company)
        logs.append(ApplicationAction(
            action="error", detail=f"Auto-apply error: {exc}",
        ))
        return ApplicationAttemptResult(
            status=PipelineStatus.FAILED, attempts=1, logs=logs,
            error=str(exc),
        )
