# AGENTS.md

## Project Overview
This repository contains an AI-powered job application web app that:
- ingests job postings from APIs or web scraping
- normalizes and stores job data
- matches jobs to a user profile
- tailors resumes and cover letters using AI
- optionally automates application submission
- provides a dashboard to monitor each pipeline stage
- stores logs, analytics, and feedback for future improvement

The system should be modular, safe, observable, and easy to extend.

---

## Core Product Goals
When making changes in this repository, prioritize:

1. Correctness
- preserve valid end-to-end logic across ingestion, matching, tailoring, approval, and application
- avoid breaking existing flows

2. Safety and trust
- never fabricate user experience, education, or skills in resumes or cover letters
- preserve truth in AI-generated outputs
- require explicit user approval before any real submission action

3. Reliability
- fail gracefully
- log structured errors
- support retries for recoverable failures
- prevent duplicate applications

4. Transparency
- expose pipeline stage status clearly in the UI
- provide logs and timestamps for major actions
- keep the user informed about what the agent is doing

5. Extensibility
- use modular service boundaries
- avoid hardcoded platform assumptions
- make it easy to add new job sources or agents later

---

## Architecture Expectations

### Backend
Actual backend structure (align all new code to this):
- `backend/app/api/v1/` — FastAPI route files (routes_pipeline.py, routes_workflow.py, routes_config.py)
- `backend/app/services/` — all business logic, organized by domain subdirectory
- `backend/app/agents/` — thin agent wrappers with typed Input/Output dataclasses
- `backend/app/db/models/` — SQLAlchemy ORM models
- `backend/app/schemas/` — Pydantic v2 request/response schemas
- `backend/app/core/config.py` — Settings via pydantic-settings, loaded from `backend/.env`
- `backend/app/tasks/` — reserved for future async/background processing

Actual stack:
- FastAPI 0.116 + Uvicorn
- SQLite (development, `backend/job_agent.db`) / PostgreSQL (production)
- SQLAlchemy 2.x with `SessionLocal` context manager
- Pydantic v2 + pydantic-settings for config and validation
- stdlib `urllib` for all HTTP calls to LLM providers (no httpx/requests dependency)

### Frontend
Actual frontend structure:
- `frontend/components/` — PipelineDashboard, SearchWorkspace, JobTimeline, LogsPanel, StatusBadge
- `frontend/app/` — Next.js App Router pages (page.tsx = landing/intake, search/ = workspace)
- `frontend/lib/api.ts` — sole HTTP contract layer between frontend and backend

Actual stack:
- Next.js (App Router)
- TypeScript
- Vanilla CSS (globals.css with design tokens)
- No Tailwind — do not add it without explicit decision

---

## Agent Design Rules

Implemented agents (all in `backend/app/agents/`):
- `job_agent.py` — normalizes raw job postings via `services/ingestion/service.py`
- `match_agent.py` — scores profile-to-job fit via `services/matching/service.py`
- `resume_agent.py` — calls LLM gateway to tailor resume via `services/resume_agent/service.py`
- `apply_agent.py` — submits applications via `services/application_agent/service.py`
- `feedback_agent.py` — placeholder for outcome feedback loop
- `job_search_agent.py` — wraps `services/job_search/service.py` (multi-source search)

Planned but not yet implemented:
- `CoverLetterAgent`

Each agent must:
- accept a single typed `Input` dataclass
- return a single typed `Output` dataclass with a `logs: list[str]` field
- delegate all real logic to a service — agents are orchestration wrappers only
- never produce side effects not reflected in their output
- be independently testable with no DB or network required

Do not tightly couple one agent's logic to another agent's internal implementation.

---

## Resume and Cover Letter Rules
When generating or modifying resumes or cover letters:

- do not invent qualifications
- do not add fake metrics, fake job titles, fake dates, or fake technologies
- only rephrase, reorganize, or emphasize information already supported by the user's source resume/profile
- optimize for ATS keywords only when truthful
- preserve a professional and concise tone
- keep original meaning intact

If key information is missing, surface that as a suggestion instead of hallucinating it.

---

## Automation Rules
For job application automation:

- prefer browser automation with robust selectors and retries
- treat external websites as unstable integrations
- isolate site-specific logic from the core pipeline
- never assume a form structure is fixed
- store audit logs for actions like:
  - page opened
  - form field filled
  - resume uploaded
  - submit attempted
  - success/failure result

Do not auto-submit real applications unless the workflow explicitly requires user approval.

---

## Data and Database Rules
Important entities may include:
- users
- user_profiles
- resumes
- resume_versions
- jobs
- job_sources
- job_matches
- applications
- application_events
- logs
- feedback
- platform_credentials

When changing schemas:
- add migrations
- keep backward compatibility where possible
- prevent duplicate applications via a deterministic uniqueness strategy
  - e.g. company + normalized title + apply URL hash

---

## API and Validation Rules
- validate all external input
- validate uploaded files and parsed resume content
- use typed request/response schemas
- return meaningful error messages
- do not leak secrets or raw credentials in logs or API responses

For API-based job sources:
- credentials must come from env vars or secure user-provided secrets
- never hardcode keys
- never commit secrets

---

## LLM Provider Configuration

The system supports three providers. All configuration lives in `backend/.env`.
The gateway is in `backend/app/services/llm_gateway/`.

| Provider | Env Key | Example models |
|---|---|---|
| OpenAI | `OPENAI_API_KEY` | `gpt-4.1-mini`, `gpt-4o-mini` |
| Anthropic (Claude) | `ANTHROPIC_API_KEY` | `claude-3-5-sonnet`, `claude-3-7-sonnet` |
| Grok (xAI) | `GROK_API_KEY` | `grok-3-mini`, `grok-3` |

All three keys are optional. The system selects the default model via `LLM_DEFAULT_MODEL`.
At startup, `config.py` validates that the default model's provider key is present.
Models whose provider key is missing are automatically excluded from the enabled set.

Do not add new providers without:
1. An adapter class in `adapters.py` implementing the `LLMAdapter` Protocol
2. Registry entries in `registry.py`
3. A key field in `Settings` (`core/config.py`)
4. A `_resolve_adapter` branch in `service.py`
5. An entry in `backend/.env.example`

---

## Frontend UX Rules
The UI should make the pipeline visible.

Preferred statuses:
- `saved`
- `fetched`
- `normalized`
- `matched`
- `tailored`
- `pending_approval`
- `approved`
- `applied`
- `failed`
- `rejected`
- `interview`
- `closed`

The dashboard should emphasize:
- job list
- fit score
- resume version status
- current pipeline stage
- logs and timestamps
- approval actions
- retry actions for failed stages

Use simple, clear, professional UI patterns. Avoid unnecessary visual complexity.

---

## Testing Requirements
Every meaningful change should consider:

1. Unit tests
- core matching logic
- ATS scoring logic
- duplicate detection logic
- resume tailoring validation logic
- status transition logic

2. Integration tests
- ingestion to matching flow
- matching to tailoring flow
- approval to application flow
- API route validation

3. Failure-path tests
- missing API key
- empty job description
- LLM failure or timeout
- scraper failure
- duplicate application attempt
- broken application step

Do not merge major logic changes without verifying both success and failure paths.

---

## Logging and Observability
Prefer structured logs with:
- timestamp
- stage
- job id
- user id where appropriate
- severity
- action summary
- failure reason if applicable

Avoid logging:
- raw secrets
- full private resume contents unless necessary
- personally sensitive fields beyond what is operationally needed

---

## Code Quality Rules
- use type hints consistently
- keep functions focused and small
- avoid giant files
- document non-obvious logic
- prefer explicit service boundaries over hidden coupling
- reuse existing project patterns before introducing new abstractions
- do not rewrite unrelated code unnecessarily

When editing existing code:
- inspect current architecture first
- align with existing naming and patterns
- minimize regressions

---

## Pull Request Expectations
When contributing code:
- summarize what changed
- explain why
- list schema or API changes
- mention any assumptions
- mention known limitations
- include test coverage notes

---

## Priorities for Coding Agents
When multiple improvements are possible, prioritize in this order:

1. correctness
2. runtime stability
3. user safety and truthfulness
4. observability
5. maintainability
6. performance
7. polish

---

## Current Implementation State

Already implemented:
- [x] User intake form (name, email, location, position, resume upload)
- [x] Resume skill parsing (deterministic keyword matching)
- [x] Multi-source job search (mock/deterministic adapters for LinkedIn, Indeed, company sites)
- [x] Fit scoring via skill overlap
- [x] ATS scoring and skill gap detection
- [x] LLM gateway with OpenAI, Anthropic, and Grok support
- [x] Deterministic resume tailoring fallback when no LLM key is present
- [x] Human approval gate
- [x] Duplicate application prevention
- [x] Application audit log
- [x] Resume version history
- [x] Pipeline status dashboard (frontend)
- [x] Search workspace with job selection (frontend)

## Good Tasks for Agents
Examples of valuable next contributions:
- wire real LinkedIn Jobs API (replace mock adapter)
- wire real Indeed / Greenhouse APIs
- implement cover letter generation (CoverLetterAgent)
- add PDF resume export
- add email ingestion for tracking replies (Gmail/Outlook OAuth)
- add Alembic migrations
- write unit tests for matching, ATS scoring, and duplicate detection
- write integration tests for the full workflow route sequence
- improve resume parser to handle more file formats

---

## Things to Avoid
- fake resume content
- hidden auto-submit behavior
- hardcoded platform selectors inside core logic
- storing secrets in code or logs
- introducing untyped API contracts
- large refactors without necessity
- brittle one-off scripts in place of reusable modules
- Never Access/Modify the .env file. Human will handle .env changes and configurations.

---

## If Unsure
If requirements are ambiguous:
- preserve user safety
- preserve truth in generated content
- prefer explicit approval steps
- keep changes modular and reversible
- leave a concise note about assumptions
