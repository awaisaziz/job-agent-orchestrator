"""Normalized saved job search result model."""

from datetime import datetime

from sqlalchemy import Boolean, DateTime, Float, ForeignKey, JSON, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class SearchResult(Base):
    """One normalized job result captured for a search session."""

    __tablename__ = "search_results"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    search_id: Mapped[int] = mapped_column(ForeignKey("job_searches.id", ondelete="CASCADE"), index=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    source: Mapped[str] = mapped_column(String(64), index=True)
    source_job_key: Mapped[str] = mapped_column(String(255), index=True)
    title: Mapped[str] = mapped_column(String(255), index=True)
    company: Mapped[str] = mapped_column(String(255), index=True)
    snippet: Mapped[str] = mapped_column(Text)
    description: Mapped[str] = mapped_column(Text)
    location: Mapped[str | None] = mapped_column(String(255), nullable=True)
    apply_url: Mapped[str | None] = mapped_column(String(1024), nullable=True)
    source_url: Mapped[str | None] = mapped_column(String(1024), nullable=True)
    skills: Mapped[list[str]] = mapped_column(JSON, default=list)
    metadata_json: Mapped[dict[str, object]] = mapped_column(JSON, default=dict)
    fit_score: Mapped[float | None] = mapped_column(Float, nullable=True)
    ats_score: Mapped[float | None] = mapped_column(Float, nullable=True)
    status: Mapped[str] = mapped_column(String(32), default="fetched", index=True)
    url_verified: Mapped[bool] = mapped_column(Boolean, default=False)
    url_status: Mapped[str | None] = mapped_column(String(32), nullable=True)  # verified, redirect, dead, requires_login
    final_apply_url: Mapped[str | None] = mapped_column(String(1024), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )
