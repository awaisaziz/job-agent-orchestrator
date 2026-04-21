# Frontend Documentation

## Overview
The frontend is a Next.js dashboard that executes a pipeline run and displays:
- Aggregate pipeline metrics.
- Per-job timeline visualization.
- Execution logs.

Core files:
- `frontend/app/page.tsx` - top-level page.
- `frontend/components/PipelineDashboard.tsx` - orchestration UI and model picker.
- `frontend/lib/api.ts` - backend API client.

## Local setup
```bash
cd frontend
npm install
npm run dev
```
Open `http://localhost:3000`.

## Backend connection
Set:
- `NEXT_PUBLIC_API_BASE_URL` (default: `http://localhost:8000`).

The dashboard currently calls `POST /api/v1/pipeline/run-demo` on each model selection change.

## Expected run flow in UI
1. User selects a model.
2. Frontend calls backend pipeline endpoint.
3. UI shows loading state while run executes.
4. UI renders pipeline counts + timeline + logs from response.
5. API errors are mapped to user-readable messages (including missing API-key hints).

## LinkedIn-capable backend notes
The backend now exposes `POST /api/v1/pipeline/run-linkedin-demo`.
If you want a dedicated LinkedIn button in the frontend, add a mode switch in `PipelineDashboard` and call that endpoint from `frontend/lib/api.ts`.
