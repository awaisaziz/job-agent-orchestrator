"""Job model placeholder."""

from pydantic import BaseModel


class Job(BaseModel):
    id: int | None = None
    title: str
    company: str
    location: str
