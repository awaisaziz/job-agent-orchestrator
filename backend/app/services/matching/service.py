"""Matching service using embedding-based cosine similarity with mock fallback."""

import math

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.models.job import Job
from app.schemas.job import JobNormalized
from app.schemas.match import MatchResult
from app.schemas.profile import Profile


def score_match(profile: Profile, job: JobNormalized) -> MatchResult:
    """Compute similarity score between candidate profile and a normalized job."""

    profile_text = " ".join([profile.full_name, *profile.skills]).strip()
    job_text = " ".join([job.title, job.company, job.description, *job.skills]).strip()
    profile_vector = _embedding(profile_text)
    job_vector = _embedding(job_text)
    similarity = _cosine_similarity(profile_vector, job_vector)
    matched_skills = sorted(set(skill for skill in profile.skills if skill.lower() in {s.lower() for s in job.skills}))
    return MatchResult(
        job_title=job.title,
        company=job.company,
        similarity=round(similarity, 4),
        matched_skills=matched_skills,
    )


def load_jobs_for_matching(session: Session, user_id: int, dataset_version: str | None = None) -> list[JobNormalized]:
    """Load normalized jobs from local DB tables used by matching."""

    query = select(Job).where(Job.user_id == user_id)
    if dataset_version:
        query = query.where(Job.dataset_version == dataset_version)

    rows = session.execute(query.order_by(Job.id.desc())).scalars().all()
    return [
        JobNormalized(
            title=row.title,
            company=row.company,
            description=row.description,
            skills=row.skills or [],
            entities=row.entities or [],
            location=row.location,
            apply_link=row.apply_link,
        )
        for row in rows
    ]


def _embedding(text: str) -> list[float]:
    """Mock fallback embedding function for demo mode."""

    if not text:
        return [0.0, 0.0, 0.0, 0.0]
    total = sum(ord(char) for char in text)
    length = float(len(text))
    alpha = sum(1 for char in text.lower() if char.isalpha())
    spaces = text.count(" ") + 1
    return [total % 997 / 997.0, length / 1000.0, alpha / 1000.0, spaces / 1000.0]


def _cosine_similarity(left: list[float], right: list[float]) -> float:
    numerator = sum(lv * rv for lv, rv in zip(left, right, strict=True))
    left_norm = math.sqrt(sum(v * v for v in left))
    right_norm = math.sqrt(sum(v * v for v in right))
    if left_norm == 0.0 or right_norm == 0.0:
        return 0.0
    return max(0.0, min(1.0, numerator / (left_norm * right_norm)))
