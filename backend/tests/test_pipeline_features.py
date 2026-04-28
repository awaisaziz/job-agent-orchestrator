import unittest

from app.api.v1 import routes_pipeline
from app.schemas.pipeline import PipelineRunRequest
from app.services.application_agent.quality import calculate_ats_score, detect_skill_gaps
from app.services.application_agent.service import submit_application
from app.db.models.credential_profile import CredentialProfileStatus


class PipelineFeatureTests(unittest.TestCase):
    def setUp(self) -> None:
        routes_pipeline._APPLICATION_DEDUP.clear()
        routes_pipeline._APPLICATION_TRACKING.clear()
        routes_pipeline._AUDIT_APPLICATIONS.clear()
        routes_pipeline._RESUME_HISTORY.clear()

    def test_ats_score_checker(self) -> None:
        score = calculate_ats_score(["python", "sql"], ["python", "docker"], 0.5)
        self.assertGreater(score, 0)
        self.assertLessEqual(score, 100)

    def test_skill_gap_detection(self) -> None:
        gap = detect_skill_gaps(["python", "sql"], ["python", "fastapi"])
        self.assertEqual(gap.matched_skills, ["python"])
        self.assertEqual(gap.missing_skills, ["fastapi"])

    def test_human_approval_required(self) -> None:
        result = routes_pipeline.run_demo_pipeline(PipelineRunRequest(model_name="gpt-4.1-mini", approved_by_human=False))
        self.assertTrue(result.waiting_for_human_approval)
        self.assertEqual(result.status.value, "PENDING")

    def test_duplicate_application_prevention(self) -> None:
        first = routes_pipeline.run_demo_pipeline(PipelineRunRequest(model_name="gpt-4.1-mini", approved_by_human=True))
        second = routes_pipeline.run_demo_pipeline(PipelineRunRequest(model_name="gpt-4.1-mini", approved_by_human=True))
        self.assertEqual(first.status.value, "COMPLETED")
        self.assertTrue(second.duplicate_prevented)

    def test_failure_recovery_retries(self) -> None:
        result = submit_application(
            job_title="Backend Engineer",
            company="Acme",
            credential_profile_id="cred-1",
            credential_status=CredentialProfileStatus.ACTIVE,
            fail_until_attempt=1,
            max_retries=3,
        )
        self.assertEqual(result.status.value, "COMPLETED")
        self.assertEqual(result.attempts, 2)

    def test_tracking_dashboard_and_resume_history(self) -> None:
        run_result = routes_pipeline.run_demo_pipeline(PipelineRunRequest(model_name="gpt-4.1-mini", approved_by_human=True))
        tracking = routes_pipeline.list_application_tracking()
        history = routes_pipeline.get_resume_history(run_result.run_id)
        self.assertGreaterEqual(len(tracking.applications), 1)
        self.assertGreaterEqual(len(history.resumes), 2)

    def test_email_integration_placeholder(self) -> None:
        status = routes_pipeline.get_email_integration_status()
        self.assertIn(status.mode, {"connected", "placeholder"})


if __name__ == "__main__":
    unittest.main()
