"""Pipeline-level schemas and shared enums."""

from datetime import datetime
from enum import Enum

from pydantic import BaseModel, ConfigDict, Field

from app.services.llm_gateway.registry import DEFAULT_MODEL_NAME


class PipelineStatus(str, Enum):
    """Lifecycle status for pipeline steps and runs."""

    PENDING = "PENDING"
    PROCESSING = "PROCESSING"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"


class ApplicationEventName(str, Enum):
    """Audit event types for application lifecycle tracking."""

    ATTEMPTED = "ATTEMPTED"
    SUBMITTED = "SUBMITTED"
    FAILED = "FAILED"
    RETRIED = "RETRIED"
    APPLICATION_RECEIVED = "APPLICATION_RECEIVED"
    INTERVIEW_INVITE = "INTERVIEW_INVITE"
    REJECTION = "REJECTION"
    FOLLOW_UP_NEEDED = "FOLLOW_UP_NEEDED"


class PipelineRunRequest(BaseModel):
    """Input schema for demo pipeline execution."""

    model_config = ConfigDict(extra="forbid", strict=True)

    model_name: str = Field(default=DEFAULT_MODEL_NAME)


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
    model_name: str
    llm_provider: str | None = None
    logs: list[str] = Field(default_factory=list)


class ApplicationAuditEvent(BaseModel):
    """One immutable event entry in the application history."""

    model_config = ConfigDict(extra="forbid", strict=True)

    event: ApplicationEventName
    created_at: datetime
    detail: str | None = None


class ApplicationAuditRecord(BaseModel):
    """Audit trail of a single application run."""

    model_config = ConfigDict(extra="forbid", strict=True)

    application_id: str
    run_id: str
    job_id: str
    target_company: str
    target_title: str
    credential_profile_id: str
    credential_provider: str
    credential_account_alias: str
    resume_id: str
    resume_version: int
    cover_letter_id: str | None = None
    cover_letter_version: int | None = None
    generation_provider: str | None = None
    generation_model: str
    submitted_at: datetime | None = None
    external_application_id: str | None = None
    external_application_url: str | None = None
    status: PipelineStatus
    events: list[ApplicationAuditEvent] = Field(default_factory=list)


class ApplicationAuditList(BaseModel):
    """Container for listing audit records."""

    model_config = ConfigDict(extra="forbid", strict=True)

    applications: list[ApplicationAuditRecord] = Field(default_factory=list)
