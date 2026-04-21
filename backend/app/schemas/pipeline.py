"""Pipeline schema placeholders."""

from pydantic import BaseModel


class PipelineResult(BaseModel):
    jobs_ingested: int
    matches_found: int
    applications_submitted: int
