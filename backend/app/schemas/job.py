"""Job ingestion and normalization schemas."""

from datetime import datetime

from pydantic import AnyHttpUrl, BaseModel, ConfigDict, Field


class JobIn(BaseModel):
    """Raw incoming job post payload."""

    model_config = ConfigDict(extra="forbid", strict=True)

    source: str
    raw_title: str
    raw_company: str
    raw_description: str
    raw_location: str | None = None
    raw_apply_link: AnyHttpUrl | None = None
    captured_at: datetime = Field(default_factory=datetime.utcnow)


class JobNormalized(BaseModel):
    """Canonical normalized job payload used by downstream agents."""

    model_config = ConfigDict(extra="forbid", strict=True)

    title: str
    company: str
    description: str
    skills: list[str] = Field(default_factory=list)
    location: str | None = None
    apply_link: AnyHttpUrl | None = None
