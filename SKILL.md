# SKILL.md

## How to work in this repo

This file is for any developer (human or AI) contributing to the job-agent-orchestrator.
Read this before touching code.

---

## Understand the architecture first

- `backend/app/agents/` — thin wrappers. Each agent has a typed Input and Output dataclass.
  They delegate to services; they do not hold logic themselves.
- `backend/app/services/` — all real business logic lives here, organized by domain.
- `backend/app/api/v1/` — FastAPI route files. Keep them thin: validate, call service, return.
- `backend/app/schemas/` — Pydantic v2 models for API contracts.
- `backend/app/db/models/` — SQLAlchemy ORM models.
- `frontend/components/` — reusable React components.
- `frontend/lib/api.ts` — the only place that talks to the backend HTTP API.

---

## LLM Gateway — how it works

The system supports **three providers** selectable per request or via `.env` default:

| Provider | Env var | Example models |
|---|---|---|
| OpenAI | `OPENAI_API_KEY` | `gpt-4.1-mini`, `gpt-4o-mini` |
| Anthropic (Claude) | `ANTHROPIC_API_KEY` | `claude-3-5-sonnet`, `claude-3-7-sonnet` |
| Grok (xAI) | `GROK_API_KEY` | `grok-3-mini`, `grok-3` |

**Routing flow:**

```
request.model_name → MODEL_REGISTRY → provider → adapter → HTTP call
```

- `registry.py` maps model aliases to provider + api_model + temperature.
- `service.py` resolves the adapter and enforces key presence.
- `adapters.py` contains `OpenAIAdapter`, `AnthropicAdapter`, `GrokAdapter`.
- The gateway uses stdlib `urllib` only — no external HTTP client dependency.

**Key `.env` settings:**

```
LLM_DEFAULT_MODEL=grok-3-mini       # used when no model_name is passed
LLM_ENABLED_MODELS=gpt-4.1-mini,gpt-4o-mini,claude-3-5-sonnet,grok-3-mini,grok-3
LLM_TIMEOUT_SECONDS=30
LLM_MAX_RETRIES=1
```

`config.py` validates at startup that the default model's provider has a key set.
If the key is missing, the server will refuse to start.

---

## Workflow — the real user path (not the demo)

The live user workflow (used by the frontend landing page) goes through these route files
and service methods in order:

1. `POST /profile/intake` → `WorkflowService.intake_profile()`
   - Creates or updates `User` row in DB.
   - Parses the uploaded resume text via `profile_intake.service.parse_resume_text()`.
   - Returns a `ParsedProfile` with detected skills and an inferred name.

2. `POST /search/jobs` → `WorkflowService.search_jobs()`
   - Calls `job_search.service.search_jobs(position, location)`.
   - The search service currently returns **deterministic adapter-generated results**
     (simulating LinkedIn, Indeed, company sites). Real API integration is the next step.
   - Persists a `JobSearch` row and one `SearchResult` per candidate job.

3. `POST /match/jobs` → `WorkflowService.match_jobs()`
   - Scores each `SearchResult` against the user's profile skills via `matching/service.py`.
   - Updates `fit_score` on each `SearchResult`.

4. `POST /applications/prepare` → `WorkflowService.prepare_applications()`
   - Creates `Application` rows (status: `saved`) for selected result IDs.

5. `POST /resumes/tailor` → `WorkflowService.tailor_applications()`
   - Calls `resume_agent/service.py` → LLM gateway.
   - Saves a `Resume` row with the tailored content.
   - Moves application status to `tailored`.

6. `POST /applications/approve` → `WorkflowService.approve_applications()`
   - Sets application status to `approved`.
   - This is the explicit human gate before anything is submitted.

7. `POST /applications/submit` → `WorkflowService.submit_applications()`
   - Simulates submission. In production this calls the `apply_agent`.

---

## Profile intake — what fields matter

The intake form collects:

| Field | Required | Notes |
|---|---|---|
| `email` | Yes | Used as unique user key |
| `full_name` | No | Inferred from resume first line if missing |
| `location` | No | Passed to job search for geographic filtering |
| `resume_filename` | Yes | Stored for audit |
| `resume_text` | Yes | The source of truth for skills and content |

The `parse_resume_text()` function does keyword matching against a dictionary of known skills.
It does **not** use an LLM for parsing — it is deterministic and fast.

---

## Job search — current state

`services/job_search/service.py` is currently **deterministic / mock**:
- It generates plausible job listings based on the position query using title normalization
  and variant expansion (e.g. "Backend Engineer" → also searches "Platform Engineer",
  "API Engineer").
- Results are deduplicated by a SHA-256 hash of `title + company + apply_url`.
- Real job APIs (LinkedIn, Indeed, Greenhouse) are not yet wired in.

---

## Resume tailoring — safety rules

In `services/resume_agent/service.py`:
- The base resume text is always included in the prompt.
- The system prompt explicitly forbids hallucinating skills or experience.
- If the LLM call fails, a deterministic fallback resume is returned.
- All tailored content is version-tracked in the `Resume` model.

---

## Database

- SQLite in development (`backend/job_agent.db`).
- PostgreSQL in production (set `DATABASE_URL` in `.env`).
- ORM: SQLAlchemy 2.x with `SessionLocal` context manager pattern.
- No Alembic yet — schema is created via `Base.metadata.create_all()`.
  **Add migrations before any schema change that could lose data.**

---

## Before you finish any change

- [ ] Check all imports resolve (especially the lazy gateway exports in `__init__.py`)
- [ ] Check that API route → service → schema contracts are aligned
- [ ] Check that any new status value is reflected in the frontend `StatusBadge` component
- [ ] Check resume tailoring never adds content not in the base resume
- [ ] Check duplicate prevention logic if touching application submission
- [ ] Check logs include timestamp, stage, and job/user context
- [ ] Check failure paths: missing API key, empty resume, LLM timeout

---

## Adding a new LLM provider

1. Add adapter class to `services/llm_gateway/adapters.py` implementing the `LLMAdapter` Protocol.
2. Add model entries to `MODEL_REGISTRY` in `registry.py`.
3. Add the API key field to `Settings` in `core/config.py`.
4. Add the key validation branch in `service.py → _resolve_adapter()`.
5. Add the key to `backend/.env.example`.
6. Update `LLM_ENABLED_MODELS` default in `.env`.

---

## Adding a new job source

1. Create a new adapter function in `services/job_search/service.py` following the same
   `SearchCandidate` dataclass return contract.
2. Register the adapter in `search_jobs()`.
3. Add any required API keys to `Settings` and `.env.example`.
4. Deduplication happens automatically via `_job_key()`.
