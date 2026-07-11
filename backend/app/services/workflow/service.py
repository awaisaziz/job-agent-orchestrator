"""Persisted search-to-application workflow service."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
import hashlib
from pathlib import Path

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.agents.job_search_agent import JobSearchAgentInput, run_job_search_agent
from app.agents.match_agent import MatchAgentInput, run_match_agent
from app.agents.resume_agent import ResumeAgentInput, run_resume_agent
from app.db.models.application import Application
from app.db.models.application_event import ApplicationEvent, ApplicationEventType
from app.db.models.application_selection import ApplicationSelection
from app.db.models.email_sync_state import EmailSyncState
from app.db.models.job_search import JobSearch
from app.db.models.resume import Resume
from app.db.models.search_result import SearchResult
from app.db.models.user import User
from app.schemas.job import JobNormalized
from app.schemas.profile import Profile
from app.schemas.workflow import (
    ApplicationEventRecord,
    ApplicationQueueItem,
    EmailIntegrationResponse,
    MatchResultItem,
    ProfileSummary,
    ResumeArtifact,
    SearchResultItem,
    SearchWorkspaceResponse,
    TailorResumeResult,
    WorkflowStatus,
)
from app.services.application_agent.quality import calculate_ats_score, detect_skill_gaps
from app.services.application_agent.service import submit_application
from app.services.document_renderer.service import PdfRenderer
from app.services.profile_intake.service import parse_resume_text


@dataclass(slots=True)
class IntakeResult:
    profile: ProfileSummary


class WorkflowService:
    """Coordinates persisted search, tailoring, approval, and application state."""

    def __init__(self) -> None:
        self.renderer = PdfRenderer(Path(__file__).resolve().parents[3] / "storage" / "resumes")

    def intake_profile(
        self,
        *,
        session: Session,
        email: str,
        resume_filename: str,
        resume_text: str,
        location: str | None,
        full_name: str | None,
        phone: str | None = None,
    ) -> IntakeResult:
        user = session.scalar(select(User).where(User.email == email))
        parsed = parse_resume_text(resume_text=resume_text, email=email, full_name=full_name)
        if user is None:
            user = User(email=email, full_name=parsed.full_name, phone=phone)
            session.add(user)
            session.flush()
        else:
            user.full_name = parsed.full_name
            if phone:
                user.phone = phone

        resume = Resume(
            user_id=user.id,
            version=self._next_resume_version(session=session, user_id=user.id, kind="base"),
            kind="base",
            source_filename=resume_filename,
            content=resume_text,
        )
        session.add(resume)
        session.commit()
        session.refresh(resume)
        return IntakeResult(
            profile=ProfileSummary(
                user_id=user.id,
                full_name=user.full_name,
                email=user.email,
                phone=user.phone,
                skills=parsed.skills,
                target_locations=[location] if location else [],
                base_resume=self._resume_artifact(resume),
                parsed_summary=parsed.summary,
            )
        )

    def search_jobs(self, *, session: Session, user_id: int, position: str, location: str | None) -> JobSearch:
        search = JobSearch(user_id=user_id, position=position, location=location, status=WorkflowStatus.SAVED.value)
        session.add(search)
        session.flush()

        agent_output = run_job_search_agent(JobSearchAgentInput(position=position, location=location))

        # In demo mode (no JSearch key) candidates carry mock apply URLs that point to
        # real Google Jobs searches — treat them as verified and skip the network check.
        from app.core.config import settings
        live_mode = bool(settings.jsearch_api_key)

        url_results: dict[str, object] = {}
        if live_mode:
            from app.services.job_search.url_verifier import verify_urls
            urls = [c.apply_url for c in agent_output.results if c.apply_url]
            url_results = verify_urls(urls, timeout=5.0)

        for candidate in agent_output.results:
            if live_mode:
                url_result = url_results.get(candidate.apply_url)
                url_verified = url_result.status in {"verified", "redirect"} if url_result else False
                url_status = url_result.status if url_result else None
                final_url = url_result.final_url if url_result else None

                # Skip dead URLs — don't store them
                if url_result and url_result.status == "dead":
                    continue
            else:
                url_verified = True
                url_status = "verified"
                final_url = candidate.apply_url

            session.add(
                SearchResult(
                    search_id=search.id,
                    user_id=user_id,
                    source=candidate.source,
                    source_job_key=self._job_fingerprint(candidate.title, candidate.company, candidate.apply_url),
                    title=candidate.title,
                    company=candidate.company,
                    snippet=candidate.snippet,
                    description=candidate.description,
                    location=candidate.location,
                    apply_url=candidate.apply_url,
                    source_url=candidate.source_url,
                    skills=candidate.skills,
                    metadata_json={"provider": candidate.source, **candidate.metadata},
                    status=WorkflowStatus.NORMALIZED.value,
                    url_verified=url_verified,
                    url_status=url_status,
                    final_apply_url=final_url,
                )
            )
        search.status = WorkflowStatus.NORMALIZED.value
        session.commit()
        session.refresh(search)
        return search

    def match_jobs(self, *, session: Session, search_id: int) -> list[MatchResultItem]:
        search = self._get_search(session=session, search_id=search_id)
        profile = self._load_profile(session=session, user_id=search.user_id)
        results = session.execute(select(SearchResult).where(SearchResult.search_id == search_id)).scalars().all()
        normalized_jobs = [self._to_job_normalized(result) for result in results]
        matches = run_match_agent(MatchAgentInput(profile=profile, jobs=normalized_jobs)).matches

        match_items: list[MatchResultItem] = []
        for result, match in zip(results, matches, strict=True):
            result.fit_score = match.similarity
            result.status = WorkflowStatus.MATCHED.value
            gaps = detect_skill_gaps(profile.skills, result.skills or [])
            match_items.append(
                MatchResultItem(
                    result_id=result.id,
                    fit_score=match.similarity,
                    matched_skills=gaps.matched_skills,
                    missing_skills=gaps.missing_skills,
                )
            )
        search.status = WorkflowStatus.MATCHED.value
        session.commit()
        return match_items

    def prepare_applications(self, *, session: Session, search_id: int, result_ids: list[int]) -> list[Application]:
        search = self._get_search(session=session, search_id=search_id)
        results = self._get_search_results(session=session, search_id=search_id, result_ids=result_ids)
        applications: list[Application] = []
        for result in results:
            selection = session.scalar(
                select(ApplicationSelection).where(
                    ApplicationSelection.search_id == search_id,
                    ApplicationSelection.search_result_id == result.id,
                )
            )
            if selection is None:
                selection = ApplicationSelection(search_id=search_id, search_result_id=result.id, user_id=search.user_id)
                session.add(selection)

            application = session.scalar(
                select(Application).where(
                    Application.user_id == search.user_id,
                    Application.search_result_id == result.id,
                )
            )
            if application is None:
                application = Application(
                    user_id=search.user_id,
                    search_result_id=result.id,
                    status=WorkflowStatus.PENDING_APPROVAL.value,
                    waiting_for_human_approval=True,
                    duplicate_blocked=self._is_duplicate(session=session, user_id=search.user_id, result=result),
                    match_score=result.fit_score,
                )
                session.add(application)
                session.flush()
                self._append_event(
                    session=session,
                    application_id=application.id,
                    event_type=ApplicationEventType.ATTEMPTED,
                    detail="Application prepared and placed into approval queue.",
                )
            result.status = WorkflowStatus.MATCHED.value
            applications.append(application)

        search.status = WorkflowStatus.MATCHED.value
        session.commit()
        return applications

    def tailor_applications(self, *, session: Session, application_ids: list[int], model_name: str) -> list[TailorResumeResult]:
        applications = self._get_applications(session=session, application_ids=application_ids)
        tailored: list[TailorResumeResult] = []
        for application in applications:
            result = self._require_search_result(session=session, application=application)
            profile = self._load_profile(session=session, user_id=application.user_id)
            base_resume = self._latest_base_resume(session=session, user_id=application.user_id)
            job = self._to_job_normalized(result)
            output = run_resume_agent(
                ResumeAgentInput(
                    base_resume=base_resume.content,
                    profile=profile,
                    target_job=job,
                    model_name=model_name,
                )
            )
            ats_score = calculate_ats_score(profile.skills, result.skills or [], result.fit_score or 0.0)
            gaps = detect_skill_gaps(profile.skills, result.skills or [])
            version = self._next_resume_version(session=session, user_id=application.user_id, kind="tailored")
            artifact = self.renderer.render_resume(
                file_stem=f"application-{application.id}-resume-v{version}",
                title=f"{result.title} - {result.company}",
                body=output.tailored_resume.tailored_resume,
            )
            resume = Resume(
                user_id=application.user_id,
                application_id=application.id,
                search_result_id=result.id,
                version=version,
                kind="tailored",
                source_filename=base_resume.source_filename,
                artifact_path=artifact.artifact_path,
                content=output.tailored_resume.tailored_resume,
            )
            session.add(resume)
            session.flush()

            application.resume_id = resume.id
            application.resume_version = resume.version
            application.ats_score = ats_score
            application.status = WorkflowStatus.TAILORED.value
            application.waiting_for_human_approval = True
            result.ats_score = ats_score
            result.status = WorkflowStatus.TAILORED.value
            self._append_event(
                session=session,
                application_id=application.id,
                event_type=ApplicationEventType.ATTEMPTED,
                detail=f"Tailored resume generated with model {model_name}.",
            )
            tailored.append(
                TailorResumeResult(
                    application_id=application.id,
                    resume_version_id=resume.id,
                    ats_score=ats_score,
                    matched_skills=gaps.matched_skills,
                    missing_skills=gaps.missing_skills,
                    artifact_path=artifact.artifact_path,
                    status=WorkflowStatus.TAILORED,
                )
            )

        session.commit()
        return tailored

    def approve_applications(self, *, session: Session, application_ids: list[int]) -> list[Application]:
        applications = self._get_applications(session=session, application_ids=application_ids)
        for application in applications:
            application.status = WorkflowStatus.APPROVED.value
            application.waiting_for_human_approval = False
            self._append_event(
                session=session,
                application_id=application.id,
                event_type=ApplicationEventType.ATTEMPTED,
                detail="Application approved by user and ready for submission.",
            )
        session.commit()
        return applications

    def submit_applications(self, *, session: Session, application_ids: list[int]) -> list[dict[str, object]]:
        applications = self._get_applications(session=session, application_ids=application_ids)
        responses: list[dict[str, object]] = []
        notification_items: list[tuple[str, str, str, str, float | None, str | None]] = []
        first_user_id: int | None = None

        for application in applications:
            result = self._require_search_result(session=session, application=application)
            if first_user_id is None:
                first_user_id = application.user_id

            if application.duplicate_blocked:
                application.status = WorkflowStatus.FAILED.value
                responses.append(
                    {
                        "application_id": application.id,
                        "status": WorkflowStatus.FAILED,
                        "attempted_actions": ["guard:duplicate_blocked"],
                        "failure_reason": "Duplicate application attempt blocked.",
                    }
                )
                notification_items.append((result.title, result.company, result.apply_url or "", "skipped", application.ats_score, "Duplicate blocked"))
                continue
            if application.status != WorkflowStatus.APPROVED.value:
                responses.append(
                    {
                        "application_id": application.id,
                        "status": WorkflowStatus.FAILED,
                        "attempted_actions": ["guard:approval_required"],
                        "failure_reason": "Application must be approved before submission.",
                    }
                )
                continue

            tailored_resume = self._latest_tailored_resume(session=session, application_id=application.id)
            profile = self._load_profile(session=session, user_id=application.user_id)
            resume_path = tailored_resume.artifact_path if tailored_resume else None

            # Simulate mode (default): record the application locally with a full audit
            # trail and notification, without driving any external site. Set
            # AUTO_APPLY_MODE=live to use the real Playwright/email auto-apply pipeline.
            from app.core.config import settings

            if settings.auto_apply_mode.lower() != "live":
                application.status = WorkflowStatus.APPLIED.value
                application.retries_used = 0
                application.submitted_at = datetime.now(timezone.utc)
                application.external_application_url = result.apply_url
                result.status = WorkflowStatus.APPLIED.value
                detail = (
                    "Simulated application recorded locally (AUTO_APPLY_MODE=simulate). "
                    "No external submission was made — set AUTO_APPLY_MODE=live to auto-submit."
                )
                self._append_event(
                    session=session,
                    application_id=application.id,
                    event_type=ApplicationEventType.SUBMITTED,
                    detail=detail,
                )
                responses.append(
                    {
                        "application_id": application.id,
                        "status": WorkflowStatus.APPLIED,
                        "attempted_actions": [detail],
                        "failure_reason": None,
                    }
                )
                notification_items.append(
                    (result.title, result.company, result.apply_url or "", "applied", application.ats_score, None)
                )
                continue

            submission = submit_application(
                job_title=result.title,
                company=result.company,
                credential_profile_id=f"local-{application.user_id}",
                applicant_profile={
                    "full_name": profile.full_name,
                    "email": profile.email,
                    "phone": profile.phone or "",
                    "resume_text": tailored_resume.content if tailored_resume else self._latest_base_resume(session=session, user_id=application.user_id).content,
                },
                apply_url=result.apply_url,
                resume_path=resume_path,
            )
            success = submission.status.value in {"COMPLETED", "completed"}
            application.status = WorkflowStatus.APPLIED.value if success else WorkflowStatus.FAILED.value
            application.retries_used = max(submission.attempts - 1, 0)
            application.submitted_at = datetime.now(timezone.utc) if success else None
            application.external_application_url = result.apply_url
            result.status = application.status
            self._append_event(
                session=session,
                application_id=application.id,
                event_type=ApplicationEventType.SUBMITTED if success else ApplicationEventType.FAILED,
                detail=submission.logs[-1].detail if submission.logs else submission.error,
            )
            responses.append(
                {
                    "application_id": application.id,
                    "status": WorkflowStatus.APPLIED if success else WorkflowStatus.FAILED,
                    "attempted_actions": [entry.detail for entry in submission.logs],
                    "failure_reason": submission.error,
                }
            )
            status_str = "applied" if success else ("skipped" if submission.method == "skipped" else "failed")
            notification_items.append((result.title, result.company, result.apply_url or "", status_str, application.ats_score, submission.error))

        session.commit()

        # Send notification email with summary
        if notification_items and first_user_id is not None:
            self._send_submission_notification(
                session=session, user_id=first_user_id,
                items=notification_items,
            )

        return responses

    def _send_submission_notification(
        self, *, session: Session, user_id: int,
        items: list[tuple[str, str, str, str, float | None, str | None]],
    ) -> None:
        """Send email notification with submission summary."""
        try:
            from app.services.notifications.service import ApplicationSummaryItem, send_notification_if_configured

            profile = self._load_profile(session=session, user_id=user_id)
            summary_items = [
                ApplicationSummaryItem(
                    job_title=title, company=company, apply_url=url,
                    status=status, ats_score=score, skip_reason=reason,
                )
                for title, company, url, status, score, reason in items
            ]
            send_notification_if_configured(
                recipient_email=profile.email,
                full_name=profile.full_name,
                applications=summary_items,
                dashboard_url="http://localhost:3000",
            )
        except Exception:
            import logging
            logging.getLogger(__name__).exception("Failed to send notification email")

    def list_applications(self, *, session: Session, user_id: int | None = None) -> list[ApplicationQueueItem]:
        query = select(Application).where(Application.search_result_id.is_not(None)).order_by(Application.updated_at.desc(), Application.id.desc())
        if user_id is not None:
            query = query.where(Application.user_id == user_id)
        applications = session.execute(query).scalars().all()
        return [self._application_item(session=session, application=application) for application in applications]

    def get_workspace(self, *, session: Session, search_id: int) -> SearchWorkspaceResponse:
        search = self._get_search(session=session, search_id=search_id)
        user = self._require_user(session=session, user_id=search.user_id)
        base_resume = self._latest_base_resume(session=session, user_id=user.id)
        parsed = parse_resume_text(resume_text=base_resume.content, email=user.email, full_name=user.full_name)
        results = session.execute(
            select(SearchResult)
            .where(SearchResult.search_id == search_id)
            .order_by(SearchResult.fit_score.is_(None), SearchResult.fit_score.desc(), SearchResult.id)
        ).scalars().all()
        selections = {
            selection.search_result_id
            for selection in session.execute(
                select(ApplicationSelection).where(ApplicationSelection.search_id == search_id, ApplicationSelection.selected.is_(True))
            ).scalars()
        }
        applications = session.execute(
            select(Application)
            .where(Application.user_id == search.user_id, Application.search_result_id.is_not(None))
            .order_by(Application.updated_at.desc(), Application.id.desc())
        ).scalars().all()
        return SearchWorkspaceResponse(
            search_id=search.id,
            status=WorkflowStatus(search.status),
            position=search.position,
            location=search.location,
            profile=ProfileSummary(
                user_id=user.id,
                full_name=user.full_name,
                email=user.email,
                phone=user.phone,
                skills=parsed.skills,
                target_locations=[search.location] if search.location else [],
                base_resume=self._resume_artifact(base_resume),
                parsed_summary=parsed.summary,
            ),
            results=[self._search_result_item(result=result, selected=result.id in selections) for result in results],
            applications=[self._application_item(session=session, application=application) for application in applications],
        )

    def email_status(self, *, session: Session, user_id: int | None = None, configured: bool) -> EmailIntegrationResponse:
        last_synced_at = None
        if user_id is not None:
            state = session.scalar(select(EmailSyncState).where(EmailSyncState.user_id == user_id, EmailSyncState.provider == "gmail"))
            if state is not None:
                last_synced_at = state.last_synced_at
        detail = "Gmail read-only inbox tracking is connected." if configured else "Connect Gmail credentials to sync interview and rejection emails."
        return EmailIntegrationResponse(
            provider="gmail",
            configured=configured,
            mode="connected" if configured else "placeholder",
            detail=detail,
            last_synced_at=last_synced_at,
        )

    def list_application_events(self, *, session: Session, application_id: int) -> list[ApplicationEventRecord]:
        records = session.execute(
            select(ApplicationEvent).where(ApplicationEvent.application_id == application_id).order_by(ApplicationEvent.created_at.asc())
        ).scalars().all()
        return [ApplicationEventRecord(event=record.event_type.value, detail=record.detail, created_at=record.created_at) for record in records]

    def _load_profile(self, *, session: Session, user_id: int) -> Profile:
        user = self._require_user(session=session, user_id=user_id)
        resume = self._latest_base_resume(session=session, user_id=user.id)
        parsed = parse_resume_text(resume_text=resume.content, email=user.email, full_name=user.full_name)
        return Profile(
            user_id=user.id,
            full_name=user.full_name,
            email=user.email,
            phone=user.phone,
            skills=parsed.skills,
            years_experience=3,
            target_locations=[],
        )

    def _application_item(self, *, session: Session, application: Application) -> ApplicationQueueItem:
        result = self._require_search_result(session=session, application=application)
        resume = self._latest_tailored_resume(session=session, application_id=application.id)
        return ApplicationQueueItem(
            application_id=application.id,
            search_result_id=result.id,
            company=result.company,
            title=result.title,
            source=result.source,
            fit_score=application.match_score,
            ats_score=application.ats_score,
            status=WorkflowStatus(application.status),
            waiting_for_human_approval=application.waiting_for_human_approval,
            duplicate_blocked=application.duplicate_blocked,
            retries_used=application.retries_used,
            apply_url=result.apply_url,
            tailored_resume=self._resume_artifact(resume) if resume else None,
            updated_at=application.updated_at or application.created_at,
        )

    def _search_result_item(self, *, result: SearchResult, selected: bool) -> SearchResultItem:
        return SearchResultItem(
            result_id=result.id,
            source=result.source,
            title=result.title,
            company=result.company,
            snippet=result.snippet,
            description=result.description,
            location=result.location,
            apply_url=result.apply_url,
            source_url=result.source_url,
            skills=result.skills or [],
            fit_score=result.fit_score,
            ats_score=result.ats_score,
            status=WorkflowStatus(result.status),
            selected=selected,
            url_verified=result.url_verified,
            url_status=result.url_status,
            final_apply_url=result.final_apply_url,
        )

    def _resume_artifact(self, resume: Resume) -> ResumeArtifact:
        return ResumeArtifact(
            resume_id=resume.id,
            version=resume.version,
            kind=resume.kind,
            artifact_path=resume.artifact_path,
            source_filename=resume.source_filename,
            created_at=resume.created_at,
        )

    def _append_event(self, *, session: Session, application_id: int, event_type: ApplicationEventType, detail: str | None) -> None:
        session.add(ApplicationEvent(application_id=application_id, event_type=event_type, detail=detail))

    def _get_search(self, *, session: Session, search_id: int) -> JobSearch:
        search = session.get(JobSearch, search_id)
        if search is None:
            raise ValueError(f"Search {search_id} was not found")
        return search

    def _get_search_results(self, *, session: Session, search_id: int, result_ids: list[int]) -> list[SearchResult]:
        results = session.execute(
            select(SearchResult).where(SearchResult.search_id == search_id, SearchResult.id.in_(result_ids))
        ).scalars().all()
        if len(results) != len(set(result_ids)):
            raise ValueError("One or more selected jobs were not found in this search")
        return results

    def _get_applications(self, *, session: Session, application_ids: list[int]) -> list[Application]:
        applications = session.execute(select(Application).where(Application.id.in_(application_ids))).scalars().all()
        if len(applications) != len(set(application_ids)):
            raise ValueError("One or more applications were not found")
        return applications

    def _latest_base_resume(self, *, session: Session, user_id: int) -> Resume:
        resume = session.execute(
            select(Resume).where(Resume.user_id == user_id, Resume.kind == "base").order_by(Resume.version.desc(), Resume.id.desc())
        ).scalars().first()
        if resume is None:
            raise ValueError("Base resume was not found for the user")
        return resume

    def _latest_tailored_resume(self, *, session: Session, application_id: int) -> Resume | None:
        return session.execute(
            select(Resume).where(Resume.application_id == application_id, Resume.kind == "tailored").order_by(Resume.version.desc(), Resume.id.desc())
        ).scalars().first()

    def _require_search_result(self, *, session: Session, application: Application) -> SearchResult:
        if application.search_result_id is None:
            raise ValueError(f"Application {application.id} is missing its search result reference")
        result = session.get(SearchResult, application.search_result_id)
        if result is None:
            raise ValueError(f"Search result {application.search_result_id} was not found")
        return result

    def _require_user(self, *, session: Session, user_id: int) -> User:
        user = session.get(User, user_id)
        if user is None:
            raise ValueError(f"User {user_id} was not found")
        return user

    def _to_job_normalized(self, result: SearchResult) -> JobNormalized:
        return JobNormalized(
            title=result.title,
            company=result.company,
            description=result.description,
            skills=result.skills or [],
            entities=[],
            location=result.location,
            apply_link=result.apply_url,
        )

    def _is_duplicate(self, *, session: Session, user_id: int, result: SearchResult) -> bool:
        fingerprint = self._job_fingerprint(result.title, result.company, result.apply_url or "")
        applications = session.execute(select(Application).where(Application.user_id == user_id)).scalars().all()
        for application in applications:
            existing = self._require_search_result(session=session, application=application) if application.search_result_id else None
            if existing and self._job_fingerprint(existing.title, existing.company, existing.apply_url or "") == fingerprint:
                return application.status == WorkflowStatus.APPLIED.value
        return False

    @staticmethod
    def _next_resume_version(*, session: Session, user_id: int, kind: str) -> int:
        latest = session.execute(
            select(Resume).where(Resume.user_id == user_id, Resume.kind == kind).order_by(Resume.version.desc(), Resume.id.desc())
        ).scalars().first()
        return 1 if latest is None else latest.version + 1

    @staticmethod
    def _job_fingerprint(title: str, company: str, apply_url: str) -> str:
        payload = f"{company.lower()}::{title.lower()}::{apply_url.lower()}"
        return hashlib.sha256(payload.encode("utf-8")).hexdigest()
