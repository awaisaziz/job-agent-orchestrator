"""SQLAlchemy model for applications submitted via the Chrome extension.

Extension applications target arbitrary external job URLs (not internal
SearchResult rows), so they get their own lightweight table.
"""

from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class ExternalApplication(Base):
    """A job application the browser extension filled/submitted on an external site."""

    __tablename__ = "external_applications"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    job_title: Mapped[str] = mapped_column(String(255))
    company: Mapped[str] = mapped_column(String(255))
    apply_url: Mapped[str] = mapped_column(String(2048))
    status: Mapped[str] = mapped_column(String(32), default="applied", index=True)
    source: Mapped[str] = mapped_column(String(32), default="extension")
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
