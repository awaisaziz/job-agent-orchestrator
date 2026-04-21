"""Pipeline orchestration endpoints."""

from datetime import datetime, timezone

from fastapi import APIRouter

from app.agents.job_agent import JobAgentInput, run_job_agent
from app.agents.match_agent import MatchAgentInput, run_match_agent
from app.agents.resume_agent import ResumeAgentInput, run_resume_agent
from app.schemas.job import JobIn
from app.schemas.pipeline import PipelineRunResult, PipelineStatus
from app.schemas.profile import Profile

router = APIRouter(prefix="/pipeline", tags=["pipeline"])


@router.post("/run-demo", response_model=PipelineRunResult)
def run_demo_pipeline() -> PipelineRunResult:
    started_at = datetime.now(timezone.utc)
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
        finished_at=datetime.now(timezone.utc),
        jobs_ingested=len(job_output.normalized_jobs),
        matches_found=len(match_output.matches),
        resume_generated=resume_generated,
        logs=logs,
    )
