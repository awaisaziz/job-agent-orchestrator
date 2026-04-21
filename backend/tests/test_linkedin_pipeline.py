import os
import unittest


class LinkedInPipelineTests(unittest.TestCase):
    def setUp(self) -> None:
        os.environ.setdefault("OPENAI_API_KEY", "test-key")

    def test_fetch_linkedin_jobs_fallback(self) -> None:
        from app.services.linkedin.service import fetch_linkedin_jobs

        jobs = fetch_linkedin_jobs(query="Software Engineer", location="Remote", limit=2)

        self.assertGreaterEqual(len(jobs), 1)
        self.assertEqual(jobs[0].source, "linkedin")

    def test_linkedin_application_success(self) -> None:
        from app.db.models.credential_profile import CredentialProfileStatus
        from app.services.application_agent.service import submit_application

        result = submit_application(
            job_title="Backend Engineer",
            company="ExampleCo",
            credential_profile_id="cred-1",
            credential_status=CredentialProfileStatus.ACTIVE,
            platform="linkedin",
            applicant_profile={
                "full_name": "Jane Doe",
                "email": "jane@example.com",
                "phone": "+1-555-0100",
                "resume_text": "Experienced backend engineer.",
            },
        )

        self.assertEqual(result.status.value, "COMPLETED")
        self.assertEqual(result.attempts, 1)

    def test_run_linkedin_demo_pipeline_completes(self) -> None:
        from app.api.v1.routes_pipeline import run_linkedin_demo_pipeline
        from app.schemas.pipeline import PipelineRunRequest

        response = run_linkedin_demo_pipeline(PipelineRunRequest(model_name="gpt-4.1-mini"))

        self.assertEqual(response.status.value, "COMPLETED")
        self.assertGreaterEqual(response.jobs_ingested, 1)
        self.assertIn("pipeline:linkedin_pull", " ".join(response.logs))


if __name__ == "__main__":
    unittest.main()
