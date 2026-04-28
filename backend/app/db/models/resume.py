"""SQLAlchemy resume model."""

from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class Resume(Base):
    """Base or tailored resume content snapshots."""

    __tablename__ = "resumes"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    application_id: Mapped[int | None] = mapped_column(ForeignKey("applications.id", ondelete="SET NULL"), nullable=True)
    search_result_id: Mapped[int | None] = mapped_column(ForeignKey("search_results.id", ondelete="SET NULL"), nullable=True)
    version: Mapped[int] = mapped_column(default=1)
    kind: Mapped[str] = mapped_column(String(32), default="base", index=True)
    source_filename: Mapped[str | None] = mapped_column(String(255), nullable=True)
    artifact_path: Mapped[str | None] = mapped_column(String(1024), nullable=True)
    content: Mapped[str] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )
