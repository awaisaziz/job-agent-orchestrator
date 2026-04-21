"""Job ingestion and normalization service."""

from app.schemas.job import JobIn, JobNormalized
from app.services.ingestion.normalize import normalize_job

__all__ = ["JobIn", "JobNormalized", "normalize_job"]
