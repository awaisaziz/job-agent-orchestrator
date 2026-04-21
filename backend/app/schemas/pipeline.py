"""Pipeline-level schemas and shared enums."""

from datetime import datetime
from enum import Enum

from pydantic import BaseModel, ConfigDict, Field


class PipelineStatus(str, Enum):
    """Lifecycle status for pipeline steps and runs."""

    PENDING = "PENDING"
    PROCESSING = "PROCESSING"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"


class PipelineRunResult(BaseModel):
    """Orchestration response for one pipeline execution."""

    model_config = ConfigDict(extra="forbid", strict=True)

    run_id: str
    status: PipelineStatus
    started_at: datetime
    finished_at: datetime | None = None
    jobs_ingested: int = Field(ge=0)
    matches_found: int = Field(ge=0)
    resume_generated: bool
    logs: list[str] = Field(default_factory=list)
