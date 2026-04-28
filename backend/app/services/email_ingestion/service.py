"""Mailbox sync service: secure OAuth, parsing, matching, and audit event persistence."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta, timezone

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import settings
from app.db.models.application_event import ApplicationEvent, ApplicationEventType
from app.db.models.email_credential import EmailCredential
from app.db.models.email_sync_state import EmailSyncState
from app.services.email_ingestion.gmail_client import GmailConnector
from app.services.email_ingestion.matcher import find_matching_application
from app.services.email_ingestion.parser import parse_email_signal
from app.services.email_ingestion.security import TokenCipher
from app.services.email_ingestion.types import ConnectorTokens, EmailSignal, SyncOutcome

_SIGNAL_TO_EVENT = {
    EmailSignal.APPLICATION_RECEIVED: ApplicationEventType.APPLICATION_RECEIVED,
    EmailSignal.INTERVIEW_INVITE: ApplicationEventType.INTERVIEW_INVITE,
    EmailSignal.REJECTION: ApplicationEventType.REJECTION,
    EmailSignal.FOLLOW_UP_NEEDED: ApplicationEventType.FOLLOW_UP_NEEDED,
}


@dataclass(slots=True)
class EmailIngestionService:
    """Coordinates mailbox ingestion with rate limiting and idempotent checkpoints."""

    connector: GmailConnector
    cipher: TokenCipher

    def sync(self, session: Session, user_id: int) -> SyncOutcome:
        credential = self._load_credential(session=session, user_id=user_id)
        self._validate_scopes(credential)

        state = self._load_sync_state(session=session, user_id=user_id)
        if self._is_rate_limited(state):
            return SyncOutcome(
                processed_messages=0,
                inserted_events=0,
                last_synced_message_id=state.last_synced_message_id,
                rate_limited=True,
            )

        tokens = ConnectorTokens(
            access_token=self.cipher.decrypt(credential.encrypted_access_token),
            refresh_token=self.cipher.decrypt(credential.encrypted_refresh_token)
            if credential.encrypted_refresh_token
            else None,
        )
        messages = self.connector.fetch_messages(
            tokens,
            since_message_id=state.last_synced_message_id,
            max_results=settings.email_sync_max_messages,
            read_only_scopes=tuple(settings.gmail_readonly_scopes),
        )

        inserted_events = 0
        processed = 0
        latest_id = state.last_synced_message_id
        for message in messages:
            processed += 1
            latest_id = message.message_id
            if self._event_exists(session=session, provider=message.provider, message_id=message.message_id):
                continue
            parsed = parse_email_signal(message)
            event_type = _SIGNAL_TO_EVENT.get(parsed.signal)
            if event_type is None:
                continue

            application = find_matching_application(session=session, user_id=user_id, parsed=parsed)
            if application is None:
                continue

            session.add(
                ApplicationEvent(
                    application_id=application.id,
                    event_type=event_type,
                    detail=parsed.reason,
                    source_provider=message.provider,
                    source_message_id=message.message_id,
                    source_thread_id=message.thread_id,
                    source_metadata={
                        "subject": message.subject,
                        "sender": message.sender,
                        "received_at": message.received_at.isoformat(),
                        "reference_ids": parsed.reference_ids,
                        "labels": message.labels,
                        "confidence": parsed.confidence,
                    },
                )
            )
            inserted_events += 1

        state.last_synced_message_id = latest_id
        state.last_synced_at = datetime.now(timezone.utc)
        session.add(state)
        session.flush()

        return SyncOutcome(
            processed_messages=processed,
            inserted_events=inserted_events,
            last_synced_message_id=latest_id,
            rate_limited=False,
        )

    @staticmethod
    def _load_credential(session: Session, user_id: int) -> EmailCredential:
        credential = session.scalar(
            select(EmailCredential).where(EmailCredential.user_id == user_id, EmailCredential.provider == "gmail")
        )
        if credential is None:
            raise ValueError(f"No Gmail credential configured for user_id={user_id}")
        return credential

    @staticmethod
    def _load_sync_state(session: Session, user_id: int) -> EmailSyncState:
        state = session.scalar(
            select(EmailSyncState).where(EmailSyncState.user_id == user_id, EmailSyncState.provider == "gmail")
        )
        if state is None:
            state = EmailSyncState(user_id=user_id, provider="gmail")
            session.add(state)
            session.flush()
        return state

    @staticmethod
    def _validate_scopes(credential: EmailCredential) -> None:
        granted = {scope.strip() for scope in credential.granted_scopes.split(" ") if scope.strip()}
        allowed = set(settings.gmail_readonly_scopes)
        if not granted:
            raise ValueError("No OAuth scopes granted for Gmail connector")
        if not granted.issubset(allowed):
            extra = sorted(granted - allowed)
            raise ValueError(f"Gmail connector has non-read-only scopes: {', '.join(extra)}")

    @staticmethod
    def _event_exists(session: Session, provider: str, message_id: str) -> bool:
        existing = session.scalar(
            select(ApplicationEvent.id).where(
                ApplicationEvent.source_provider == provider,
                ApplicationEvent.source_message_id == message_id,
            )
        )
        return existing is not None

    @staticmethod
    def _is_rate_limited(state: EmailSyncState) -> bool:
        if state.last_synced_at is None:
            return False
        return datetime.now(timezone.utc) - state.last_synced_at < timedelta(seconds=settings.email_sync_min_interval_seconds)
