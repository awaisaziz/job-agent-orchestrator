"""Matching schemas."""

from pydantic import BaseModel, ConfigDict, Field


class MatchResult(BaseModel):
    """Match score output for a profile and normalized job."""

    model_config = ConfigDict(extra="forbid", strict=True)

    job_title: str
    company: str
    similarity: float = Field(ge=0.0, le=1.0)
    matched_skills: list[str] = Field(default_factory=list)
