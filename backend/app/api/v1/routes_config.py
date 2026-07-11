"""Frontend-safe configuration routes."""

from fastapi import APIRouter

from app.core.config import settings

router = APIRouter(prefix="/config", tags=["config"])


@router.get("/frontend")
def get_frontend_config() -> dict[str, object]:
    return {
        "default_model": settings.llm_default_model,
        "enabled_models": settings.llm_enabled_models,
        "environment": settings.environment,
        # Mode flags let the UI tell the user which features are live vs. demo.
        "job_search_live": bool(settings.jsearch_api_key),
        "job_search_mode": settings.job_search_mode,  # "jsearch" | "web"
        "llm_live": settings.llm_live_mode,
        "email_live": bool(settings.resend_api_key),
        "auto_apply_mode": settings.auto_apply_mode,
    }
