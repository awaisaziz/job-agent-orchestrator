"""Normalization helpers for ingestion pipelines."""

from __future__ import annotations

import re
from typing import Any

from app.schemas.job import JobIn, JobNormalized

_SKILL_KEYWORDS = {
    "python",
    "fastapi",
    "sql",
    "aws",
    "docker",
    "react",
    "typescript",
    "etl",
}

_ENTITY_PATTERN = re.compile(r"\b[A-Z][a-zA-Z0-9+&.-]{1,}\b")


def normalize_job(job_in: JobIn) -> JobNormalized:
    """Normalize raw ingestion payload into canonical job schema."""

    description = _clean_whitespace(job_in.raw_description)
    skills = _extract_skills(description)
    entities = _extract_entities(description)
    if job_in.raw_company and job_in.raw_company not in entities:
        entities.append(job_in.raw_company)

    return JobNormalized(
        title=_normalize_title(job_in.raw_title),
        company=_normalize_company(job_in.raw_company),
        description=description,
        skills=skills,
        entities=entities,
        location=_normalize_location(job_in.raw_location),
        apply_link=job_in.raw_apply_link,
    )


def normalize_raw_record(raw_record: dict[str, Any]) -> JobNormalized:
    """Normalize an untyped raw record from csv/jsonl into JobNormalized."""

    payload = JobIn.model_validate(raw_record)
    return normalize_job(payload)


def _normalize_title(title: str) -> str:
    return _clean_whitespace(title).title()


def _normalize_company(company: str) -> str:
    return _clean_whitespace(company)


def _normalize_location(location: str | None) -> str | None:
    if location is None:
        return None
    cleaned = _clean_whitespace(location)
    return cleaned or None


def _extract_skills(description: str) -> list[str]:
    tokens = {token.lower() for token in re.findall(r"[a-zA-Z0-9+#.]+", description)}
    return sorted(skill for skill in _SKILL_KEYWORDS if skill in tokens)


def _extract_entities(description: str) -> list[str]:
    entities = {match.group(0) for match in _ENTITY_PATTERN.finditer(description)}
    return sorted(entities)


def _clean_whitespace(value: str) -> str:
    return " ".join(value.strip().split())
