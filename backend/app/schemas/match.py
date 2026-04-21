"""Match schema placeholders."""

from pydantic import BaseModel


class MatchSchema(BaseModel):
    job_id: int
    fit_score: float
