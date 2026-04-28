"""JSearch (RapidAPI) adapter — returns real job listings from Google for Jobs.

API docs: https://rapidapi.com/letscrape-6bRBa3QguO5/api/jsearch
Free tier: 200 requests/month, 10 results per page.
"""

from __future__ import annotations

import json
import logging
import time
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen

from app.services.job_search.skill_extractor import extract_skills_from_text

logger = logging.getLogger(__name__)

_BASE_URL = "https://jsearch.p.rapidapi.com/search"

# Rate-limit guard — at most 1 request per second
_last_request_time: float = 0.0


def jsearch_search(
    *,
    query: str,
    country: str = "us",
    num_pages: int = 3,
    date_posted: str = "all",
    api_key: str,
    api_host: str = "jsearch.p.rapidapi.com",
) -> list[dict[str, Any]]:
    """Fetch real job listings from JSearch API.

    Returns a list of raw result dicts, each containing:
      job_title, employer_name, job_description, job_apply_link,
      job_google_link, job_city, job_state, job_country,
      job_required_skills, employer_logo, etc.
    """
    global _last_request_time  # noqa: PLW0603

    params = {
        "query": query,
        "page": "1",
        "num_pages": str(num_pages),
        "country": country,
        "date_posted": date_posted,
    }
    url = f"{_BASE_URL}?{urlencode(params)}"
    headers = {
        "x-rapidapi-key": api_key,
        "x-rapidapi-host": api_host,
        "Content-Type": "application/json",
    }

    # Rate-limit: wait if last request was < 1s ago
    elapsed = time.monotonic() - _last_request_time
    if elapsed < 1.0:
        time.sleep(1.0 - elapsed)

    request = Request(url=url, headers=headers, method="GET")
    _last_request_time = time.monotonic()

    try:
        with urlopen(request, timeout=15) as response:
            data = json.loads(response.read().decode("utf-8"))
    except HTTPError as exc:
        body = exc.read().decode("utf-8", errors="replace")
        logger.error("JSearch API error (%d): %s", exc.code, body[:500])
        raise RuntimeError(f"JSearch API request failed ({exc.code}): {body[:200]}") from exc
    except URLError as exc:
        logger.error("JSearch network error: %s", exc.reason)
        raise RuntimeError(f"JSearch network error: {exc.reason}") from exc

    results = data.get("data") or []
    logger.info("JSearch returned %d results for query=%r country=%s", len(results), query, country)
    return results


def parse_jsearch_results(raw_results: list[dict[str, Any]]) -> list["SearchCandidate"]:
    """Convert raw JSearch API results into SearchCandidate dataclass instances."""

    from app.services.job_search.service import SearchCandidate

    candidates: list[SearchCandidate] = []
    for job in raw_results:
        title = job.get("job_title") or "Untitled"
        company = job.get("employer_name") or "Unknown"
        description = job.get("job_description") or ""
        apply_url = job.get("job_apply_link") or ""
        source_url = job.get("job_google_link") or apply_url

        # Build location string
        city = job.get("job_city") or ""
        state = job.get("job_state") or ""
        country = job.get("job_country") or ""
        location_parts = [part for part in [city, state, country] if part]
        location = ", ".join(location_parts) or "Remote"

        # Extract skills: prefer API-provided, fallback to keyword extraction
        api_skills = job.get("job_required_skills") or []
        if not api_skills:
            api_skills = extract_skills_from_text(description)

        snippet = description[:300].strip()
        if len(description) > 300:
            snippet += "..."

        candidates.append(
            SearchCandidate(
                source="jsearch",
                title=title,
                company=company,
                snippet=snippet,
                description=description,
                location=location,
                apply_url=apply_url,
                source_url=source_url,
                skills=api_skills,
                metadata={
                    "provider": "jsearch",
                    "employer_logo": job.get("employer_logo"),
                    "job_id": job.get("job_id"),
                    "job_posted_at": job.get("job_posted_at_datetime_utc"),
                    "job_is_remote": job.get("job_is_remote"),
                    "job_employment_type": job.get("job_employment_type"),
                    "job_min_salary": job.get("job_min_salary"),
                    "job_max_salary": job.get("job_max_salary"),
                    "job_salary_currency": job.get("job_salary_currency"),
                    "job_salary_period": job.get("job_salary_period"),
                },
            )
        )
    return candidates
