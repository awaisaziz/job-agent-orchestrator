"""Business logic for the Chrome extension API.

Given the user's stored profile + base resume and a job posting the extension
scraped from an open tab, this:
  - tailors the resume to the job (reusing the resume agent),
  - answers the ACTUAL form fields the extension found (identity fields mapped
    directly from the profile; open-ended questions answered by the LLM, grounded
    in the resume, with a deterministic fallback when no LLM key is set),
  - records applications the extension submitted so they show up in the app.
"""

from __future__ import annotations

import json
import logging
import re

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.models.external_application import ExternalApplication
from app.db.models.resume import Resume
from app.db.models.user import User
from app.schemas.extension import (
    ExtensionApplicationItem,
    ExtensionProfileResponse,
    FormFieldSpec,
    PrepareApplicationRequest,
    PrepareApplicationResponse,
    RecordApplicationRequest,
    RecordApplicationResponse,
)
from app.schemas.job import JobNormalized
from app.schemas.profile import Profile
from app.services.application_agent.quality import detect_skill_gaps
from app.services.job_search.skill_extractor import extract_skills_from_text
from app.services.profile_intake.service import parse_resume_text
from app.services.resume_agent.service import build_tailored_resume

logger = logging.getLogger(__name__)


class ProfileNotFoundError(Exception):
    """Raised when no user exists for the given email."""


# ── Profile loading ───────────────────────────────────────────────────────────

def _load_user_and_resume(session: Session, email: str) -> tuple[User, Resume]:
    user = session.scalar(select(User).where(User.email == email))
    if user is None:
        raise ProfileNotFoundError(
            f"No profile found for {email}. Open the web app and complete profile intake first."
        )
    resume = session.execute(
        select(Resume)
        .where(Resume.user_id == user.id, Resume.kind == "base")
        .order_by(Resume.version.desc(), Resume.id.desc())
    ).scalars().first()
    if resume is None:
        raise ProfileNotFoundError(
            f"No base resume found for {email}. Upload your resume in the web app first."
        )
    return user, resume


def _build_profile(user: User, resume: Resume) -> tuple[Profile, str]:
    parsed = parse_resume_text(resume_text=resume.content, email=user.email, full_name=user.full_name)
    profile = Profile(
        user_id=user.id,
        full_name=user.full_name,
        email=user.email,
        phone=user.phone,
        skills=parsed.skills,
        years_experience=3,
        target_locations=[],
    )
    return profile, parsed.summary


def get_profile_response(session: Session, email: str) -> ExtensionProfileResponse:
    user, resume = _load_user_and_resume(session, email)
    profile, summary = _build_profile(user, resume)
    return ExtensionProfileResponse(
        user_id=user.id,
        full_name=profile.full_name,
        email=profile.email,
        phone=profile.phone,
        skills=profile.skills,
        years_experience=profile.years_experience,
        base_resume_text=resume.content,
        summary=summary,
    )


# ── Application preparation ───────────────────────────────────────────────────

def prepare_application(session: Session, req: PrepareApplicationRequest) -> PrepareApplicationResponse:
    from app.core.config import settings

    user, resume = _load_user_and_resume(session, req.email)
    profile, _summary = _build_profile(user, resume)

    jd_skills = extract_skills_from_text(req.job_description) if req.job_description else []
    job = JobNormalized(
        title=req.job_title or "the role",
        company=req.company or "the company",
        description=req.job_description,
        skills=jd_skills,
        entities=[],
        location=None,
        apply_link=req.apply_url or None,
    )

    model_name = settings.llm_default_model
    tailored = build_tailored_resume(
        base_resume=resume.content, profile=profile, job=job, model_name=model_name
    )
    llm_used = any("LLM provider used" in note for note in tailored.notes)

    # Only spend an LLM round-trip on a cover letter when the page actually has a
    # cover-letter field to fill — that's the only thing that consumes it.
    needs_cover = any(
        _has((field.label or field.name).lower(), "cover letter", "cover note")
        for field in req.fields
    )
    cover_letter, cover_from_llm = (
        _cover_letter(profile, job, resume.content, model_name) if needs_cover else ("", False)
    )
    answers = _answer_fields(
        profile=profile, job=job, resume_text=resume.content,
        fields=req.fields, cover_letter=cover_letter, model_name=model_name,
    )

    gaps = detect_skill_gaps(profile.skills, jd_skills)
    return PrepareApplicationResponse(
        tailored_resume=tailored.tailored_resume,
        cover_letter=cover_letter,
        answers=answers,
        matched_skills=gaps.matched_skills,
        missing_skills=gaps.missing_skills,
        model_used=model_name,
        llm_used=llm_used or cover_from_llm,
    )


# Identity fields we can fill directly from the profile (no LLM needed). Ordered:
# more specific patterns first so "first name" isn't caught by "name".
def _direct_answer(label: str, profile: Profile) -> str | None:
    text = label.lower()
    parts = profile.full_name.split()
    first = parts[0] if parts else profile.full_name
    last = parts[-1] if len(parts) > 1 else ""

    if _has(text, "first name", "given name", "forename"):
        return first
    if _has(text, "last name", "surname", "family name"):
        return last
    if _has(text, "full name", "your name", "candidate name") or text.strip() in {"name"}:
        return profile.full_name
    if _has(text, "e-mail", "email"):
        return profile.email
    if _has(text, "phone", "mobile", "telephone", "contact number"):
        return profile.phone or ""
    if _has(text, "linkedin"):
        return ""  # unknown; leave for user
    if _has(text, "current company", "employer"):
        return ""
    if _has(text, "years of experience", "years experience"):
        return str(profile.years_experience)
    return None


def _answer_fields(
    *,
    profile: Profile,
    job: JobNormalized,
    resume_text: str,
    fields: list[FormFieldSpec],
    cover_letter: str,
    model_name: str,
) -> dict[str, str]:
    answers: dict[str, str] = {}
    open_questions: list[FormFieldSpec] = []

    for field in fields:
        direct = _direct_answer(field.label or field.name, profile)
        if direct is not None:
            if direct:
                answers[field.name] = direct
            continue
        label = (field.label or field.name).lower()
        if _has(label, "cover letter", "cover note"):
            answers[field.name] = cover_letter
            continue
        # Long-form / screening questions → answer with the LLM (batched).
        if field.type in {"textarea"} or _looks_open_ended(label):
            open_questions.append(field)

    if open_questions:
        answers.update(
            _generate_open_answers(
                profile=profile, job=job, resume_text=resume_text,
                questions=open_questions, model_name=model_name,
            )
        )
    return answers


def _looks_open_ended(label: str) -> bool:
    return _has(
        label, "why", "describe", "tell us", "cover", "motivat", "interest",
        "about you", "summary", "message", "question", "experience with", "how would",
    )


def _generate_open_answers(
    *,
    profile: Profile,
    job: JobNormalized,
    resume_text: str,
    questions: list[FormFieldSpec],
    model_name: str,
) -> dict[str, str]:
    fallback = {q.name: _fallback_answer(q, profile, job) for q in questions}

    from app.services.llm_gateway import LLMGenerateRequest, generate_text

    listing = "\n".join(f'- id="{q.name}": {q.label or q.name}' for q in questions)
    prompt = (
        "You are helping a job candidate fill out an application form. Answer each "
        "question truthfully AS THE CANDIDATE, in first person, grounded ONLY in the "
        "resume below. Never invent employers, titles, dates, degrees, or metrics. "
        "Keep each answer concise (2-4 sentences). If the resume lacks the information, "
        "give a brief honest answer without fabricating.\n\n"
        f"CANDIDATE: {profile.full_name}\n"
        f"TARGET ROLE: {job.title} at {job.company}\n"
        f"JOB DESCRIPTION:\n{job.description[:1500]}\n\n"
        f"RESUME:\n{resume_text[:3000]}\n\n"
        f"QUESTIONS:\n{listing}\n\n"
        'Return ONLY a JSON object mapping each id to its answer string, e.g. '
        '{"q1": "answer", "q2": "answer"}.'
    )
    try:
        response = generate_text(
            LLMGenerateRequest(
                model_name=model_name,
                system_prompt="You answer job application questions truthfully as the candidate. Output JSON only.",
                prompt=prompt,
                temperature=0.3,
                max_tokens=900,
            )
        )
        parsed = _extract_json_object(response.output_text)
        if parsed:
            return {q.name: str(parsed.get(q.name) or fallback[q.name]).strip() for q in questions}
    except Exception as exc:  # noqa: BLE001 — deterministic fallback on any LLM failure
        logger.info("Open-answer generation fell back to deterministic: %s", exc)
    return fallback


def _fallback_answer(field: FormFieldSpec, profile: Profile, job: JobNormalized) -> str:
    label = (field.label or field.name).lower()
    top_skills = ", ".join(profile.skills[:4]) or "my background"
    if _has(label, "cover"):
        return _deterministic_cover_letter(profile, job)
    if _has(label, "why", "interest", "motivat"):
        return (
            f"I'm excited about the {job.title} role at {job.company} because it aligns "
            f"closely with my experience in {top_skills}. I'd welcome the chance to "
            "contribute and grow with the team."
        )
    return (
        f"Drawing on my experience with {top_skills}, I believe I can contribute "
        f"effectively to the {job.title} role at {job.company}."
    )


def _cover_letter(profile: Profile, job: JobNormalized, resume_text: str, model_name: str) -> tuple[str, bool]:
    from app.services.llm_gateway import LLMGenerateRequest, generate_text

    prompt = (
        "Write a concise, truthful cover letter (max 180 words) for this candidate and "
        "role, in first person, grounded ONLY in the resume. Do not invent facts.\n\n"
        f"CANDIDATE: {profile.full_name}\n"
        f"ROLE: {job.title} at {job.company}\n"
        f"JOB DESCRIPTION:\n{job.description[:1200]}\n\n"
        f"RESUME:\n{resume_text[:2500]}"
    )
    try:
        response = generate_text(
            LLMGenerateRequest(
                model_name=model_name,
                system_prompt="You write concise, truthful cover letters grounded in the candidate's resume.",
                prompt=prompt,
                temperature=0.3,
                max_tokens=400,
            )
        )
        text = (response.output_text or "").strip()
        if text:
            return text, True
    except Exception as exc:  # noqa: BLE001
        logger.info("Cover-letter generation fell back to deterministic: %s", exc)
    return _deterministic_cover_letter(profile, job), False


def _deterministic_cover_letter(profile: Profile, job: JobNormalized) -> str:
    top_skills = ", ".join(profile.skills[:5]) or "the required areas"
    return (
        f"Dear {job.company} Hiring Team,\n\n"
        f"I'm writing to apply for the {job.title} role. My background includes hands-on "
        f"experience with {top_skills}, which maps closely to what this position calls for. "
        "I focus on shipping reliable, well-tested work and collaborating closely with my team.\n\n"
        f"I'd welcome the opportunity to bring that experience to {job.company}. Thank you for "
        "your consideration.\n\n"
        f"Sincerely,\n{profile.full_name}"
    )


# ── Recording ─────────────────────────────────────────────────────────────────

def record_application(session: Session, req: RecordApplicationRequest) -> RecordApplicationResponse:
    user, _resume = _load_user_and_resume(session, req.email)
    record = ExternalApplication(
        user_id=user.id,
        job_title=req.job_title,
        company=req.company,
        apply_url=req.apply_url,
        status=req.status,
        source="extension",
        notes=req.notes,
    )
    session.add(record)
    session.commit()
    session.refresh(record)

    notified = False
    if req.notify and req.status == "applied":
        notified = _notify(user=user, record=record)

    return RecordApplicationResponse(application_id=record.id, recorded=True, notified=notified)


def _notify(*, user: User, record: ExternalApplication) -> bool:
    try:
        from app.services.notifications.service import (
            ApplicationSummaryItem,
            send_notification_if_configured,
        )

        result = send_notification_if_configured(
            recipient_email=user.email,
            full_name=user.full_name,
            applications=[
                ApplicationSummaryItem(
                    job_title=record.job_title, company=record.company,
                    apply_url=record.apply_url, status="applied",
                )
            ],
            dashboard_url="http://localhost:3000",
        )
        return bool(result and result.sent)
    except Exception:  # noqa: BLE001
        logger.exception("Extension application notification failed")
        return False


def list_applications(session: Session, email: str) -> list[ExtensionApplicationItem]:
    user = session.scalar(select(User).where(User.email == email))
    if user is None:
        return []
    rows = session.execute(
        select(ExternalApplication)
        .where(ExternalApplication.user_id == user.id)
        .order_by(ExternalApplication.created_at.desc(), ExternalApplication.id.desc())
    ).scalars().all()
    return [
        ExtensionApplicationItem(
            id=row.id, job_title=row.job_title, company=row.company, apply_url=row.apply_url,
            status=row.status, source=row.source, notes=row.notes, created_at=row.created_at,
        )
        for row in rows
    ]


# ── Helpers ───────────────────────────────────────────────────────────────────

def _has(text: str, *needles: str) -> bool:
    return any(needle in text for needle in needles)


def _extract_json_object(text: str) -> dict | None:
    if not text:
        return None
    cleaned = text.strip()
    cleaned = re.sub(r"^```(?:json)?", "", cleaned).strip()
    cleaned = re.sub(r"```$", "", cleaned).strip()
    try:
        result = json.loads(cleaned)
        return result if isinstance(result, dict) else None
    except json.JSONDecodeError:
        pass
    match = re.search(r"\{.*\}", cleaned, re.DOTALL)
    if match:
        try:
            result = json.loads(match.group(0))
            return result if isinstance(result, dict) else None
        except json.JSONDecodeError:
            return None
    return None
