"""Job ingestion and normalization service."""

from app.schemas.job import JobIn, JobNormalized


def normalize_job(job_in: JobIn) -> JobNormalized:
    """Normalize raw ingestion payload into canonical job schema."""

    skills = _extract_skills(job_in.raw_description)
    return JobNormalized(
        title=job_in.raw_title.strip(),
        company=job_in.raw_company.strip(),
        description=job_in.raw_description.strip(),
        skills=skills,
        location=job_in.raw_location.strip() if job_in.raw_location else None,
        apply_link=job_in.raw_apply_link,
    )


def _extract_skills(description: str) -> list[str]:
    keywords = ["python", "fastapi", "sql", "aws", "docker", "react", "typescript"]
    text = description.lower()
    return [skill for skill in keywords if skill in text]
