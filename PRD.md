# PRD.md — Product Requirements Document
## Job Agent Orchestrator

**Version:** 0.1 (discovery & foundation)
**Status:** Active development — foundation in place, core workflow functional in mock mode

---

## 1. Problem Statement

Job searching is a multi-step, repetitive, mentally expensive process.
For each application a person must:
- Find relevant postings across multiple platforms
- Filter for fit
- Tailor their resume to each job description
- Write a cover letter
- Track where they applied and what happened

This is 80% mechanical, 20% judgment.
This product automates the 80%.

---

## 2. Target User

**Primary:** A technically-literate job seeker applying for professional roles
(software engineering, data, product, design, etc.)

**Characteristics:**
- Has an existing resume they trust
- Applies to 10–100+ jobs per search cycle
- Wants control and transparency over what gets submitted
- Comfortable with a local-first web app that connects to APIs

**Not targeting:**
- Enterprise HR teams (this is a personal tool)
- Non-technical users who need fully automated submission with no review

---

## 3. User Flow

### 3.1 Landing / Intake

The user arrives at the homepage and fills in:

| Input | Required | Purpose |
|---|---|---|
| Position name | Yes | Drives job search query |
| Preferred location | No | Filters job results geographically |
| Email | Yes | Unique identity key for all DB records |
| Full name | No | Used in resume and cover letter; inferred from resume if absent |
| Base resume (file upload) | Yes | Source of truth for all AI-generated content |

On submit:
1. Profile intake runs — user is created/updated, resume is parsed for skills
2. Job search runs — multi-source search returns normalized job candidates
3. Match scoring runs — each job is scored against the user's detected skills
4. User is redirected to the **Search Workspace**

### 3.2 Search Workspace

The workspace shows all returned jobs with:
- Job title, company, location
- Fit score (0–100, based on skill overlap)
- Skill gap indicators
- Source (LinkedIn, Indeed, company site)
- Status badge

The user can:
- Select jobs to queue for application
- View job description and matched skills
- See ATS score per job

### 3.3 Resume Tailoring

For selected jobs the user triggers tailoring:
- The system calls the LLM gateway with the base resume + job description
- A tailored resume is produced that emphasizes relevant experience
- The tailored content is **never fabricated** — only reorganized and rephrased
- A version history is maintained

The user can:
- Review the tailored resume
- Reject it and retry with a different model
- Accept it and move to approval

### 3.4 Approval Gate

Before any application is submitted, the user must explicitly approve.
This is a hard gate — no submission happens without it.

The approval action sets application status to `approved`.

### 3.5 Application Submission

On submit:
- The system uses platform-specific automation (currently simulated)
- An audit log is written for every action taken
- Duplicate prevention: same user + company + title cannot be submitted twice
- Result status is set: `applied`, `failed`, etc.

### 3.6 Dashboard / Tracking

At any time the user can view:
- All applications with their current pipeline status
- Full audit trail per application
- Resume version history
- Logs and timestamps for every major action
- Email integration status

---

## 4. Pipeline Statuses

| Status | Meaning |
|---|---|
| `saved` | Job queued, no action taken |
| `fetched` | Job data retrieved from source |
| `normalized` | Raw job data cleaned and structured |
| `matched` | Scored against user profile |
| `tailored` | Resume version generated for this job |
| `pending_approval` | Waiting for user review |
| `approved` | User approved, ready to submit |
| `applied` | Successfully submitted |
| `failed` | Submission failed |
| `rejected` | Rejected by the company |
| `interview` | Interview stage |
| `closed` | Position closed |

---

## 5. LLM Provider Configuration

The system is provider-agnostic. Keys are optional except that **at least one
provider must have a key configured** for tailoring to use live LLM calls.

| Provider | Env Key | Models available |
|---|---|---|
| OpenAI | `OPENAI_API_KEY` | `gpt-4.1-mini`, `gpt-4o-mini` |
| Anthropic (Claude) | `ANTHROPIC_API_KEY` | `claude-3-5-sonnet`, `claude-3-7-sonnet` |
| Grok (xAI) | `GROK_API_KEY` | `grok-3-mini`, `grok-3` |

**Default model** is set via `LLM_DEFAULT_MODEL` in `.env`.
The system validates at startup that the default model's provider key is present.

If a provider key is missing, that provider's models are excluded from the enabled set automatically.
If no key is set at all, the resume tailoring falls back to a deterministic (non-LLM) output.

The frontend shows the currently active default model to the user.

---

## 6. Job Sources

### Current (mock/deterministic)
- Simulated LinkedIn results
- Simulated Indeed results
- Simulated company career site results
- All return realistic normalized `SearchCandidate` records
- Deduplication via SHA-256 hash of `title + company + apply_url`

### Planned (real API integration)
- LinkedIn Jobs API (requires OAuth token — env: `LINKEDIN_ACCESS_TOKEN`)
- Indeed Publisher API
- Greenhouse/Lever ATS APIs
- Web scraping fallback for sites without API

---

## 7. Resume Rules (non-negotiable)

These rules apply to all AI-generated resume and cover letter content:

1. **No invented qualifications.** Only rephrase what the user provided.
2. **No fake metrics.** Do not add numbers not present in the base resume.
3. **No fake titles or dates.** Do not add positions not in the base resume.
4. **No fake technologies.** Only surface skills actually in the base resume.
5. **ATS optimization is allowed** only when truthful — highlighting existing
   skills that match the job description.
6. **If something is missing**, surface it as a suggestion to the user, not as
   generated content.

---

## 8. Functional Requirements

### Must have (MVP)

- [x] User intake form (name, email, location, position, resume upload)
- [x] Resume parsing for skills (deterministic keyword matching)
- [x] Job search (multi-source, normalized results)
- [x] Fit scoring (skill overlap)
- [x] ATS score per job
- [x] Resume tailoring via LLM gateway (OpenAI, Anthropic, Grok)
- [x] LLM fallback when no provider key is set
- [x] Human approval gate before submission
- [x] Application audit log
- [x] Duplicate application prevention
- [x] Pipeline status dashboard
- [x] Resume version history

### Should have (near-term)

- [ ] Cover letter generation (same truthfulness rules as resume)
- [ ] Real LinkedIn Jobs API integration
- [ ] Real Indeed API integration
- [ ] Email ingestion for tracking replies (Gmail/Outlook OAuth)
- [ ] Retry logic for failed submissions
- [ ] PDF export of tailored resume

### Nice to have (later)

- [ ] Feedback loop — track interview/rejection outcomes for better matching
- [ ] Multi-user accounts
- [ ] Browser automation for applying to sites without APIs
- [ ] Job alert notifications
- [ ] Resume templates / formatting control

---

## 9. Non-Functional Requirements

| Requirement | Target |
|---|---|
| API response time (non-LLM) | < 500ms |
| LLM call timeout | 30s (configurable) |
| LLM retries | 1 (configurable) |
| Duplicate submission protection | SHA-256 fingerprint dedup |
| Secret storage | Env vars only — never in code or logs |
| Application audit trail | Immutable, timestamped |

---

## 10. What is *not* in scope

- Automatic submission without human approval
- Fabricating any part of the user's background
- Enterprise multi-tenant features in v0
- Real-time job alerts / push notifications in v0
