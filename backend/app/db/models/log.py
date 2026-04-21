"""Log model placeholder."""

from datetime import datetime

from pydantic import BaseModel


class Log(BaseModel):
    id: int | None = None
    level: str = "info"
    message: str
    created_at: datetime = datetime.utcnow()
