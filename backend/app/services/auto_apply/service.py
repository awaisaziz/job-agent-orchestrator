"""Auto-apply orchestrator — routes applications to the right handler.

Flow:
1. Classify the apply URL (email_apply, simple_form, ats_portal, etc.)
2. Route to the appropriate handler:
   - email_apply → email_applicant.send_email_application()
   - simple_form → form_filler.fill_and_submit_form()
   - ats_portal, login_required, captcha_detected → SKIP (mark as requires_manual)
3. Return detailed result with audit trail
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field

from app.services.auto_apply.classifier import classify_page

logger = logging.getLogger(__name__)


@dataclass(slots=True)
class AutoApplyResult:
    success: bool
    method: str  # email, form, skipped, error
    page_type: str
    actions: list[str] = field(default_factory=list)
    screenshot_path: str | None = None
    error: str | None = None


def auto_apply(
    *,
    apply_url: str,
    job_title: str,
    company: str,
    full_name: str,
    email: str,
    phone: str | None = None,
    resume_path: str | None = None,
    screenshots_dir: str | None = None,
    resend_api_key: str | None = None,
    resend_from_email: str = "Job Agent <onboarding@resend.dev>",
) -> AutoApplyResult:
    """Attempt to auto-apply to a job. Classifies the page, then routes to handler."""

    actions: list[str] = [f"auto_apply:start url={apply_url}"]

    # Step 1: Classify the page
    classification = classify_page(apply_url, screenshots_dir=screenshots_dir)
    actions.append(
        f"auto_apply:classified page_type={classification.page_type} "
        f"confidence={classification.confidence:.2f}"
    )
    actions.extend(classification.details)

    # Step 2: Route based on classification
    if classification.page_type == "email_apply":
        return _handle_email_apply(
            classification=classification,
            apply_url=apply_url,
            job_title=job_title,
            company=company,
            full_name=full_name,
            email=email,
            phone=phone,
            resume_path=resume_path,
            actions=actions,
            resend_api_key=resend_api_key,
            resend_from_email=resend_from_email,
        )

    if classification.page_type == "simple_form":
        return _handle_form_apply(
            apply_url=apply_url,
            full_name=full_name,
            email=email,
            phone=phone,
            resume_path=resume_path,
            screenshots_dir=screenshots_dir,
            actions=actions,
        )

    # All other types: skip
    skip_reason = {
        "ats_portal": "ATS portal requires account login",
        "login_required": "Page requires login credentials",
        "captcha_detected": "Page has CAPTCHA protection",
        "unknown": "Could not determine page type",
    }.get(classification.page_type, "Unsupported page type")

    actions.append(f"auto_apply:SKIPPED reason={skip_reason}")
    return AutoApplyResult(
        success=False,
        method="skipped",
        page_type=classification.page_type,
        actions=actions,
        screenshot_path=classification.screenshot_path,
        error=skip_reason,
    )


def _handle_email_apply(
    *,
    classification,
    apply_url: str,
    job_title: str,
    company: str,
    full_name: str,
    email: str,
    phone: str | None,
    resume_path: str | None,
    actions: list[str],
    resend_api_key: str | None,
    resend_from_email: str,
) -> AutoApplyResult:
    """Handle email-based job applications via Resend."""
    from app.services.auto_apply.email_applicant import send_email_application

    hr_email = classification.hr_email
    if not hr_email:
        actions.append("auto_apply:SKIPPED no HR email found on page")
        return AutoApplyResult(
            success=False, method="skipped", page_type="email_apply",
            actions=actions, error="No HR email address found on the page",
        )

    if not resend_api_key:
        actions.append("auto_apply:SKIPPED RESEND_API_KEY not configured")
        return AutoApplyResult(
            success=False, method="skipped", page_type="email_apply",
            actions=actions, error="RESEND_API_KEY not configured in .env",
        )

    result = send_email_application(
        hr_email=hr_email,
        job_title=job_title,
        company=company,
        full_name=full_name,
        applicant_email=email,
        phone=phone,
        resume_path=resume_path,
        api_key=resend_api_key,
        from_email=resend_from_email,
    )
    actions.extend(result.logs)

    return AutoApplyResult(
        success=result.success,
        method="email",
        page_type="email_apply",
        actions=actions,
        error=result.error,
    )


def _handle_form_apply(
    *,
    apply_url: str,
    full_name: str,
    email: str,
    phone: str | None,
    resume_path: str | None,
    screenshots_dir: str | None,
    actions: list[str],
) -> AutoApplyResult:
    """Handle simple form-based job applications."""
    from app.services.auto_apply.form_filler import fill_and_submit_form

    # Build profile dict for form filler
    name_parts = full_name.split(maxsplit=1)
    profile = {
        "full_name": full_name,
        "first_name": name_parts[0] if name_parts else full_name,
        "last_name": name_parts[1] if len(name_parts) > 1 else "",
        "email": email,
        "phone": phone or "",
    }

    result = fill_and_submit_form(
        url=apply_url,
        profile=profile,
        resume_path=resume_path,
        screenshots_dir=screenshots_dir,
    )
    actions.extend(result.actions)

    return AutoApplyResult(
        success=result.success,
        method="form",
        page_type="simple_form",
        actions=actions,
        screenshot_path=result.screenshot_after or result.screenshot_before,
        error=result.error,
    )
