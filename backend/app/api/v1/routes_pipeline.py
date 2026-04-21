"""Pipeline endpoints (mock implementation)."""

from fastapi import APIRouter

router = APIRouter(prefix="/pipeline", tags=["pipeline"])


@router.get("/demo")
def demo_pipeline() -> dict[str, object]:
    return {
        "candidate": "Jane Doe",
        "jobs_ingested": 3,
        "matches": 2,
        "applications_submitted": 1,
        "status": "mock-run-complete",
    }
