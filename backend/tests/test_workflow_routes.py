import os
import unittest

os.environ.setdefault("OPENAI_API_KEY", "test-key")

from app.api.v1 import routes_workflow
from app.db.base import Base
from app.db.session import engine
from app.services.job_search.service import search_jobs
from app.schemas.workflow import (
    ApproveApplicationsRequest,
    EmailSyncRequest,
    JobSearchRequest,
    MatchJobRequest,
    PrepareApplicationsRequest,
    ProfileIntakeRequest,
    SubmitApplicationsRequest,
    TailorResumeRequest,
)


class WorkflowRouteTests(unittest.TestCase):
    def setUp(self) -> None:
        Base.metadata.drop_all(bind=engine)
        Base.metadata.create_all(bind=engine)

    def test_intake_search_and_match_workspace(self) -> None:
        intake = routes_workflow.intake_profile(
            ProfileIntakeRequest(
                email="candidate@example.com",
                full_name="Casey Candidate",
                location="Remote",
                resume_filename="resume.txt",
                resume_text="Casey Candidate\nPython FastAPI SQL Docker React",
            )
        )

        search = routes_workflow.search_jobs(
            JobSearchRequest(
                user_id=intake.profile.user_id,
                position="backend engineer",
                location="Remote",
                email=intake.profile.email,
            )
        )
        matches = routes_workflow.match_jobs(MatchJobRequest(search_id=search.search_id))
        workspace = routes_workflow.get_workspace(search.search_id)

        self.assertEqual(workspace.profile.email, "candidate@example.com")
        self.assertGreaterEqual(len(search.results), 3)
        self.assertEqual(len(matches.results), len(search.results))
        self.assertTrue(all(result.fit_score is not None for result in workspace.results))

    def test_prepare_tailor_approve_and_submit(self) -> None:
        intake = routes_workflow.intake_profile(
            ProfileIntakeRequest(
                email="apply@example.com",
                full_name="Apply User",
                location="New York, NY",
                resume_filename="resume.txt",
                resume_text="Apply User\nPython FastAPI SQL Docker Playwright",
            )
        )
        search = routes_workflow.search_jobs(
            JobSearchRequest(
                user_id=intake.profile.user_id,
                position="ai platform engineer",
                location="Remote",
                email=intake.profile.email,
            )
        )
        routes_workflow.match_jobs(MatchJobRequest(search_id=search.search_id))

        prepared = routes_workflow.prepare_applications(
            PrepareApplicationsRequest(search_id=search.search_id, result_ids=[search.results[0].result_id, search.results[1].result_id])
        )
        tailored = routes_workflow.tailor_resumes(
            TailorResumeRequest(
                application_ids=[item.application_id for item in prepared.applications],
                model_name="gpt-4.1-mini",
            )
        )
        approved = routes_workflow.approve_applications(
            ApproveApplicationsRequest(application_ids=[item.application_id for item in prepared.applications])
        )
        submitted = routes_workflow.submit_applications(
            SubmitApplicationsRequest(application_ids=[item.application_id for item in prepared.applications])
        )

        self.assertEqual(len(tailored.results), 2)
        self.assertTrue(all(result.artifact_path.endswith(".pdf") for result in tailored.results))
        self.assertTrue(all(item.status.value == "approved" for item in approved.applications))
        self.assertTrue(all(result.status.value == "applied" for result in submitted.results))

    def test_email_status_and_sync_placeholder(self) -> None:
        intake = routes_workflow.intake_profile(
            ProfileIntakeRequest(
                email="mail@example.com",
                resume_filename="resume.txt",
                resume_text="Mail User\nPython SQL",
            )
        )

        status = routes_workflow.get_email_status(intake.profile.user_id)
        sync = routes_workflow.sync_email(EmailSyncRequest(user_id=intake.profile.user_id))

        self.assertIn(status.mode, {"connected", "placeholder"})
        self.assertEqual(sync.processed_messages, 0)
        self.assertEqual(sync.inserted_events, 0)

    def test_search_expands_related_titles_and_dedupes_skills(self) -> None:
        results = search_jobs(position="backend engineer", location="Remote")

        self.assertGreaterEqual(len(results), 4)
        # Search expands the requested title into related role variants, so the
        # result set contains more than one distinct base title.
        distinct_titles = {result.title for result in results}
        self.assertGreater(len(distinct_titles), 1)
        self.assertTrue(all(len(result.skills) == len(set(skill.lower() for skill in result.skills)) for result in results))


if __name__ == "__main__":
    unittest.main()
