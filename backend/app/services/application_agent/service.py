"""Application agent service with retry-safe stub and action logging."""

from dataclasses import dataclass, field

from app.schemas.pipeline import PipelineStatus


@dataclass(slots=True)
class ApplicationAction:
    action: str
    detail: str


@dataclass(slots=True)
class ApplicationAttemptResult:
    status: PipelineStatus
    attempts: int
    logs: list[ApplicationAction] = field(default_factory=list)


def submit_application(job_title: str, company: str, max_retries: int = 2) -> ApplicationAttemptResult:
    """Retry-safe submission interface with stubbed Playwright call for demo."""

    logs: list[ApplicationAction] = []
    for attempt in range(1, max_retries + 1):
        logs.append(ApplicationAction(action="navigate", detail=f"Attempt {attempt}: open {company} careers page"))
        logs.append(ApplicationAction(action="playwright_stub", detail="Playwright submit flow skipped in demo mode"))
        if attempt == 1:
            logs.append(ApplicationAction(action="result", detail=f"Simulated success for {job_title}"))
            return ApplicationAttemptResult(status=PipelineStatus.COMPLETED, attempts=attempt, logs=logs)
    logs.append(ApplicationAction(action="result", detail="All retries exhausted"))
    return ApplicationAttemptResult(status=PipelineStatus.FAILED, attempts=max_retries, logs=logs)
