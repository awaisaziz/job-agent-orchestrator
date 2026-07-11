"""API routes for the Chrome extension.

The extension calls these from the user's browser to identify the user, prepare a
tailored application (resume + answers for the form fields it found), and record
what it applied to.
"""

from __future__ import annotations

from fastapi import APIRouter, HTTPException

from app.db.base import Base
from app.db.models import ExternalApplication, Resume, User  # noqa: F401 — ensure tables register
from app.db.session import SessionLocal, engine
from app.schemas.extension import (
    ExtensionApplicationsResponse,
    ExtensionProfileResponse,
    PrepareApplicationRequest,
    PrepareApplicationResponse,
    RecordApplicationRequest,
    RecordApplicationResponse,
)
from app.services.extension import service as extension_service
from app.services.extension.service import ProfileNotFoundError

router = APIRouter(prefix="/extension", tags=["extension"])


def _init_schema() -> None:
    Base.metadata.create_all(bind=engine)


@router.get("/profile", response_model=ExtensionProfileResponse)
def get_profile(email: str) -> ExtensionProfileResponse:
    _init_schema()
    with SessionLocal() as session:
        try:
            return extension_service.get_profile_response(session, email)
        except ProfileNotFoundError as exc:
            raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.post("/prepare-application", response_model=PrepareApplicationResponse)
def prepare_application(payload: PrepareApplicationRequest) -> PrepareApplicationResponse:
    _init_schema()
    with SessionLocal() as session:
        try:
            return extension_service.prepare_application(session, payload)
        except ProfileNotFoundError as exc:
            raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.post("/record-application", response_model=RecordApplicationResponse)
def record_application(payload: RecordApplicationRequest) -> RecordApplicationResponse:
    _init_schema()
    with SessionLocal() as session:
        try:
            return extension_service.record_application(session, payload)
        except ProfileNotFoundError as exc:
            raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.get("/applications", response_model=ExtensionApplicationsResponse)
def list_applications(email: str) -> ExtensionApplicationsResponse:
    _init_schema()
    with SessionLocal() as session:
        return ExtensionApplicationsResponse(
            applications=extension_service.list_applications(session, email)
        )
