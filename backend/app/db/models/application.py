"""SQLAlchemy application model."""

from datetime import datetime

from sqlalchemy import DateTime, Float, ForeignKey, String, func
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base
from app.schemas.pipeline import PipelineStatus


class Application(Base):
    """Submitted (or attempted) job application status."""

    __tablename__ = "applications"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    job_id: Mapped[int] = mapped_column(ForeignKey("jobs.id", ondelete="CASCADE"), index=True)
    status: Mapped[PipelineStatus] = mapped_column(String(24), default=PipelineStatus.PENDING)
    match_score: Mapped[float | None] = mapped_column(Float, nullable=True)
    external_reference: Mapped[str | None] = mapped_column(String(255), nullable=True)
    credential_profile_id: Mapped[int | None] = mapped_column(
        ForeignKey("credential_profiles.id", ondelete="SET NULL"), nullable=True, index=True
    )
    resume_id: Mapped[int | None] = mapped_column(ForeignKey("resumes.id", ondelete="SET NULL"), nullable=True)
    resume_version: Mapped[int | None] = mapped_column(nullable=True)
    cover_letter_id: Mapped[int | None] = mapped_column(
        ForeignKey("cover_letters.id", ondelete="SET NULL"), nullable=True
    )
    cover_letter_version: Mapped[int | None] = mapped_column(nullable=True)
    submitted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    external_application_id: Mapped[str | None] = mapped_column(String(255), nullable=True)
    external_application_url: Mapped[str | None] = mapped_column(String(1024), nullable=True)
    generation_provider: Mapped[str | None] = mapped_column(String(64), nullable=True)
    generation_model: Mapped[str | None] = mapped_column(String(128), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )
