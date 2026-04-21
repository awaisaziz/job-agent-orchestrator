"""Resume model placeholder."""

from pydantic import BaseModel


class Resume(BaseModel):
    id: int | None = None
    user_id: int
    content: str
