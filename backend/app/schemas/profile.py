"""Candidate profile schemas."""

from pydantic import BaseModel, ConfigDict, EmailStr, Field


class Profile(BaseModel):
    """Candidate profile used for matching and tailoring."""

    model_config = ConfigDict(extra="forbid", strict=True)

    user_id: int = Field(gt=0)
    full_name: str
    email: EmailStr
    skills: list[str] = Field(default_factory=list)
    years_experience: int = Field(ge=0)
    target_locations: list[str] = Field(default_factory=list)
