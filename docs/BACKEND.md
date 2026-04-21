# Backend Documentation

## Overview
The backend is a FastAPI orchestration service that runs the end-to-end job application pipeline:

1. Job ingestion and normalization.
2. Job-to-profile matching.
3. Resume tailoring through the LLM gateway (with deterministic fallback).
4. Application submission (generic demo mode or LinkedIn Easy Apply simulation).
5. Audit/log aggregation for the frontend dashboard.

Core entrypoints:
- API app: `backend/app/main.py`
- Pipeline routes: `backend/app/api/v1/routes_pipeline.py`

## Local setup
```bash
cd backend
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
uvicorn app.main:app --reload --port 8000
```

## Key API endpoints
- `GET /health` - liveness probe.
- `POST /api/v1/pipeline/run-demo` - default demo orchestration with mock job source.
- `POST /api/v1/pipeline/run-linkedin-demo` - LinkedIn-capable orchestration that pulls LinkedIn jobs and submits via LinkedIn Easy Apply simulation.
- `GET /api/v1/pipeline/audit/applications` - list immutable application audit records.
- `GET /api/v1/pipeline/audit/applications/{application_id}` - fetch one application audit record.

## LinkedIn integration behavior
The LinkedIn service (`backend/app/services/linkedin/service.py`) supports two execution modes:

1. **Connected mode** (if `LINKEDIN_ACCESS_TOKEN` and `LINKEDIN_JOBS_API_URL` are provided):
   - Sends a bearer-authenticated request to the configured LinkedIn jobs endpoint.
   - Maps response rows into canonical `JobIn` records.
2. **Fallback mode** (default local/dev):
   - Returns deterministic LinkedIn-like demo jobs so the pipeline still runs safely.

Application step:
- The apply agent can run in `platform="linkedin"` mode.
- Required profile fields for LinkedIn apply simulation: `full_name`, `email`, `phone`, `resume_text`.
- Missing required fields produce a failed status without crashing the pipeline.

## Environment variables
In addition to existing LLM/email settings:

- `LINKEDIN_ACCESS_TOKEN` (optional): OAuth bearer token for LinkedIn jobs API access.
- `LINKEDIN_JOBS_API_URL` (optional): Endpoint used to fetch LinkedIn jobs.

If these are not set, the LinkedIn route still works using deterministic fallback jobs.
