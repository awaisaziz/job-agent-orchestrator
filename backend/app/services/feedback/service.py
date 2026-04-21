"""Feedback service for application outcomes and manual feedback."""

from dataclasses import dataclass, field
from datetime import datetime


@dataclass(slots=True)
class FeedbackRecord:
    application_id: int
    outcome: str
    notes: str | None = None
    created_at: datetime = field(default_factory=datetime.utcnow)


class FeedbackService:
    """In-memory demo feedback recorder."""

    def __init__(self) -> None:
        self._records: list[FeedbackRecord] = []

    def record_outcome(self, application_id: int, outcome: str, notes: str | None = None) -> FeedbackRecord:
        record = FeedbackRecord(application_id=application_id, outcome=outcome, notes=notes)
        self._records.append(record)
        return record

    def list_records(self) -> list[FeedbackRecord]:
        return list(self._records)
