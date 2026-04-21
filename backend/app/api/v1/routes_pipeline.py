"""Pipeline orchestration endpoints."""

from datetime import datetime, timezone

from fastapi import APIRouter, HTTPException

from app.agents.apply_agent import ApplyAgentInput, run_apply_agent
from app.agents.job_agent import JobAgentInput, run_job_agent
from app.agents.match_agent import MatchAgentInput, run_match_agent
from app.agents.resume_agent import ResumeAgentInput, run_resume_agent
from app.db.base import Base
from app.db.models.user import User
from app.db.session import SessionLocal, engine
from app.schemas.job import JobIn
from app.schemas.pipeline import (
    ApplicationAuditEvent,
    ApplicationAuditList,
    ApplicationAuditRecord,
    ApplicationEventName,
    PipelineRunRequest,
    PipelineRunResult,
    PipelineStatus,
)
from app.schemas.profile import Profile
from app.db.models.credential_profile import CredentialProfileStatus
from app.services.ingestion.pipeline import run_dataset_pipeline
from app.services.ingestion.repository import persist_normalized_jobs
from app.services.llm_gateway.registry import MODEL_REGISTRY

router = APIRouter(prefix="/pipeline", tags=["pipeline"])

_AUDIT_APPLICATIONS: dict[str, ApplicationAuditRecord] = {}


@router.post("/run-demo", response_model=PipelineRunResult)
def run_demo_pipeline(payload: PipelineRunRequest) -> PipelineRunResult:
    started_at = datetime.now(timezone.utc)
    run_id = f"demo-{int(started_at.timestamp())}"
    logs: list[str] = [f"pipeline:start demo model={payload.model_name}"]
    status = PipelineStatus.PROCESSING

    profile = Profile(
        user_id=1,
        full_name="Jane Doe",
        email="jane@example.com",
        skills=["python", "fastapi", "sql", "docker"],
        years_experience=5,
        target_locations=["Remote", "New York, NY"],
    )
    raw_jobs = [
        JobIn(
            source="demo",
            raw_title="Backend Engineer",
            raw_company="Acme Corp",
            raw_description="Build APIs in Python FastAPI and SQL for cloud workloads.",
            raw_location="Remote",
            raw_apply_link="https://example.com/jobs/backend-engineer",
        ),
        JobIn(
            source="demo",
            raw_title="Frontend Engineer",
            raw_company="Globex",
            raw_description="React Typescript role with UX collaboration.",
            raw_location="San Francisco, CA",
            raw_apply_link="https://example.com/jobs/frontend-engineer",
        ),
    ]

    dataset = run_dataset_pipeline(dataset_name="jobs_demo")
    dataset_version = dataset.dataset_version
    logs.append(f"pipeline:dataset version={dataset_version} rows={len(dataset.normalized_jobs)}")

    job_output = run_job_agent(JobAgentInput(raw_jobs=raw_jobs))
    logs.extend(job_output.logs)

    Base.metadata.create_all(bind=engine)
    with SessionLocal() as session:
        user = session.query(User).filter(User.email == profile.email).one_or_none()
        if user is None:
            user = User(email=profile.email, full_name=profile.full_name)
            session.add(user)
            session.commit()
            session.refresh(user)

        persist_normalized_jobs(
            session,
            user_id=user.id,
            dataset_version=dataset_version,
            jobs=job_output.normalized_jobs,
        )
    logs.append(f"pipeline:persisted jobs={len(job_output.normalized_jobs)} dataset_version={dataset_version}")

    match_output = run_match_agent(MatchAgentInput(profile=profile, jobs=job_output.normalized_jobs))
    logs.extend(match_output.logs)

    resume_generated = False
    llm_provider = MODEL_REGISTRY.get(payload.model_name).provider if payload.model_name in MODEL_REGISTRY else None
    if match_output.matches and job_output.normalized_jobs:
        top_match = match_output.matches[0]
        target_job = next(job for job in job_output.normalized_jobs if job.title == top_match.job_title)
        resume_output = run_resume_agent(
            ResumeAgentInput(
                base_resume="Experienced software engineer with API and platform background.",
                profile=profile,
                target_job=target_job,
                model_name=payload.model_name,
            )
        )
        logs.extend(resume_output.logs)
        resume_generated = bool(resume_output.tailored_resume.tailored_resume)

        credential_profile_id = "cred-demo-1"
        credential_status = CredentialProfileStatus.ACTIVE
        apply_output = run_apply_agent(
            ApplyAgentInput(
                job_title=target_job.title,
                company=target_job.company,
                credential_profile_id=credential_profile_id,
                credential_status=credential_status,
                credential_username="demo.user@example.com",
                credential_secret="enc:demo-ciphertext",
            )
        )
        logs.extend(apply_output.logs)
        logs.extend(action.detail for action in apply_output.result.logs)
        status = apply_output.result.status

        submitted_at = datetime.now(timezone.utc)
        application_id = f"app-{run_id}"
        job_id = f"job-{abs(hash((target_job.title, target_job.company))) % 10_000_000}"

        _AUDIT_APPLICATIONS[application_id] = ApplicationAuditRecord(
            application_id=application_id,
            run_id=run_id,
            job_id=job_id,
            target_company=target_job.company,
            target_title=target_job.title,
            credential_profile_id=credential_profile_id,
            credential_provider="greenhouse",
            credential_account_alias="primary",
            resume_id=f"resume-{run_id}",
            resume_version=1,
            cover_letter_id=f"cover-{run_id}",
            cover_letter_version=1,
            generation_provider=llm_provider,
            generation_model=payload.model_name,
            submitted_at=submitted_at,
            external_application_id=f"ext-{run_id}",
            external_application_url="https://example.com/applications/ext-demo",
            status=status,
            events=[
                ApplicationAuditEvent(
                    event=ApplicationEventName.ATTEMPTED,
                    created_at=started_at,
                    detail="Application automation flow started.",
                ),
                ApplicationAuditEvent(
                    event=ApplicationEventName.SUBMITTED,
                    created_at=submitted_at,
                    detail="Application submitted successfully.",
                ),
            ],
        )
    else:
        status = PipelineStatus.FAILED
        logs.append("pipeline:failed no_matches")

    return PipelineRunResult(
        run_id=run_id,
        status=status,
        started_at=started_at,
        finished_at=datetime.now(timezone.utc),
        jobs_ingested=len(job_output.normalized_jobs),
        matches_found=len(match_output.matches),
        resume_generated=resume_generated,
        model_name=payload.model_name,
        llm_provider=llm_provider,
        dataset_version=dataset_version,
        logs=logs,
    )


@router.get("/audit/applications", response_model=ApplicationAuditList)
def list_application_audit_history() -> ApplicationAuditList:
    """List immutable audit records for all application runs."""

    return ApplicationAuditList(applications=list(_AUDIT_APPLICATIONS.values()))


@router.get("/audit/applications/{application_id}", response_model=ApplicationAuditRecord)
def get_application_audit_history(application_id: str) -> ApplicationAuditRecord:
    """Get one immutable audit record by application id."""

    record = _AUDIT_APPLICATIONS.get(application_id)
    if record is None:
        raise HTTPException(status_code=404, detail="Application audit record not found")
    return record
