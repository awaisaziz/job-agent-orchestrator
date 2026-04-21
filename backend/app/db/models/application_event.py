"""SQLAlchemy immutable application event model."""

from datetime import datetime
from enum import Enum

from sqlalchemy import DateTime, ForeignKey, String, func
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class ApplicationEventType(str, Enum):
    """Lifecycle event names captured for an application run."""

    ATTEMPTED = "ATTEMPTED"
    SUBMITTED = "SUBMITTED"
    FAILED = "FAILED"
    RETRIED = "RETRIED"


class ApplicationEvent(Base):
    """Append-only application lifecycle audit events."""

    __tablename__ = "application_events"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    application_id: Mapped[int] = mapped_column(ForeignKey("applications.id", ondelete="CASCADE"), index=True)
    event_type: Mapped[ApplicationEventType] = mapped_column(String(24), index=True)
    detail: Mapped[str | None] = mapped_column(String(1024), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), index=True)
