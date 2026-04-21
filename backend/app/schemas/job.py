"""Job schema placeholders."""

from pydantic import BaseModel


class JobSchema(BaseModel):
    title: str
    company: str
    score: float | None = None
