"""Schemas for the persisted search and application workflow."""

from __future__ import annotations

from datetime import datetime
from enum import Enum

from pydantic import BaseModel, ConfigDict, EmailStr, Field


class WorkflowStatus(str, Enum):
    SAVED = "saved"
    FETCHED = "fetched"
    NORMALIZED = "normalized"
    MATCHED = "matched"
    TAILORED = "tailored"
    PENDING_APPROVAL = "pending_approval"
    APPROVED = "approved"
    APPLIED = "applied"
    FAILED = "failed"
    REJECTED = "rejected"
    INTERVIEW = "interview"
    CLOSED = "closed"


class ResumeArtifact(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)

    resume_id: int
    version: int
    kind: str
    artifact_path: str | None = None
    source_filename: str | None = None
    created_at: datetime


class ProfileSummary(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)

    user_id: int
    full_name: str
    email: EmailStr
    skills: list[str] = Field(default_factory=list)
    target_locations: list[str] = Field(default_factory=list)
    base_resume: ResumeArtifact
    parsed_summary: str


class ProfileIntakeRequest(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)

    email: EmailStr
    full_name: str | None = None
    location: str | None = None
    resume_filename: str
    resume_text: str = Field(min_length=1)


class ProfileIntakeResponse(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)

    profile: ProfileSummary


class JobSearchRequest(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)

    user_id: int = Field(gt=0)
    position: str = Field(min_length=2)
    location: str | None = None
    email: EmailStr


class SearchResultItem(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)

    result_id: int
    source: str
    title: str
    company: str
    snippet: str
    description: str
    location: str | None = None
    apply_url: str | None = None
    source_url: str | None = None
    skills: list[str] = Field(default_factory=list)
    fit_score: float | None = None
    ats_score: float | None = None
    status: WorkflowStatus
    selected: bool = False
    url_verified: bool = False
    url_status: str | None = None
    final_apply_url: str | None = None


class JobSearchResponse(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)

    search_id: int
    status: WorkflowStatus
    position: str
    location: str | None = None
    results: list[SearchResultItem] = Field(default_factory=list)


class MatchJobRequest(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)

    search_id: int = Field(gt=0)


class MatchResultItem(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)

    result_id: int
    fit_score: float = Field(ge=0.0, le=1.0)
    matched_skills: list[str] = Field(default_factory=list)
    missing_skills: list[str] = Field(default_factory=list)


class MatchJobsResponse(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)

    search_id: int
    results: list[MatchResultItem] = Field(default_factory=list)


class PrepareApplicationsRequest(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)

    search_id: int = Field(gt=0)
    result_ids: list[int] = Field(min_length=1)


class ApplicationQueueItem(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)

    application_id: int
    search_result_id: int
    company: str
    title: str
    source: str
    fit_score: float | None = None
    ats_score: float | None = None
    status: WorkflowStatus
    waiting_for_human_approval: bool
    duplicate_blocked: bool
    retries_used: int
    apply_url: str | None = None
    tailored_resume: ResumeArtifact | None = None
    updated_at: datetime


class PrepareApplicationsResponse(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)

    search_id: int
    applications: list[ApplicationQueueItem] = Field(default_factory=list)


class TailorResumeRequest(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)

    application_ids: list[int] = Field(min_length=1)
    model_name: str


class TailorResumeResult(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)

    application_id: int
    resume_version_id: int
    ats_score: float = Field(ge=0.0, le=100.0)
    matched_skills: list[str] = Field(default_factory=list)
    missing_skills: list[str] = Field(default_factory=list)
    artifact_path: str
    status: WorkflowStatus


class TailorResumeResponse(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)

    results: list[TailorResumeResult] = Field(default_factory=list)


class ApproveApplicationsRequest(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)

    application_ids: list[int] = Field(min_length=1)


class SubmitApplicationsRequest(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)

    application_ids: list[int] = Field(min_length=1)


class ApplicationEventRecord(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)

    event: str
    detail: str | None = None
    created_at: datetime


class SubmitApplicationResult(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)

    application_id: int
    status: WorkflowStatus
    attempted_actions: list[str] = Field(default_factory=list)
    failure_reason: str | None = None


class SubmitApplicationsResponse(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)

    results: list[SubmitApplicationResult] = Field(default_factory=list)


class ApplicationListResponse(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)

    applications: list[ApplicationQueueItem] = Field(default_factory=list)


class SearchWorkspaceResponse(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)

    search_id: int
    status: WorkflowStatus
    position: str
    location: str | None = None
    profile: ProfileSummary
    results: list[SearchResultItem] = Field(default_factory=list)
    applications: list[ApplicationQueueItem] = Field(default_factory=list)


class EmailIntegrationResponse(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)

    provider: str
    configured: bool
    mode: str
    detail: str
    last_synced_at: datetime | None = None


class EmailSyncRequest(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)

    user_id: int = Field(gt=0)


class EmailSyncResponse(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)

    processed_messages: int
    inserted_events: int
    rate_limited: bool
    detail: str
    last_synced_at: datetime | None = None
