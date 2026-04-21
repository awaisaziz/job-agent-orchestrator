"""Application matching helpers for parsed email signals."""

from __future__ import annotations

from sqlalchemy import Select, or_, select
from sqlalchemy.orm import Session

from app.db.models.application import Application
from app.db.models.job import Job
from app.services.email_ingestion.types import ParsedEmailSignal


def build_application_match_query(user_id: int, parsed: ParsedEmailSignal) -> Select[tuple[Application]]:
    """Build a best-effort query to map emails back to existing applications."""

    stmt = (
        select(Application)
        .join(Job, Job.id == Application.job_id)
        .where(Application.user_id == user_id)
        .order_by(Application.created_at.desc())
    )

    filters = []
    if parsed.company_hint:
        lowered = f"%{parsed.company_hint.lower()}%"
        filters.extend([Job.company.ilike(lowered), Application.external_reference.ilike(lowered)])

    for ref_id in parsed.reference_ids:
        like_ref = f"%{ref_id}%"
        filters.extend([Application.external_reference.ilike(like_ref), Application.external_application_id.ilike(like_ref)])

    if filters:
        stmt = stmt.where(or_(*filters))
    return stmt.limit(1)


def find_matching_application(session: Session, user_id: int, parsed: ParsedEmailSignal) -> Application | None:
    """Resolve a single application match candidate from parsed email context."""

    return session.scalar(build_application_match_query(user_id=user_id, parsed=parsed))
