"""Schemas for the Chrome extension API.

The extension runs in the user's real browser, scans open job tabs, and asks the
backend to (a) identify the user, (b) tailor a resume + answer the actual form
fields it found on the page, and (c) record what it applied to.
"""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, ConfigDict, EmailStr, Field


class ExtensionProfileResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    user_id: int
    full_name: str
    email: EmailStr
    phone: str | None = None
    skills: list[str] = Field(default_factory=list)
    years_experience: int = 0
    base_resume_text: str
    summary: str


class FormFieldSpec(BaseModel):
    """One fillable field the content script discovered on the application page."""

    model_config = ConfigDict(extra="ignore")

    name: str  # stable key the content script uses to map the answer back (id/name/index)
    label: str = ""  # human label (from <label>, aria-label, placeholder, nearby text)
    type: str = "text"  # text | textarea | email | tel | url | select | checkbox | radio | number
    options: list[str] = Field(default_factory=list)  # for select/radio
    required: bool = False


class PrepareApplicationRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    email: EmailStr
    job_title: str = ""
    company: str = ""
    job_description: str = ""
    apply_url: str = ""
    fields: list[FormFieldSpec] = Field(default_factory=list)


class PrepareApplicationResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    tailored_resume: str
    cover_letter: str
    # name (content-script key) -> value to fill.
    answers: dict[str, str] = Field(default_factory=dict)
    matched_skills: list[str] = Field(default_factory=list)
    missing_skills: list[str] = Field(default_factory=list)
    model_used: str
    llm_used: bool


class RecordApplicationRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    email: EmailStr
    job_title: str
    company: str = ""
    apply_url: str = ""
    status: str = "applied"  # applied | needs_review | skipped | failed
    notes: str | None = None
    notify: bool = False


class RecordApplicationResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    application_id: int
    recorded: bool
    notified: bool


class ExtensionApplicationItem(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: int
    job_title: str
    company: str
    apply_url: str
    status: str
    source: str
    notes: str | None = None
    created_at: datetime


class ExtensionApplicationsResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    applications: list[ExtensionApplicationItem] = Field(default_factory=list)
