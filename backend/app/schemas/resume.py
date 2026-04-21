"""Resume tailoring schemas."""

from pydantic import BaseModel, ConfigDict


class TailoredResume(BaseModel):
    """Tailored resume artifact generated from base resume + job context."""

    model_config = ConfigDict(extra="forbid", strict=True)

    base_resume: str
    tailored_resume: str
    truth_preserved: bool
    notes: list[str]
