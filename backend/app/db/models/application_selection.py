"""Persistent job selection queue entries."""

from datetime import datetime

from sqlalchemy import Boolean, DateTime, ForeignKey, func
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class ApplicationSelection(Base):
    """Tracks which search results the user queued for application work."""

    __tablename__ = "application_selections"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    search_id: Mapped[int] = mapped_column(ForeignKey("job_searches.id", ondelete="CASCADE"), index=True)
    search_result_id: Mapped[int] = mapped_column(ForeignKey("search_results.id", ondelete="CASCADE"), index=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    selected: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )
