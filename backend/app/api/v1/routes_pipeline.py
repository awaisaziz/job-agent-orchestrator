"""Pipeline orchestration endpoints."""

from datetime import datetime, timezone
import os

from fastapi import APIRouter, HTTPException

from app.agents.apply_agent import ApplyAgentInput, run_apply_agent
from app.agents.job_agent import JobAgentInput, run_job_agent
from app.agents.match_agent import MatchAgentInput, run_match_agent
from app.agents.resume_agent import ResumeAgentInput, run_resume_agent
from app.db.base import Base
from app.db.models.user import User
from app.db.session import SessionLocal, engine
from app.schemas.job import JobIn, JobNormalized
from app.schemas.pipeline import (
    ApplicationAuditEvent,
    ApplicationAuditList,
    ApplicationAuditRecord,
    ApplicationEventName,
    ApplicationTrackingItem,
    ApplicationTrackingList,
    EmailIntegrationStatus,
    PipelineRunRequest,
    PipelineRunResult,
    PipelineStatus,
    ResumeHistoryList,
    ResumeVersionRecord,
)
from app.schemas.profile import Profile
from app.db.models.credential_profile import CredentialProfileStatus
from app.services.application_agent.quality import calculate_ats_score, detect_skill_gaps
from app.services.ingestion.pipeline import run_dataset_pipeline
from app.services.ingestion.repository import persist_normalized_jobs
from app.services.linkedin.service import fetch_linkedin_jobs
from app.services.llm_gateway.registry import MODEL_REGISTRY

router = APIRouter(prefix="/pipeline", tags=["pipeline"])

_AUDIT_APPLICATIONS: dict[str, ApplicationAuditRecord] = {}
_APPLICATION_TRACKING: dict[str, ApplicationTrackingItem] = {}
_RESUME_HISTORY: dict[str, list[ResumeVersionRecord]] = {}
_APPLICATION_DEDUP: set[str] = set()


def _default_profile() -> Profile:
    return Profile(
        user_id=1,
        full_name="Jane Doe",
        email="jane@example.com",
        skills=["python", "fastapi", "sql", "docker"],
        years_experience=5,
        target_locations=["Remote", "New York, NY"],
    )


def _default_raw_jobs() -> list[JobIn]:
    return [
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


def _persist_jobs(profile: Profile, dataset_version: str, jobs: list[JobNormalized]) -> None:
    Base.metadata.create_all(bind=engine)
    with SessionLocal() as session:
        user = session.query(User).filter(User.email == profile.email).one_or_none()
        if user is None:
            user = User(email=profile.email, full_name=profile.full_name)
            session.add(user)
            session.commit()
            session.refresh(user)

        persist_normalized_jobs(session, user_id=user.id, dataset_version=dataset_version, jobs=jobs)


def _email_integration_configured() -> bool:
    return bool(os.getenv("EMAIL_INGESTION_CLIENT_ID") and os.getenv("EMAIL_INGESTION_CLIENT_SECRET"))


def _make_resume_versions(run_id: str, content: str) -> list[ResumeVersionRecord]:
    now = datetime.now(timezone.utc)
    versions = [
        ResumeVersionRecord(
            resume_id=f"resume-{run_id}",
            version=1,
            created_at=now,
            summary="Base resume imported",
        ),
        ResumeVersionRecord(
            resume_id=f"resume-{run_id}",
            version=2,
            created_at=now,
            summary=(content[:80] + "...") if len(content) > 80 else content,
        ),
    ]
    _RESUME_HISTORY[run_id] = versions
    return versions


def _tracking_item(
    run_id: str,
    job: JobNormalized,
    status: PipelineStatus,
    ats_score: float,
    retries_used: int,
    duplicate_blocked: bool,
    waiting_for_human_approval: bool,
) -> ApplicationTrackingItem:
    item = ApplicationTrackingItem(
        application_id=f"app-{run_id}",
        job_title=job.title,
        company=job.company,
        status=status,
        ats_score=ats_score,
        retries_used=retries_used,
        duplicate_blocked=duplicate_blocked,
        waiting_for_human_approval=waiting_for_human_approval,
        created_at=datetime.now(timezone.utc),
    )
    _APPLICATION_TRACKING[item.application_id] = item
    return item


def _handle_application(
    payload: PipelineRunRequest,
    run_id: str,
    started_at: datetime,
    profile: Profile,
    target_job: JobNormalized,
    model_name: str,
    llm_provider: str | None,
    similarity: float,
    logs: list[str],
) -> tuple[PipelineStatus, bool, bool, int, ApplicationTrackingItem]:
    dedup_key = f"{profile.email.lower()}::{target_job.company.lower()}::{target_job.title.lower()}"
    if dedup_key in _APPLICATION_DEDUP:
        logs.append("pipeline:duplicate_prevented")
        item = _tracking_item(
            run_id=run_id,
            job=target_job,
            status=PipelineStatus.FAILED,
            ats_score=calculate_ats_score(profile.skills, target_job.skills, similarity),
            retries_used=0,
            duplicate_blocked=True,
            waiting_for_human_approval=False,
        )
        return PipelineStatus.FAILED, True, False, 0, item

    if payload.require_human_approval and not payload.approved_by_human:
        logs.append("pipeline:waiting_human_approval")
        item = _tracking_item(
            run_id=run_id,
            job=target_job,
            status=PipelineStatus.PENDING,
            ats_score=calculate_ats_score(profile.skills, target_job.skills, similarity),
            retries_used=0,
            duplicate_blocked=False,
            waiting_for_human_approval=True,
        )
        return PipelineStatus.PENDING, False, True, 0, item

    apply_output = run_apply_agent(
        ApplyAgentInput(
            job_title=target_job.title,
            company=target_job.company,
            credential_profile_id="cred-demo-1",
            credential_status=CredentialProfileStatus.ACTIVE,
            credential_username="demo.user@example.com",
            credential_secret="enc:demo-ciphertext",
            fail_until_attempt=1,
        )
    )
    logs.extend(apply_output.logs)
    logs.extend(action.detail for action in apply_output.result.logs)

    status = apply_output.result.status
    _APPLICATION_DEDUP.add(dedup_key)

    application_id = f"app-{run_id}"
    _AUDIT_APPLICATIONS[application_id] = ApplicationAuditRecord(
        application_id=application_id,
        run_id=run_id,
        job_id=f"job-{abs(hash((target_job.title, target_job.company))) % 10_000_000}",
        target_company=target_job.company,
        target_title=target_job.title,
        credential_profile_id="cred-demo-1",
        credential_provider="greenhouse",
        credential_account_alias="primary",
        resume_id=f"resume-{run_id}",
        resume_version=2,
        cover_letter_id=f"cover-{run_id}",
        cover_letter_version=1,
        generation_provider=llm_provider,
        generation_model=model_name,
        submitted_at=datetime.now(timezone.utc),
        external_application_id=f"ext-{run_id}",
        external_application_url="https://example.com/applications/ext-demo",
        status=status,
        events=[
            ApplicationAuditEvent(event=ApplicationEventName.ATTEMPTED, created_at=started_at, detail="Application automation flow started."),
            ApplicationAuditEvent(event=ApplicationEventName.RETRIED, created_at=datetime.now(timezone.utc), detail="Transient failure recovered."),
            ApplicationAuditEvent(event=ApplicationEventName.SUBMITTED, created_at=datetime.now(timezone.utc), detail="Application submitted successfully."),
        ],
    )

    item = _tracking_item(
        run_id=run_id,
        job=target_job,
        status=status,
        ats_score=calculate_ats_score(profile.skills, target_job.skills, similarity),
        retries_used=max(apply_output.result.attempts - 1, 0),
        duplicate_blocked=False,
        waiting_for_human_approval=False,
    )
    return status, False, False, max(apply_output.result.attempts - 1, 0), item


@router.post("/run-demo", response_model=PipelineRunResult)
def run_demo_pipeline(payload: PipelineRunRequest) -> PipelineRunResult:
    started_at = datetime.now(timezone.utc)
    run_id = f"demo-{int(started_at.timestamp())}"
    logs: list[str] = [f"pipeline:start demo model={payload.model_name}"]
    status = PipelineStatus.PROCESSING

    profile = _default_profile()
    dataset = run_dataset_pipeline(dataset_name="jobs_demo")
    dataset_version = dataset.dataset_version
    logs.append(f"pipeline:dataset version={dataset_version} rows={len(dataset.normalized_jobs)}")

    job_output = run_job_agent(JobAgentInput(raw_jobs=_default_raw_jobs()))
    logs.extend(job_output.logs)

    _persist_jobs(profile, dataset_version, job_output.normalized_jobs)
    logs.append(f"pipeline:persisted jobs={len(job_output.normalized_jobs)} dataset_version={dataset_version}")

    match_output = run_match_agent(MatchAgentInput(profile=profile, jobs=job_output.normalized_jobs))
    logs.extend(match_output.logs)

    resume_generated = False
    llm_provider = MODEL_REGISTRY.get(payload.model_name).provider if payload.model_name in MODEL_REGISTRY else None
    skill_gap = detect_skill_gaps(profile.skills, [])
    ats_score = 0.0
    resume_versions: list[ResumeVersionRecord] = []
    duplicate_prevented = False
    waiting_for_human_approval = False
    retries_used = 0
    tracking_item: ApplicationTrackingItem | None = None

    if match_output.matches and job_output.normalized_jobs:
        top_match = match_output.matches[0]
        target_job = next(job for job in job_output.normalized_jobs if job.title == top_match.job_title)
        skill_gap = detect_skill_gaps(profile.skills, target_job.skills)
        ats_score = calculate_ats_score(profile.skills, target_job.skills, top_match.similarity)

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
        resume_versions = _make_resume_versions(run_id, resume_output.tailored_resume.tailored_resume)

        status, duplicate_prevented, waiting_for_human_approval, retries_used, tracking_item = _handle_application(
            payload=payload,
            run_id=run_id,
            started_at=started_at,
            profile=profile,
            target_job=target_job,
            model_name=payload.model_name,
            llm_provider=llm_provider,
            similarity=top_match.similarity,
            logs=logs,
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
        ats_score=ats_score,
        skill_gap=skill_gap,
        waiting_for_human_approval=waiting_for_human_approval,
        duplicate_prevented=duplicate_prevented,
        retries_used=retries_used,
        tracking_item=tracking_item,
        resume_versions=resume_versions,
        email_integration_configured=_email_integration_configured(),
    )


@router.post("/run-linkedin-demo", response_model=PipelineRunResult)
def run_linkedin_demo_pipeline(payload: PipelineRunRequest) -> PipelineRunResult:
    """Run pipeline with LinkedIn ingestion + Easy Apply simulation."""

    started_at = datetime.now(timezone.utc)
    run_id = f"linkedin-{int(started_at.timestamp())}"
    logs: list[str] = [f"pipeline:start linkedin model={payload.model_name}"]

    profile = _default_profile()
    linkedin_jobs = fetch_linkedin_jobs(
        query="Software Engineer",
        location="Remote",
        limit=3,
        access_token=os.getenv("LINKEDIN_ACCESS_TOKEN"),
        api_url=os.getenv("LINKEDIN_JOBS_API_URL"),
    )
    logs.append(f"pipeline:linkedin_pull jobs={len(linkedin_jobs)}")

    job_output = run_job_agent(JobAgentInput(raw_jobs=linkedin_jobs))
    logs.extend(job_output.logs)

    match_output = run_match_agent(MatchAgentInput(profile=profile, jobs=job_output.normalized_jobs))
    logs.extend(match_output.logs)

    llm_provider = MODEL_REGISTRY.get(payload.model_name).provider if payload.model_name in MODEL_REGISTRY else None
    if not match_output.matches or not job_output.normalized_jobs:
        return PipelineRunResult(
            run_id=run_id,
            status=PipelineStatus.FAILED,
            started_at=started_at,
            finished_at=datetime.now(timezone.utc),
            jobs_ingested=len(job_output.normalized_jobs),
            matches_found=len(match_output.matches),
            resume_generated=False,
            model_name=payload.model_name,
            llm_provider=llm_provider,
            logs=logs,
            skill_gap=detect_skill_gaps(profile.skills, []),
            email_integration_configured=_email_integration_configured(),
        )

    target_job = job_output.normalized_jobs[0]
    top_match = match_output.matches[0]
    resume_output = run_resume_agent(
        ResumeAgentInput(
            base_resume="Experienced software engineer with API and platform background.",
            profile=profile,
            target_job=target_job,
            model_name=payload.model_name,
        )
    )
    logs.extend(resume_output.logs)

    apply_output = run_apply_agent(
        ApplyAgentInput(
            job_title=target_job.title,
            company=target_job.company,
            credential_profile_id="cred-linkedin-1",
            credential_status=CredentialProfileStatus.ACTIVE,
            platform="linkedin",
            applicant_profile={
                "full_name": profile.full_name,
                "email": profile.email,
                "phone": "+1-555-0100",
                "resume_text": resume_output.tailored_resume.tailored_resume,
            },
        )
    )
    logs.extend(apply_output.logs)
    logs.extend(action.detail for action in apply_output.result.logs)

    return PipelineRunResult(
        run_id=run_id,
        status=apply_output.result.status,
        started_at=started_at,
        finished_at=datetime.now(timezone.utc),
        jobs_ingested=len(job_output.normalized_jobs),
        matches_found=len(match_output.matches),
        resume_generated=bool(resume_output.tailored_resume.tailored_resume),
        model_name=payload.model_name,
        llm_provider=llm_provider,
        logs=logs,
        ats_score=calculate_ats_score(profile.skills, target_job.skills, top_match.similarity),
        skill_gap=detect_skill_gaps(profile.skills, target_job.skills),
        retries_used=max(apply_output.result.attempts - 1, 0),
        resume_versions=_make_resume_versions(run_id, resume_output.tailored_resume.tailored_resume),
        email_integration_configured=_email_integration_configured(),
    )


@router.get("/audit/applications", response_model=ApplicationAuditList)
def list_application_audit_history() -> ApplicationAuditList:
    return ApplicationAuditList(applications=list(_AUDIT_APPLICATIONS.values()))


@router.get("/audit/applications/{application_id}", response_model=ApplicationAuditRecord)
def get_application_audit_history(application_id: str) -> ApplicationAuditRecord:
    record = _AUDIT_APPLICATIONS.get(application_id)
    if record is None:
        raise HTTPException(status_code=404, detail="Application audit record not found")
    return record


@router.get("/tracking/applications", response_model=ApplicationTrackingList)
def list_application_tracking() -> ApplicationTrackingList:
    return ApplicationTrackingList(applications=list(_APPLICATION_TRACKING.values()))


@router.get("/resumes/history/{run_id}", response_model=ResumeHistoryList)
def get_resume_history(run_id: str) -> ResumeHistoryList:
    return ResumeHistoryList(resumes=_RESUME_HISTORY.get(run_id, []))


@router.get("/integrations/email/status", response_model=EmailIntegrationStatus)
def get_email_integration_status() -> EmailIntegrationStatus:
    configured = _email_integration_configured()
    mode = "connected" if configured else "placeholder"
    detail = "Email ingestion credentials are configured." if configured else "Placeholder mode; connect provider credentials to enable sync."
    return EmailIntegrationStatus(configured=configured, mode=mode, detail=detail)
