"""Data contracts for email ingestion and parsing."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from enum import Enum


READ_ONLY_GMAIL_SCOPES = {
    "https://www.googleapis.com/auth/gmail.readonly",
    "openid",
    "email",
    "profile",
}


class EmailSignal(str, Enum):
    APPLICATION_RECEIVED = "application_received"
    INTERVIEW_INVITE = "interview_invite"
    REJECTION = "rejection"
    FOLLOW_UP_NEEDED = "follow_up_needed"
    UNKNOWN = "unknown"


@dataclass(slots=True)
class EmailMessage:
    message_id: str
    thread_id: str
    subject: str
    sender: str
    recipients: list[str]
    snippet: str
    body_text: str
    received_at: datetime
    labels: list[str]
    provider: str = "gmail"


@dataclass(slots=True)
class ParsedEmailSignal:
    signal: EmailSignal
    confidence: float
    reason: str
    reference_ids: list[str]
    company_hint: str | None = None


@dataclass(slots=True)
class ConnectorTokens:
    access_token: str
    refresh_token: str | None


@dataclass(slots=True)
class SyncOutcome:
    processed_messages: int
    inserted_events: int
    last_synced_message_id: str | None
    rate_limited: bool = False
