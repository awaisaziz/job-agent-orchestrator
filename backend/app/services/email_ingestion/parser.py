"""Rule-based parsing for job-application email state signals."""

from __future__ import annotations

import re

from app.services.email_ingestion.types import EmailMessage, EmailSignal, ParsedEmailSignal

_REFERENCE_ID_RE = re.compile(r"\b(?:app(?:lication)?|req|candidate|job)[-_:#\s]*([A-Z0-9]{5,})\b", re.IGNORECASE)

_RULES: list[tuple[EmailSignal, tuple[str, ...]]] = [
    (EmailSignal.REJECTION, ("regret to inform", "not moving forward", "unfortunately", "rejected")),
    (EmailSignal.INTERVIEW_INVITE, ("interview", "schedule", "availability", "meet with", "next round")),
    (EmailSignal.APPLICATION_RECEIVED, ("application received", "thank you for applying", "we received")),
    (EmailSignal.FOLLOW_UP_NEEDED, ("additional information", "follow up", "complete assessment", "reply with")),
]


def parse_email_signal(message: EmailMessage) -> ParsedEmailSignal:
    """Extract job-application status signal and optional identifiers from an email."""

    joined = " ".join((message.subject, message.snippet, message.body_text)).lower()
    reference_ids = sorted(set(_REFERENCE_ID_RE.findall(" ".join((message.subject, message.body_text)))))

    for signal, keywords in _RULES:
        score = sum(1 for keyword in keywords if keyword in joined)
        if score:
            confidence = min(0.99, 0.55 + (0.1 * score))
            return ParsedEmailSignal(
                signal=signal,
                confidence=confidence,
                reason=f"Matched keywords for {signal.value}: {', '.join(k for k in keywords if k in joined)}",
                reference_ids=reference_ids,
                company_hint=_infer_company_hint(message.sender, message.subject),
            )

    return ParsedEmailSignal(
        signal=EmailSignal.UNKNOWN,
        confidence=0.0,
        reason="No known status keywords matched",
        reference_ids=reference_ids,
        company_hint=_infer_company_hint(message.sender, message.subject),
    )


def _infer_company_hint(sender: str, subject: str) -> str | None:
    domain = sender.split("@")[-1].lower().strip() if "@" in sender else ""
    if domain:
        chunks = [chunk for chunk in domain.split(".") if chunk and chunk not in {"com", "io", "co", "org", "net"}]
        if chunks:
            return chunks[0].replace("-", " ").title()

    subject_match = re.search(r"\b(?:at|with)\s+([A-Z][A-Za-z0-9&\- ]{1,40})", subject)
    if subject_match:
        return subject_match.group(1).strip()
    return None
