"""Persisted job search and application workflow routes."""

from __future__ import annotations

import os

from fastapi import APIRouter, HTTPException

from app.db.base import Base
from app.db.models import Application, ApplicationEvent, ApplicationSelection, JobSearch, Resume, SearchResult, User
from app.db.session import SessionLocal, engine
from app.schemas.workflow import (
    ApplicationListResponse,
    EmailIntegrationResponse,
    EmailSyncRequest,
    EmailSyncResponse,
    JobSearchRequest,
    JobSearchResponse,
    MatchJobsResponse,
    MatchJobRequest,
    PrepareApplicationsRequest,
    PrepareApplicationsResponse,
    ProfileIntakeRequest,
    ProfileIntakeResponse,
    SearchWorkspaceResponse,
    SubmitApplicationsRequest,
    SubmitApplicationsResponse,
    TailorResumeRequest,
    TailorResumeResponse,
    ApproveApplicationsRequest,
)
from app.services.workflow.service import WorkflowService

router = APIRouter(tags=["workflow"])
workflow_service = WorkflowService()


def _init_schema() -> None:
    _ = (Application, ApplicationEvent, ApplicationSelection, JobSearch, Resume, SearchResult, User)
    Base.metadata.create_all(bind=engine)


def _email_configured() -> bool:
    return bool(os.getenv("EMAIL_INGESTION_CLIENT_ID") and os.getenv("EMAIL_INGESTION_CLIENT_SECRET"))


@router.post("/profile/intake", response_model=ProfileIntakeResponse)
def intake_profile(payload: ProfileIntakeRequest) -> ProfileIntakeResponse:
    _init_schema()
    with SessionLocal() as session:
        try:
            result = workflow_service.intake_profile(
                session=session,
                email=payload.email,
                resume_filename=payload.resume_filename,
                resume_text=payload.resume_text,
                location=payload.location,
                full_name=payload.full_name,
                phone=payload.phone,
            )
        except ValueError as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc
    return ProfileIntakeResponse(profile=result.profile)


@router.post("/search/jobs", response_model=JobSearchResponse)
def search_jobs(payload: JobSearchRequest) -> JobSearchResponse:
    _init_schema()
    with SessionLocal() as session:
        try:
            search = workflow_service.search_jobs(
                session=session,
                user_id=payload.user_id,
                position=payload.position,
                location=payload.location,
            )
            workspace = workflow_service.get_workspace(session=session, search_id=search.id)
        except ValueError as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc
    return JobSearchResponse(
        search_id=workspace.search_id,
        status=workspace.status,
        position=workspace.position,
        location=workspace.location,
        results=workspace.results,
    )


@router.post("/match/jobs", response_model=MatchJobsResponse)
def match_jobs(payload: MatchJobRequest) -> MatchJobsResponse:
    _init_schema()
    with SessionLocal() as session:
        try:
            results = workflow_service.match_jobs(session=session, search_id=payload.search_id)
        except ValueError as exc:
            raise HTTPException(status_code=404, detail=str(exc)) from exc
    return MatchJobsResponse(search_id=payload.search_id, results=results)


@router.post("/applications/prepare", response_model=PrepareApplicationsResponse)
def prepare_applications(payload: PrepareApplicationsRequest) -> PrepareApplicationsResponse:
    _init_schema()
    with SessionLocal() as session:
        try:
            workflow_service.prepare_applications(session=session, search_id=payload.search_id, result_ids=payload.result_ids)
            workspace = workflow_service.get_workspace(session=session, search_id=payload.search_id)
        except ValueError as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc
    return PrepareApplicationsResponse(search_id=payload.search_id, applications=workspace.applications)


@router.post("/resumes/tailor", response_model=TailorResumeResponse)
def tailor_resumes(payload: TailorResumeRequest) -> TailorResumeResponse:
    _init_schema()
    with SessionLocal() as session:
        try:
            results = workflow_service.tailor_applications(
                session=session,
                application_ids=payload.application_ids,
                model_name=payload.model_name,
            )
        except ValueError as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc
    return TailorResumeResponse(results=results)


@router.post("/applications/approve", response_model=PrepareApplicationsResponse)
def approve_applications(payload: ApproveApplicationsRequest) -> PrepareApplicationsResponse:
    _init_schema()
    with SessionLocal() as session:
        try:
            applications = workflow_service.approve_applications(session=session, application_ids=payload.application_ids)
            search_id = None
            for application in applications:
                if application.search_result_id is None:
                    continue
                search_result = session.get(SearchResult, application.search_result_id)
                if search_result is not None:
                    search_id = search_result.search_id
                    break
            if search_id is None:
                raise ValueError("Approved applications are missing search context")
            workspace = workflow_service.get_workspace(session=session, search_id=search_id)
        except ValueError as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc
    return PrepareApplicationsResponse(search_id=workspace.search_id, applications=workspace.applications)


@router.post("/applications/submit", response_model=SubmitApplicationsResponse)
def submit_applications(payload: SubmitApplicationsRequest) -> SubmitApplicationsResponse:
    _init_schema()
    with SessionLocal() as session:
        results = workflow_service.submit_applications(session=session, application_ids=payload.application_ids)
    return SubmitApplicationsResponse(results=results)


@router.get("/applications", response_model=ApplicationListResponse)
def list_applications(user_id: int | None = None) -> ApplicationListResponse:
    _init_schema()
    with SessionLocal() as session:
        applications = workflow_service.list_applications(session=session, user_id=user_id)
    return ApplicationListResponse(applications=applications)


@router.get("/jobs/searches/{search_id}", response_model=SearchWorkspaceResponse)
def get_workspace(search_id: int) -> SearchWorkspaceResponse:
    _init_schema()
    with SessionLocal() as session:
        try:
            return workflow_service.get_workspace(session=session, search_id=search_id)
        except ValueError as exc:
            raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.get("/integrations/email/status", response_model=EmailIntegrationResponse)
def get_email_status(user_id: int | None = None) -> EmailIntegrationResponse:
    _init_schema()
    with SessionLocal() as session:
        return workflow_service.email_status(
            session=session,
            user_id=user_id,
            configured=_email_configured(),
        )


@router.post("/integrations/email/sync", response_model=EmailSyncResponse)
def sync_email(payload: EmailSyncRequest) -> EmailSyncResponse:
    _init_schema()
    with SessionLocal() as session:
        configured = _email_configured()
        if not configured:
            status = workflow_service.email_status(session=session, user_id=payload.user_id, configured=False)
            return EmailSyncResponse(
                processed_messages=0,
                inserted_events=0,
                rate_limited=False,
                detail=status.detail,
                last_synced_at=status.last_synced_at,
            )

        status = workflow_service.email_status(session=session, user_id=payload.user_id, configured=True)
        return EmailSyncResponse(
            processed_messages=0,
            inserted_events=0,
            rate_limited=False,
            detail="Email connector is configured, but live mailbox sync still requires provider-specific connector wiring.",
            last_synced_at=status.last_synced_at,
        )
