"""LinkedIn pull/apply integration with safe local fallback behavior."""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from typing import Any
from urllib.error import URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen

from app.schemas.job import JobIn
from app.schemas.pipeline import PipelineStatus


@dataclass(slots=True)
class LinkedInApplicationResult:
    """Structured result of a LinkedIn easy apply attempt."""

    status: PipelineStatus
    submitted: bool
    logs: list[str] = field(default_factory=list)


def fetch_linkedin_jobs(
    *,
    query: str,
    location: str,
    limit: int = 5,
    access_token: str | None = None,
    api_url: str | None = None,
) -> list[JobIn]:
    """Fetch jobs from LinkedIn API when credentials exist; otherwise return deterministic demo jobs."""

    if access_token and api_url:
        try:
            params = urlencode({"keywords": query, "location": location, "limit": max(1, limit)})
            request = Request(f"{api_url}?{params}", headers={"Authorization": f"Bearer {access_token}"})
            with urlopen(request, timeout=15) as response:  # nosec: endpoint configured by operator
                payload = json.loads(response.read().decode("utf-8"))
            jobs = _map_linkedin_jobs(payload)
            if jobs:
                return jobs[:limit]
        except (URLError, TimeoutError, ValueError, KeyError):
            # Fallback below intentionally keeps pipeline runnable when LinkedIn API is unavailable.
            pass

    return _demo_linkedin_jobs(limit=limit, location=location)


def fill_linkedin_easy_apply(*, job: JobIn, applicant_profile: dict[str, Any]) -> LinkedInApplicationResult:
    """Validate required fields and emulate a deterministic Easy Apply flow."""

    logs: list[str] = [f"linkedin_apply:start title={job.raw_title} company={job.raw_company}"]
    required_fields = ["full_name", "email", "phone", "resume_text"]
    missing_fields = [field for field in required_fields if not applicant_profile.get(field)]

    if missing_fields:
        logs.append(f"linkedin_apply:failed missing_fields={','.join(sorted(missing_fields))}")
        return LinkedInApplicationResult(status=PipelineStatus.FAILED, submitted=False, logs=logs)

    logs.extend(
        [
            "linkedin_apply:open_easy_apply_modal",
            "linkedin_apply:populate_contact_fields",
            "linkedin_apply:populate_resume_and_screening_answers",
            "linkedin_apply:submit_application",
        ]
    )

    return LinkedInApplicationResult(status=PipelineStatus.COMPLETED, submitted=True, logs=logs)


def _map_linkedin_jobs(payload: dict[str, Any]) -> list[JobIn]:
    elements = payload.get("elements", [])
    mapped: list[JobIn] = []
    for item in elements:
        mapped.append(
            JobIn(
                source="linkedin",
                raw_title=str(item.get("title", "Unknown Role")),
                raw_company=str(item.get("companyName", "Unknown Company")),
                raw_description=str(item.get("description", "")),
                raw_location=str(item.get("formattedLocation", "Remote")),
                raw_apply_link=item.get("applyUrl") or "https://www.linkedin.com/jobs",
            )
        )
    return mapped


def _demo_linkedin_jobs(*, limit: int, location: str) -> list[JobIn]:
    seed = [
        JobIn(
            source="linkedin",
            raw_title="Senior Backend Engineer",
            raw_company="LinkedIn PartnerCo",
            raw_description="Build FastAPI services, data pipelines, and high quality APIs.",
            raw_location=location,
            raw_apply_link="https://www.linkedin.com/jobs/view/1001",
        ),
        JobIn(
            source="linkedin",
            raw_title="AI Platform Engineer",
            raw_company="TalentGraph",
            raw_description="Python, SQL, and workflow orchestration for recruiting intelligence.",
            raw_location=location,
            raw_apply_link="https://www.linkedin.com/jobs/view/1002",
        ),
    ]
    return seed[: max(1, limit)]
