"""Email-based job application sender via Resend API.

For jobs classified as 'email_apply', this service:
1. Composes a professional application email with cover body
2. Attaches the tailored resume PDF (base64-encoded, Resend API format)
3. Sends via Resend API using stdlib urllib — no new dependencies
4. Logs every action for the audit trail

Docs: https://resend.com/docs/api-reference/emails/send-email
"""

from __future__ import annotations

import base64
import json
import logging
from dataclasses import dataclass, field
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

logger = logging.getLogger(__name__)

_RESEND_API_URL = "https://api.resend.com/emails"


@dataclass(slots=True)
class EmailApplicationResult:
    success: bool
    hr_email: str
    subject: str
    logs: list[str] = field(default_factory=list)
    error: str | None = None


def send_email_application(
    *,
    hr_email: str,
    job_title: str,
    company: str,
    full_name: str,
    applicant_email: str,
    phone: str | None = None,
    resume_path: str | None = None,
    cover_text: str | None = None,
    api_key: str,
    from_email: str = "Job Agent <onboarding@resend.dev>",
) -> EmailApplicationResult:
    """Send a job application email with optional resume attachment via Resend."""

    subject = f"Application for {job_title} — {full_name}"
    logs: list[str] = [f"email_apply:composing subject='{subject}' to={hr_email}"]

    body = cover_text or _default_cover_body(
        full_name=full_name, job_title=job_title, company=company,
        email=applicant_email, phone=phone,
    )

    # Build Resend payload
    payload: dict = {
        "from": from_email,
        "to": [hr_email],
        "reply_to": applicant_email,
        "subject": subject,
        "text": body,
    }

    # Attach resume as base64 if available
    if resume_path and Path(resume_path).exists():
        with open(resume_path, "rb") as f:
            encoded = base64.b64encode(f.read()).decode("utf-8")
        payload["attachments"] = [
            {
                "filename": Path(resume_path).name,
                "content": encoded,
            }
        ]
        logs.append(f"email_apply:attached resume={Path(resume_path).name}")
    else:
        logs.append("email_apply:no resume file to attach")

    logs.append(f"email_apply:sending via Resend API to={hr_email}")

    request = Request(
        url=_RESEND_API_URL,
        data=json.dumps(payload).encode("utf-8"),
        headers={
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
        },
        method="POST",
    )

    try:
        with urlopen(request, timeout=10) as response:
            data = json.loads(response.read().decode("utf-8"))
            msg_id = data.get("id", "unknown")
            logs.append(f"email_apply:sent successfully id={msg_id}")
            return EmailApplicationResult(
                success=True, hr_email=hr_email, subject=subject, logs=logs,
            )

    except HTTPError as exc:
        body_err = exc.read().decode("utf-8", errors="replace")
        error = f"Resend API error {exc.code}: {body_err[:300]}"
        logs.append(f"email_apply:FAILED {error}")
        logger.error(error)
        return EmailApplicationResult(
            success=False, hr_email=hr_email, subject=subject, logs=logs, error=error,
        )

    except URLError as exc:
        error = f"Resend network error: {exc.reason}"
        logs.append(f"email_apply:FAILED {error}")
        logger.error(error)
        return EmailApplicationResult(
            success=False, hr_email=hr_email, subject=subject, logs=logs, error=error,
        )

    except Exception as exc:
        error = f"Email send failed: {exc}"
        logs.append(f"email_apply:FAILED {error}")
        logger.exception("Email application failed")
        return EmailApplicationResult(
            success=False, hr_email=hr_email, subject=subject, logs=logs, error=str(exc),
        )


def _default_cover_body(
    *, full_name: str, job_title: str, company: str, email: str, phone: str | None
) -> str:
    """Generate a brief, professional default application email body."""
    contact = f"Email: {email}"
    if phone:
        contact += f" | Phone: {phone}"

    return f"""Dear Hiring Team,

I am writing to express my interest in the {job_title} position at {company}.

Please find my resume attached for your consideration. I believe my skills and experience align well with the requirements of this role, and I would welcome the opportunity to discuss how I can contribute to your team.

I am available for an interview at your earliest convenience.

Thank you for your time and consideration.

Best regards,
{full_name}
{contact}
"""
