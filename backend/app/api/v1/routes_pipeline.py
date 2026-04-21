<<<<<<< ours
"""Pipeline endpoints (demo implementation)."""

from __future__ import annotations

from datetime import datetime, timezone
from time import perf_counter
from uuid import uuid4

from fastapi import APIRouter

from app.db.models.log import insert_log, list_logs_for_run
from app.schemas.pipeline import (
    JobTimelineEntry,
    JobTimelineStage,
    PipelineLogEntry,
    PipelineRunDemoResponse,
    StageResult,
)
=======
"""Pipeline orchestration endpoints."""

from datetime import datetime

from fastapi import APIRouter

from app.agents.job_agent import JobAgentInput, run_job_agent
from app.agents.match_agent import MatchAgentInput, run_match_agent
from app.agents.resume_agent import ResumeAgentInput, run_resume_agent
from app.schemas.job import JobIn
from app.schemas.pipeline import PipelineRunResult, PipelineStatus
from app.schemas.profile import Profile
>>>>>>> theirs

router = APIRouter(prefix="/pipeline", tags=["pipeline"])


<<<<<<< ours
@router.get("/demo")
def demo_pipeline() -> dict[str, object]:
    return {
        "candidate": "Jane Doe",
        "jobs_ingested": 3,
        "matches": 2,
        "applications_submitted": 1,
        "status": "mock-run-complete",
    }


@router.post("/run-demo", response_model=PipelineRunDemoResponse)
def run_demo_pipeline() -> PipelineRunDemoResponse:
    run_id = f"demo-{uuid4().hex[:8]}"
    start_ts = datetime.now(timezone.utc)

    sample_jobs = [
        {
            "job_id": "job-001",
            "title": "Backend Python Engineer",
            "company": "Atlas Systems",
            "description": "Build FastAPI services, SQL tuning, and async integrations.",
        },
        {
            "job_id": "job-002",
            "title": "Platform API Developer",
            "company": "Northstar Cloud",
            "description": "Design internal APIs, observability, and CI pipelines.",
        },
        {
            "job_id": "job-003",
            "title": "Data Integrations Engineer",
            "company": "SignalFlow",
            "description": "Develop ETL connectors, REST ingestion, and data quality checks.",
        },
    ]
    sample_profile = {
        "name": "Taylor Brooks",
        "skills": ["Python", "FastAPI", "PostgreSQL", "Docker", "ETL"],
        "years_experience": 6,
        "target_role": "Backend Engineer",
    }
    base_resume_text = (
        "Backend engineer with 6 years of experience building Python APIs, "
        "integration services, and data pipelines in cloud environments."
    )

    stage_results: list[StageResult] = []

    stage_start = perf_counter()
    normalized_jobs = []
    for raw in sample_jobs:
        normalized_jobs.append(
            {
                "job_id": raw["job_id"],
                "title": raw["title"].strip(),
                "company": raw["company"].strip(),
                "description": raw["description"].strip(),
            }
        )
    ingest_ms = int((perf_counter() - stage_start) * 1000)
    insert_log(
        run_id=run_id,
        stage="ingestion_normalization",
        message=f"Normalized {len(normalized_jobs)} job postings for {sample_profile['name']}.",
    )
    stage_results.append(
        StageResult(name="ingestion_normalization", status="completed", duration_ms=ingest_ms)
    )

    stage_start = perf_counter()
    scored_jobs = []
    for job in normalized_jobs:
        overlap = 0
        desc = job["description"].lower()
        for skill in sample_profile["skills"]:
            if skill.lower() in desc:
                overlap += 1
        scored_jobs.append({**job, "score": overlap})
    scored_jobs.sort(key=lambda item: item["score"], reverse=True)
    top_matches = [job for job in scored_jobs[:2] if job["score"] > 0]
    match_ms = int((perf_counter() - stage_start) * 1000)
    insert_log(
        run_id=run_id,
        stage="match_scoring",
        message=f"Scored {len(scored_jobs)} jobs and selected {len(top_matches)} top matches.",
    )
    stage_results.append(StageResult(name="match_scoring", status="completed", duration_ms=match_ms))

    stage_start = perf_counter()
    tailored_resume = None
    if top_matches:
        top_job = top_matches[0]
        tailored_resume = (
            f"{base_resume_text}\n\n"
            f"Tailored for {top_job['title']} at {top_job['company']}: "
            "Emphasized FastAPI API design, SQL optimization, and ETL reliability outcomes."
        )
    resume_ms = int((perf_counter() - stage_start) * 1000)
    insert_log(
        run_id=run_id,
        stage="resume_tailoring",
        message=(
            f"Generated 1 tailored resume for top match {top_matches[0]['job_id']}."
            if tailored_resume
            else "No resume generated because no match passed threshold."
        ),
    )
    stage_results.append(
        StageResult(
            name="resume_tailoring",
            status="completed" if tailored_resume else "skipped",
            duration_ms=resume_ms,
        )
    )

    insert_log(
        run_id=run_id,
        stage="run_summary",
        message=(
            f"Demo pipeline run completed in {int((datetime.now(timezone.utc)-start_ts).total_seconds()*1000)} ms."
        ),
    )

    job_timelines: list[JobTimelineEntry] = []
    for job in scored_jobs:
        is_top = any(match["job_id"] == job["job_id"] for match in top_matches)
        stages = [
            JobTimelineStage(name="Ingestion", status="done", progress_percent=100),
            JobTimelineStage(name="Matching", status="done", progress_percent=100),
            JobTimelineStage(
                name="Resume Tailoring",
                status="done" if is_top and tailored_resume else "pending",
                progress_percent=100 if is_top and tailored_resume else 0,
            ),
            JobTimelineStage(
                name="Application",
                status="running" if is_top else "pending",
                progress_percent=65 if is_top else 0,
            ),
        ]
        job_timelines.append(
            JobTimelineEntry(
                job_id=job["job_id"],
                title=job["title"],
                company=job["company"],
                stages=stages,
            )
        )

    logs = [
        PipelineLogEntry(
            id=entry.id or 0,
            level=entry.level,
            stage=entry.stage,
            message=entry.message,
            created_at=entry.created_at.isoformat(),
        )
        for entry in list_logs_for_run(run_id)
    ]

    return PipelineRunDemoResponse(
        run_id=run_id,
        jobs_fetched=len(sample_jobs),
        jobs_matched=len(top_matches),
        resumes_generated=1 if tailored_resume else 0,
        applications_sent=0,
        stage_results=stage_results,
        job_timelines=job_timelines,
=======
@router.post("/run-demo", response_model=PipelineRunResult)
def run_demo_pipeline() -> PipelineRunResult:
    started_at = datetime.utcnow()
    logs: list[str] = ["pipeline:start demo"]
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

    job_output = run_job_agent(JobAgentInput(raw_jobs=raw_jobs))
    logs.extend(job_output.logs)

    match_output = run_match_agent(MatchAgentInput(profile=profile, jobs=job_output.normalized_jobs))
    logs.extend(match_output.logs)

    resume_generated = False
    if match_output.matches and job_output.normalized_jobs:
        top_match = match_output.matches[0]
        target_job = next(job for job in job_output.normalized_jobs if job.title == top_match.job_title)
        resume_output = run_resume_agent(
            ResumeAgentInput(
                base_resume="Experienced software engineer with API and platform background.",
                profile=profile,
                target_job=target_job,
            )
        )
        logs.extend(resume_output.logs)
        resume_generated = bool(resume_output.tailored_resume.tailored_resume)
        status = PipelineStatus.COMPLETED
    else:
        status = PipelineStatus.FAILED
        logs.append("pipeline:failed no_matches")

    return PipelineRunResult(
        run_id=f"demo-{int(started_at.timestamp())}",
        status=status,
        started_at=started_at,
        finished_at=datetime.utcnow(),
        jobs_ingested=len(job_output.normalized_jobs),
        matches_found=len(match_output.matches),
        resume_generated=resume_generated,
>>>>>>> theirs
        logs=logs,
    )
