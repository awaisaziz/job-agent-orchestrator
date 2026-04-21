# Architecture Overview

## Repository layout
- `backend/`: FastAPI orchestration API, domain agents, service adapters, DB models.
- `frontend/`: Next.js dashboard for executing runs and viewing telemetry.
- `docs/`: system documentation (`ARCHITECTURE.md`, `BACKEND.md`, `FRONTEND.md`).
- `data/`: reproducible datasets and normalized artifacts.

## Backend architecture

### API layer
- `app/main.py`: creates FastAPI app and mounts `/api/v1` routes.
- `app/api/v1/routes_pipeline.py`: pipeline orchestration endpoints.

### Agent layer
- `job_agent`: normalizes incoming jobs.
- `match_agent`: computes profile-to-job relevance.
- `resume_agent`: tailors resume text via LLM gateway with deterministic fallback.
- `apply_agent`: submits applications via generic or LinkedIn platform mode.

### Service layer
- `services/ingestion/*`: dataset loading, normalization, persistence pipeline.
- `services/resume_agent/service.py`: prompt construction and LLM call orchestration.
- `services/application_agent/service.py`: retry-safe application submission logic.
- `services/linkedin/service.py`: LinkedIn job pull + Easy Apply simulation.

## Frontend architecture
- `PipelineDashboard` is a client component that triggers demo pipeline runs.
- `lib/api.ts` centralizes HTTP contracts and error mapping.
- `JobTimeline` and `LogsPanel` visualize per-job progress and backend logs.

## End-to-end pipeline sequence
1. **Ingestion**
   - Demo route uses seeded/mock jobs and dataset normalization.
   - LinkedIn route pulls jobs from LinkedIn API (if configured) or deterministic fallback.
2. **Matching**
   - Candidate profile skills are scored against normalized job skills/entities.
3. **Resume tailoring**
   - Resume is tailored for top match via selected LLM model.
   - If provider credentials are missing, fallback text is generated deterministically.
4. **Apply**
   - Generic mode logs retry-safe stub actions.
   - LinkedIn mode validates applicant profile fields and simulates Easy Apply submission.
5. **Observability**
   - Route returns status, counts, provider metadata, and ordered logs.
   - Audit endpoints provide immutable application history for downstream review.

## LinkedIn connectivity contract
- Configure `LINKEDIN_ACCESS_TOKEN` and `LINKEDIN_JOBS_API_URL` to enable connected pull mode.
- Without configuration, system uses deterministic LinkedIn-like records so local runs stay stable.
- Easy Apply simulation enforces required applicant fields and never crashes the run on missing data.
