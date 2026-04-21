"""Application model placeholder."""

from pydantic import BaseModel


class Application(BaseModel):
    id: int | None = None
    user_id: int
    job_id: int
    status: str = "draft"
