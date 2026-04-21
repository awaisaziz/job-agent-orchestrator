# Architecture Overview

This repository is split into:

- `backend/`: FastAPI service with API routes, agents, tasks, prompt templates, and placeholder domain models/schemas.
- `frontend/`: Next.js UI with a lightweight dashboard to visualize a mock pipeline run.
- `docker-compose.yml`: Local multi-service orchestration for backend and frontend.

## Pipeline (mock)

1. Ingest jobs from configured sources.
2. Match jobs against candidate profile and resume.
3. Tailor resume and generate cover letter artifacts.
4. Submit applications.
5. Collect feedback and logs for iteration.
