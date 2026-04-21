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

### Demo flow (mock data)
1. Open `http://localhost:3000` to view the pipeline dashboard.
2. The UI shows a mock run: ingestion → matching → resume tailoring → application → feedback.
3. Call `GET http://localhost:8000/api/v1/pipeline/demo` to retrieve the same mock pipeline summary from backend.
