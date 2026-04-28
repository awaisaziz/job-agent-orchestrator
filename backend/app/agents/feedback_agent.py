"""Feedback agent wrapper for inbox sync."""

from dataclasses import dataclass, field

from sqlalchemy.orm import Session

from app.services.email_ingestion.service import EmailIngestionService


@dataclass(slots=True)
class FeedbackAgentOutput:
    processed_messages: int
    inserted_events: int
    rate_limited: bool
    logs: list[str] = field(default_factory=list)


def run_feedback_agent(*, service: EmailIngestionService, session: Session, user_id: int) -> FeedbackAgentOutput:
    logs = [f"feedback_agent:start user_id={user_id}"]
    outcome = service.sync(session=session, user_id=user_id)
    logs.append(
        "feedback_agent:completed "
        f"processed={outcome.processed_messages} inserted={outcome.inserted_events} rate_limited={outcome.rate_limited}"
    )
    return FeedbackAgentOutput(
        processed_messages=outcome.processed_messages,
        inserted_events=outcome.inserted_events,
        rate_limited=outcome.rate_limited,
        logs=logs,
    )
