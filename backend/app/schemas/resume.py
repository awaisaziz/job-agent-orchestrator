"""Resume schema placeholders."""

from pydantic import BaseModel


class ResumeSchema(BaseModel):
    summary: str
    skills: list[str] = []
