"""SQLAlchemy credential profile model."""

from datetime import datetime
from enum import Enum

from sqlalchemy import DateTime, ForeignKey, String, func
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class CredentialProfileStatus(str, Enum):
    """Operational state for a credential profile."""

    ACTIVE = "ACTIVE"
    DISABLED = "DISABLED"
    ERROR = "ERROR"


class CredentialProfile(Base):
    """Credential profile used to submit applications to provider portals."""

    __tablename__ = "credential_profiles"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    provider: Mapped[str] = mapped_column(String(64), index=True)
    account_alias: Mapped[str] = mapped_column(String(128), index=True)
    username: Mapped[str] = mapped_column(String(255), index=True)
    secret_reference: Mapped[str] = mapped_column(String(255))
    status: Mapped[CredentialProfileStatus] = mapped_column(String(24), default=CredentialProfileStatus.ACTIVE)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )
