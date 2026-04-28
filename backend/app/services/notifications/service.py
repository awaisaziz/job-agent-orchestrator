"""Resend email notification service.

Sends a summary email to the user after job applications are submitted.
Uses Resend API (https://resend.com) via stdlib urllib — no new dependencies.

Free tier: 3,000 emails/month, 100/day.
Docs: https://resend.com/docs/api-reference/emails/send-email
"""

from __future__ import annotations

import json
import logging
from dataclasses import dataclass, field
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

logger = logging.getLogger(__name__)

_RESEND_API_URL = "https://api.resend.com/emails"


@dataclass(slots=True)
class ApplicationSummaryItem:
    job_title: str
    company: str
    apply_url: str
    status: str  # applied, skipped, failed
    ats_score: float | None = None
    skip_reason: str | None = None


@dataclass(slots=True)
class NotificationResult:
    sent: bool
    recipient: str
    message_id: str | None = None
    error: str | None = None


def send_application_summary(
    *,
    recipient_email: str,
    full_name: str,
    applications: list[ApplicationSummaryItem],
    dashboard_url: str | None = None,
    api_key: str,
    from_email: str = "Job Agent <onboarding@resend.dev>",
) -> NotificationResult:
    """Send a job application summary email via Resend API."""

    applied = [a for a in applications if a.status == "applied"]
    skipped = [a for a in applications if a.status == "skipped"]
    failed = [a for a in applications if a.status == "failed"]
    total = len(applications)

    subject = f"Job Agent — {len(applied)} Applied, {len(skipped)} Skipped ({total} Total)"

    text_body = _build_text_body(
        full_name=full_name,
        applied=applied,
        skipped=skipped,
        failed=failed,
        applications=applications,
        dashboard_url=dashboard_url,
    )

    html_body = _build_html_body(
        full_name=full_name,
        applied=applied,
        skipped=skipped,
        failed=failed,
        applications=applications,
        dashboard_url=dashboard_url,
    )

    payload = json.dumps({
        "from": from_email,
        "to": [recipient_email],
        "subject": subject,
        "text": text_body,
        "html": html_body,
    }).encode("utf-8")

    request = Request(
        url=_RESEND_API_URL,
        data=payload,
        headers={
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
        },
        method="POST",
    )

    try:
        with urlopen(request, timeout=10) as response:
            data = json.loads(response.read().decode("utf-8"))
            message_id = data.get("id")
            logger.info("Resend notification sent to %s (id=%s)", recipient_email, message_id)
            return NotificationResult(sent=True, recipient=recipient_email, message_id=message_id)

    except HTTPError as exc:
        body = exc.read().decode("utf-8", errors="replace")
        error = f"Resend API error {exc.code}: {body[:300]}"
        logger.error(error)
        return NotificationResult(sent=False, recipient=recipient_email, error=error)

    except URLError as exc:
        error = f"Resend network error: {exc.reason}"
        logger.error(error)
        return NotificationResult(sent=False, recipient=recipient_email, error=error)

    except Exception as exc:
        error = f"Unexpected error: {exc}"
        logger.exception("Failed to send Resend notification to %s", recipient_email)
        return NotificationResult(sent=False, recipient=recipient_email, error=error)


def send_notification_if_configured(
    *,
    recipient_email: str,
    full_name: str,
    applications: list[ApplicationSummaryItem],
    dashboard_url: str | None = None,
) -> NotificationResult | None:
    """Send notification using Resend settings from config.

    Returns None (without error) if RESEND_API_KEY is not configured.
    """
    from app.core.config import settings

    if not settings.resend_api_key:
        logger.info("RESEND_API_KEY not configured — skipping notification email")
        return None

    return send_application_summary(
        recipient_email=recipient_email,
        full_name=full_name,
        applications=applications,
        dashboard_url=dashboard_url,
        api_key=settings.resend_api_key,
        from_email=settings.resend_from_email,
    )


# ── Body builders ────────────────────────────────────────────────────────────

def _build_text_body(
    *,
    full_name: str,
    applied: list[ApplicationSummaryItem],
    skipped: list[ApplicationSummaryItem],
    failed: list[ApplicationSummaryItem],
    applications: list[ApplicationSummaryItem],
    dashboard_url: str | None,
) -> str:
    lines = [
        f"Hi {full_name},",
        "",
        f"Your job agent has processed {len(applications)} application(s):",
        "",
    ]

    if applied:
        lines.append(f"✅ APPLIED ({len(applied)}):")
        for app in applied:
            score = f" | ATS: {app.ats_score:.0f}%" if app.ats_score is not None else ""
            lines.append(f"  • {app.job_title} at {app.company}{score}")
            lines.append(f"    {app.apply_url}")
        lines.append("")

    if skipped:
        lines.append(f"⚠️ SKIPPED ({len(skipped)}):")
        for app in skipped:
            reason = f" — {app.skip_reason}" if app.skip_reason else ""
            lines.append(f"  • {app.job_title} at {app.company}{reason}")
            lines.append(f"    {app.apply_url}")
        lines.append("")

    if failed:
        lines.append(f"❌ FAILED ({len(failed)}):")
        for app in failed:
            reason = f" — {app.skip_reason}" if app.skip_reason else ""
            lines.append(f"  • {app.job_title} at {app.company}{reason}")
        lines.append("")

    scores = [a.ats_score for a in applications if a.ats_score is not None]
    if scores:
        lines.append(f"ATS scores ranged from {min(scores):.0f}% to {max(scores):.0f}%.")
        lines.append("")

    if dashboard_url:
        lines.append(f"View your dashboard: {dashboard_url}")
        lines.append("")

    lines.extend(["—", "Job Agent Orchestrator", "This is an automated message."])
    return "\n".join(lines)


def _build_html_body(
    *,
    full_name: str,
    applied: list[ApplicationSummaryItem],
    skipped: list[ApplicationSummaryItem],
    failed: list[ApplicationSummaryItem],
    applications: list[ApplicationSummaryItem],
    dashboard_url: str | None,
) -> str:
    """Build a clean HTML email with inline styles for broad client compatibility."""

    def _row(emoji: str, title: str, company: str, url: str, score: float | None, reason: str | None) -> str:
        score_badge = (
            f'<span style="background:#1a1a2e;color:#a78bfa;padding:2px 8px;border-radius:12px;font-size:12px;font-weight:600;margin-left:8px">ATS {score:.0f}%</span>'
            if score is not None else ""
        )
        reason_str = f'<div style="color:#9ca3af;font-size:12px;margin-top:2px">{reason}</div>' if reason else ""
        return f"""
        <tr>
          <td style="padding:12px 0;border-bottom:1px solid #1e1e2e">
            <div style="display:flex;align-items:center;gap:8px">
              <span style="font-size:18px">{emoji}</span>
              <div>
                <span style="font-weight:600;color:#e2e8f0">{title}</span>
                <span style="color:#6b7280;margin:0 6px">at</span>
                <span style="color:#a78bfa">{company}</span>
                {score_badge}
                <div style="margin-top:4px">
                  <a href="{url}" style="color:#818cf8;font-size:12px;word-break:break-all">{url}</a>
                </div>
                {reason_str}
              </div>
            </div>
          </td>
        </tr>"""

    rows_html = ""
    for app in applied:
        rows_html += _row("✅", app.job_title, app.company, app.apply_url, app.ats_score, None)
    for app in skipped:
        rows_html += _row("⚠️", app.job_title, app.company, app.apply_url, None, app.skip_reason)
    for app in failed:
        rows_html += _row("❌", app.job_title, app.company, app.apply_url, None, app.skip_reason)

    scores = [a.ats_score for a in applications if a.ats_score is not None]
    score_line = (
        f'<p style="color:#9ca3af;font-size:13px;margin:16px 0 0">ATS scores ranged from <strong>{min(scores):.0f}%</strong> to <strong>{max(scores):.0f}%</strong>.</p>'
        if scores else ""
    )

    dashboard_btn = (
        f'<a href="{dashboard_url}" style="display:inline-block;margin-top:20px;padding:10px 24px;background:linear-gradient(135deg,#7c3aed,#4f46e5);color:#fff;text-decoration:none;border-radius:8px;font-weight:600;font-size:14px">View Dashboard →</a>'
        if dashboard_url else ""
    )

    return f"""<!DOCTYPE html>
<html>
<head><meta charset="utf-8"><title>Job Agent Summary</title></head>
<body style="margin:0;padding:0;background:#0f0f1a;font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',sans-serif">
  <table width="100%" cellpadding="0" cellspacing="0" style="background:#0f0f1a;padding:40px 0">
    <tr><td align="center">
      <table width="600" cellpadding="0" cellspacing="0" style="background:#13131f;border-radius:16px;overflow:hidden;border:1px solid #1e1e2e">

        <!-- Header -->
        <tr><td style="background:linear-gradient(135deg,#1a1a2e,#16213e);padding:32px 40px">
          <div style="font-size:22px;font-weight:700;color:#e2e8f0">🤖 Job Agent Report</div>
          <div style="color:#9ca3af;font-size:14px;margin-top:6px">Hi {full_name} — here's what your agent did</div>
        </td></tr>

        <!-- Stats bar -->
        <tr><td style="padding:24px 40px;border-bottom:1px solid #1e1e2e">
          <table width="100%" cellpadding="0" cellspacing="0">
            <tr>
              <td align="center" style="padding:12px;background:#0f0f1a;border-radius:10px;border:1px solid #1e1e2e">
                <div style="font-size:28px;font-weight:700;color:#22c55e">{len(applied)}</div>
                <div style="font-size:12px;color:#9ca3af;margin-top:2px">Applied</div>
              </td>
              <td width="12"></td>
              <td align="center" style="padding:12px;background:#0f0f1a;border-radius:10px;border:1px solid #1e1e2e">
                <div style="font-size:28px;font-weight:700;color:#eab308">{len(skipped)}</div>
                <div style="font-size:12px;color:#9ca3af;margin-top:2px">Skipped</div>
              </td>
              <td width="12"></td>
              <td align="center" style="padding:12px;background:#0f0f1a;border-radius:10px;border:1px solid #1e1e2e">
                <div style="font-size:28px;font-weight:700;color:#ef4444">{len(failed)}</div>
                <div style="font-size:12px;color:#9ca3af;margin-top:2px">Failed</div>
              </td>
              <td width="12"></td>
              <td align="center" style="padding:12px;background:#0f0f1a;border-radius:10px;border:1px solid #1e1e2e">
                <div style="font-size:28px;font-weight:700;color:#a78bfa">{len(applications)}</div>
                <div style="font-size:12px;color:#9ca3af;margin-top:2px">Total</div>
              </td>
            </tr>
          </table>
        </td></tr>

        <!-- Job rows -->
        <tr><td style="padding:0 40px 24px">
          <table width="100%" cellpadding="0" cellspacing="0">
            {rows_html}
          </table>
          {score_line}
          {dashboard_btn}
        </td></tr>

        <!-- Footer -->
        <tr><td style="padding:20px 40px;background:#0a0a14;border-top:1px solid #1e1e2e">
          <p style="margin:0;color:#4b5563;font-size:12px">Job Agent Orchestrator • Automated notification • Do not reply</p>
        </td></tr>

      </table>
    </td></tr>
  </table>
</body>
</html>"""
