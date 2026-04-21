"""Persistence helpers for normalized ingestion outputs."""

from __future__ import annotations

from sqlalchemy.orm import Session

from app.db.models.job import Job
from app.schemas.job import JobNormalized


def persist_normalized_jobs(
    session: Session,
    *,
    user_id: int,
    dataset_version: str,
    jobs: list[JobNormalized],
) -> list[Job]:
    """Persist normalized jobs so matching can read from local DB state."""

    session.query(Job).filter(Job.user_id == user_id, Job.dataset_version == dataset_version).delete()

    persisted: list[Job] = []
    for job in jobs:
        row = Job(
            user_id=user_id,
            title=job.title,
            company=job.company,
            description=job.description,
            location=job.location,
            apply_link=str(job.apply_link) if job.apply_link else None,
            skills=job.skills,
            entities=job.entities,
            dataset_version=dataset_version,
        )
        session.add(row)
        persisted.append(row)

    session.commit()
    return persisted
