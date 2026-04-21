<<<<<<< ours
"""In-memory log table model used by pipeline demo runs."""
=======
"""SQLAlchemy log model."""
>>>>>>> theirs

from __future__ import annotations

<<<<<<< ours
from datetime import datetime, timezone
from itertools import count

from pydantic import BaseModel, Field
=======
from sqlalchemy import DateTime, ForeignKey, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column
>>>>>>> theirs

from app.db.base import Base

<<<<<<< ours
class Log(BaseModel):
    id: int | None = None
    level: str = "info"
    stage: str
    message: str
    run_id: str
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


_LOGS_TABLE: list[Log] = []
_LOG_ID_COUNTER = count(1)


def insert_log(*, stage: str, message: str, run_id: str, level: str = "info") -> Log:
    """Persist a log entry in the in-memory logs table."""
    row = Log(
        id=next(_LOG_ID_COUNTER),
        level=level,
        stage=stage,
        message=message,
        run_id=run_id,
    )
    _LOGS_TABLE.append(row)
    return row


def list_logs_for_run(run_id: str) -> list[Log]:
    """Fetch all logs for a pipeline run."""
    return [log for log in _LOGS_TABLE if log.run_id == run_id]
=======

class Log(Base):
    """System and per-step agent logs."""

    __tablename__ = "logs"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    user_id: Mapped[int | None] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"), nullable=True, index=True)
    application_id: Mapped[int | None] = mapped_column(
        ForeignKey("applications.id", ondelete="SET NULL"), nullable=True, index=True
    )
    level: Mapped[str] = mapped_column(String(16), default="INFO")
    step: Mapped[str] = mapped_column(String(128), default="general")
    message: Mapped[str] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )
>>>>>>> theirs
