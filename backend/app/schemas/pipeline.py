<<<<<<< ours
"""Pipeline response schemas."""
=======
"""Pipeline-level schemas and shared enums."""
>>>>>>> theirs

from datetime import datetime
from enum import Enum

from pydantic import BaseModel, ConfigDict, Field

<<<<<<< ours
class StageResult(BaseModel):
    name: str
    status: str
    duration_ms: int


class JobTimelineStage(BaseModel):
    name: str
    status: str
    progress_percent: int


class JobTimelineEntry(BaseModel):
    job_id: str
    title: str
    company: str
    stages: list[JobTimelineStage]


class PipelineLogEntry(BaseModel):
    id: int
    level: str
    stage: str
    message: str
    created_at: str


class PipelineRunDemoResponse(BaseModel):
    run_id: str
    jobs_fetched: int
    jobs_matched: int
    resumes_generated: int
    applications_sent: int
    stage_results: list[StageResult]
    job_timelines: list[JobTimelineEntry]
    logs: list[PipelineLogEntry]
=======

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
>>>>>>> theirs
