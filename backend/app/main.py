"""Backend entrypoint for the Job Agent Orchestrator API."""

from fastapi import FastAPI, Response
from fastapi.middleware.cors import CORSMiddleware

from app.api.v1.routes_config import router as config_router
from app.api.v1.routes_pipeline import router as pipeline_router
from app.api.v1.routes_workflow import router as workflow_router

app = FastAPI(title="Job Agent Orchestrator", version="0.1.0")
app.add_middleware(
    CORSMiddleware,
    allow_origin_regex=r"https?://(localhost|127\.0\.0\.1)(:\d+)?",
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)
app.include_router(pipeline_router, prefix="/api/v1")
app.include_router(workflow_router, prefix="/api/v1")
app.include_router(config_router, prefix="/api/v1")


@app.get("/")
def root() -> dict[str, object]:
    return {
        "name": app.title,
        "version": app.version,
        "status": "ok",
        "health": "/health",
        "docs": "/docs",
        "pipeline_demo": "/api/v1/pipeline/run-demo",
        "job_search": "/api/v1/search/jobs",
    }


@app.get("/favicon.ico", include_in_schema=False)
def favicon() -> Response:
    return Response(status_code=204)


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}
