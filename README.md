# job-agent-orchestrator

## Quick start

### Backend
```bash
cd backend
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
uvicorn app.main:app --reload --port 8000
```

### Frontend
```bash
cd frontend
npm install
npm run dev
```

### Reproducible local seed command
Use this before running the demo pipeline to normalize a known dataset snapshot and persist it to the local DB used by matching and pipeline runs.

```bash
cd backend
python -m app.services.ingestion.seed_local --dataset jobs_demo --dataset-version v1.0.0
```

This command will:
1. Read source data from `data/raw/` based on `data/catalog.yaml`.
2. Normalize title/company/location plus extracted skills/entities.
3. Write deterministic processed artifacts under `data/processed/v1.0.0/`.
4. Persist normalized jobs into local DB tables (`jobs`) with `dataset_version` metadata.

### Demo flow (mock data)
1. Open `http://localhost:3000` to view the pipeline dashboard.
2. The UI shows a mock run: ingestion → matching → resume tailoring → application → feedback.
3. Call `POST http://localhost:8000/api/v1/pipeline/run-demo` to execute the demo pipeline and fetch stage timings, logs, per-job timelines, and `dataset_version` metadata.
4. Call `POST http://localhost:8000/api/v1/pipeline/run-linkedin-demo` to execute the LinkedIn-capable pipeline (LinkedIn job pull + Easy Apply simulation).
5. (Legacy) `GET http://localhost:8000/api/v1/pipeline/demo` still returns a minimal mock summary.


## Environment
Copy `.env.example` to `.env` and set values for database, OpenAI, and optional job APIs.

## Extended docs
- Backend docs: `docs/BACKEND.md`
- Frontend docs: `docs/FRONTEND.md`
- Architecture docs: `docs/ARCHITECTURE.md`
