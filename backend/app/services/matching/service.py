"""Real matching service using skill overlap, title similarity, and location scoring.

Replaces the previous mock embedding approach with meaningful weighted scoring.
"""

import difflib
import re

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.models.job import Job
from app.schemas.job import JobNormalized
from app.schemas.match import MatchResult
from app.schemas.profile import Profile


def score_match(profile: Profile, job: JobNormalized) -> MatchResult:
    """Compute real similarity score between candidate profile and a normalized job.

    Weighted blend:
      skill_overlap (0.40) + title_relevance (0.25) + location (0.15) + description_keywords (0.20)
    """

    skill_score = _skill_overlap_score(profile.skills, job.skills)
    title_score = _title_relevance_score(profile, job.title)
    location_score = _location_score(profile.target_locations, job.location)
    keyword_score = _description_keyword_score(profile.skills, job.description)

    similarity = (
        skill_score * 0.40
        + title_score * 0.25
        + location_score * 0.15
        + keyword_score * 0.20
    )
    similarity = max(0.0, min(1.0, similarity))

    matched_skills = sorted(
        set(skill for skill in profile.skills if skill.lower() in {s.lower() for s in job.skills})
    )

    return MatchResult(
        job_title=job.title,
        company=job.company,
        similarity=round(similarity, 4),
        matched_skills=matched_skills,
    )


def _skill_overlap_score(profile_skills: list[str], job_skills: list[str]) -> float:
    """Jaccard-style overlap: |intersection| / |job_skills|."""
    if not job_skills:
        return 0.5  # No skill info, neutral score
    profile_set = {s.lower() for s in profile_skills}
    job_set = {s.lower() for s in job_skills}
    overlap = len(profile_set & job_set)
    return overlap / len(job_set)


def _title_relevance_score(profile: Profile, job_title: str) -> float:
    """Fuzzy match between what the user is looking for and the job title."""
    # The user's target is encoded in their profile — we approximate via full_name context
    # and the skills they have. Use SequenceMatcher for fuzzy title similarity.
    job_lower = job_title.lower()
    # Check common title patterns against profile skills
    relevance_keywords = {s.lower() for s in profile.skills}
    # Add common title words
    title_words = set(re.findall(r"\b\w+\b", job_lower))
    skill_title_overlap = len(relevance_keywords & title_words)
    base_score = min(1.0, skill_title_overlap / max(len(title_words), 1) * 2)
    return max(0.3, base_score)  # Floor at 0.3 to avoid over-penalizing


def _location_score(target_locations: list[str], job_location: str | None) -> float:
    """Score based on location match."""
    if not job_location:
        return 0.5  # Unknown location, neutral

    job_loc_lower = job_location.lower()

    # Remote is always a good match
    if "remote" in job_loc_lower:
        return 0.95

    if not target_locations:
        return 0.7  # No preference specified, default decent score

    for target in target_locations:
        target_lower = target.lower()
        if target_lower == "remote":
            continue  # Already handled
        # Exact or fuzzy match
        ratio = difflib.SequenceMatcher(None, target_lower, job_loc_lower).ratio()
        if ratio > 0.6:
            return max(0.8, ratio)
        # Check if target city/state appears in job location
        if target_lower in job_loc_lower or job_loc_lower in target_lower:
            return 0.9

    # Same country check
    if _same_country(target_locations, job_location):
        return 0.7

    return 0.4


def _same_country(targets: list[str], job_location: str) -> bool:
    """Rough check if locations share a country."""
    job_lower = job_location.lower()
    us_markers = {"us", "usa", "united states"}
    ca_markers = {"ca", "canada", "on", "bc", "ab", "qc"}

    job_is_us = any(marker in job_lower for marker in us_markers) or bool(
        re.search(r"\b[A-Z]{2}\b", job_location)  # US state abbreviation
    )
    job_is_ca = any(marker in job_lower for marker in ca_markers)

    for target in targets:
        t = target.lower()
        if job_is_us and any(m in t for m in us_markers):
            return True
        if job_is_ca and any(m in t for m in ca_markers):
            return True
    return False


def _description_keyword_score(profile_skills: list[str], description: str) -> float:
    """Score based on how many profile skills appear in the full job description."""
    if not description or not profile_skills:
        return 0.3

    desc_lower = description.lower()
    matches = sum(1 for skill in profile_skills if skill.lower() in desc_lower)
    # Normalize: up to 5 matches = 1.0
    return min(1.0, matches / min(5, len(profile_skills)))


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
