"""Backend entrypoint for the Job Agent Orchestrator API."""

from fastapi import FastAPI

from app.api.v1.routes_pipeline import router as pipeline_router

app = FastAPI(title="Job Agent Orchestrator", version="0.1.0")
app.include_router(pipeline_router, prefix="/api/v1")


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}
