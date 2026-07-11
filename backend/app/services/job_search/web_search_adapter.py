"""Keyless web job-search adapter.

Discovers real job postings from free, public job-board APIs that need **no API
key**, so the app genuinely "searches the web" for jobs out of the box:

  - Remotive     https://remotive.com/api/remote-jobs   (supports ?search=)
  - Arbeitnow    https://www.arbeitnow.com/api/job-board-api  (Europe-heavy)
  - RemoteOK     https://remoteok.com/api

Each source is queried independently and failures are isolated — if every
source is unreachable the caller falls back to deterministic demo jobs. Results
are filtered by the requested role keywords and softly ranked by region so the
list stays relevant without discarding applicable remote roles.
"""

from __future__ import annotations

import html
import json
import logging
import re
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen

logger = logging.getLogger(__name__)

_USER_AGENT = "Mozilla/5.0 (compatible; JobAgent/1.0; +https://localhost)"
_STOPWORDS = {"the", "and", "for", "with", "job", "role", "position", "senior", "junior", "staff", "lead"}


def web_search_jobs(*, position: str, location: str | None, limit: int = 24) -> list["SearchCandidate"]:
    """Search free public job APIs for real postings. Returns [] if all fail."""
    from app.services.job_search.service import SearchCandidate, detect_region

    tokens = _keywords(position)
    region = detect_region(location)

    collected: list[SearchCandidate] = []
    for fetcher in (_fetch_remotive, _fetch_arbeitnow, _fetch_remoteok):
        try:
            collected.extend(fetcher(position=position, tokens=tokens))
        except Exception:  # noqa: BLE001 — isolate per-source failures
            logger.exception("web job source failed: %s", getattr(fetcher, "__name__", "?"))

    if not collected:
        logger.warning("web_search_jobs: all public job sources returned nothing")
        return []

    # Dedupe by (title, company) and rank by role relevance, then region.
    seen: set[tuple[str, str]] = set()
    unique: list[SearchCandidate] = []
    for candidate in collected:
        key = (candidate.title.lower().strip(), candidate.company.lower().strip())
        if key in seen:
            continue
        seen.add(key)
        unique.append(candidate)

    # Highest title/skill relevance first; within the same relevance, region match
    # then remote roles first.
    unique.sort(key=lambda c: (-_relevance(tokens, c.title, c.skills), _region_rank(c.location, region)))
    result = unique[:limit]
    logger.info(
        "web_search_jobs: %d unique jobs (from %d raw) for position=%r region=%s",
        len(result), len(collected), position, region,
    )
    return result


# ── Per-source fetchers ───────────────────────────────────────────────────────

def _fetch_remotive(*, position: str, tokens: list[str]) -> list["SearchCandidate"]:
    from app.services.job_search.service import SearchCandidate

    url = "https://remotive.com/api/remote-jobs?" + urlencode({"search": position, "limit": "40"})
    data = _get_json(url)
    jobs = data.get("jobs") or []
    out: list[SearchCandidate] = []
    for job in jobs:
        title = (job.get("title") or "").strip()
        company = (job.get("company_name") or "").strip()
        tags_raw = [t for t in (job.get("tags") or []) if isinstance(t, str)]
        # Remotive's server-side search is fuzzy — keep only role-relevant hits.
        if not title or not company or not _matches(tokens, title, tags_raw):
            continue
        description = _strip_html(job.get("description") or "")
        tags = tags_raw[:8]
        location = (job.get("candidate_required_location") or "Remote").strip() or "Remote"
        out.append(
            _candidate(
                source="remotive",
                title=title,
                company=company,
                description=description,
                location=location,
                apply_url=(job.get("url") or "").strip(),
                skills=tags,
                extra={"job_type": job.get("job_type"), "category": job.get("category"), "salary": job.get("salary")},
            )
        )
    return out


def _fetch_arbeitnow(*, position: str, tokens: list[str]) -> list["SearchCandidate"]:
    from app.services.job_search.service import SearchCandidate

    data = _get_json("https://www.arbeitnow.com/api/job-board-api")
    jobs = data.get("data") or []
    out: list[SearchCandidate] = []
    for job in jobs:
        title = (job.get("title") or "").strip()
        company = (job.get("company_name") or "").strip()
        if not title or not company or not _matches(tokens, title, job.get("tags") or []):
            continue
        description = _strip_html(job.get("description") or "")
        tags = [t for t in (job.get("tags") or []) if isinstance(t, str)][:8]
        location = (job.get("location") or "").strip() or ("Remote" if job.get("remote") else "Europe")
        out.append(
            _candidate(
                source="arbeitnow",
                title=title,
                company=company,
                description=description,
                location=location,
                apply_url=(job.get("url") or "").strip(),
                skills=tags,
                extra={"remote": job.get("remote"), "job_types": job.get("job_types")},
            )
        )
    return out


def _fetch_remoteok(*, position: str, tokens: list[str]) -> list["SearchCandidate"]:
    from app.services.job_search.service import SearchCandidate

    data = _get_json("https://remoteok.com/api")
    jobs = data if isinstance(data, list) else []
    out: list[SearchCandidate] = []
    for job in jobs:
        title = (job.get("position") or "").strip()
        company = (job.get("company") or "").strip()
        if not title or not company or not _matches(tokens, title, job.get("tags") or []):
            continue
        description = _strip_html(job.get("description") or "")
        tags = [t for t in (job.get("tags") or []) if isinstance(t, str)][:8]
        location = (job.get("location") or "").strip() or "Remote"
        apply_url = (job.get("apply_url") or job.get("url") or "").strip()
        out.append(
            _candidate(
                source="remoteok",
                title=title,
                company=company,
                description=description,
                location=location,
                apply_url=apply_url,
                skills=tags,
                extra={"salary_min": job.get("salary_min"), "salary_max": job.get("salary_max")},
            )
        )
    return out


# ── Helpers ───────────────────────────────────────────────────────────────────

def _candidate(
    *,
    source: str,
    title: str,
    company: str,
    description: str,
    location: str,
    apply_url: str,
    skills: list[str],
    extra: dict[str, Any],
) -> "SearchCandidate":
    from app.services.job_search.service import SearchCandidate
    from app.services.job_search.skill_extractor import extract_skills_from_text

    title = _clean(title)
    company = _clean(company)
    if not skills:
        skills = extract_skills_from_text(description)[:8]
    snippet = description[:280].strip()
    if len(description) > 280:
        snippet += "..."
    if not snippet:
        snippet = f"{company} is hiring a {title}."
    return SearchCandidate(
        source=source,
        title=title,
        company=company,
        snippet=snippet,
        description=description or snippet,
        location=location,
        apply_url=apply_url,
        source_url=apply_url,
        skills=[s.strip() for s in skills if s and s.strip()],
        metadata={"provider": source, "web_search": True, **{k: v for k, v in extra.items() if v is not None}},
    )


def _get_json(url: str, timeout: float = 15.0) -> Any:
    request = Request(url=url, headers={"User-Agent": _USER_AGENT, "Accept": "application/json"}, method="GET")
    try:
        with urlopen(request, timeout=timeout) as response:
            return json.loads(response.read().decode("utf-8", errors="replace"))
    except (HTTPError, URLError, TimeoutError, json.JSONDecodeError) as exc:
        logger.warning("web job source request failed for %s: %s", url, exc)
        raise


def _keywords(position: str) -> list[str]:
    tokens = [t for t in re.split(r"[^a-zA-Z0-9+#]+", position.lower()) if len(t) >= 3 and t not in _STOPWORDS]
    return tokens or [position.lower().strip()]


def _matches(tokens: list[str], title: str, tags: list[Any]) -> bool:
    """True when the role keywords overlap the posting's title or tags."""
    haystack = title.lower() + " " + " ".join(str(t).lower() for t in tags)
    return any(token in haystack for token in tokens)


def _relevance(tokens: list[str], title: str, tags: list[Any]) -> int:
    """Count distinct role keywords present in the title (weighted) and tags."""
    title_lower = title.lower()
    tag_text = " ".join(str(t).lower() for t in tags)
    score = 0
    for token in tokens:
        if token in title_lower:
            score += 2
        elif token in tag_text:
            score += 1
    return score


def _clean(text: str) -> str:
    """Unescape HTML entities and collapse whitespace in a short field."""
    return re.sub(r"\s+", " ", html.unescape(text or "")).strip()


def _strip_html(text: str) -> str:
    text = re.sub(r"<[^>]+>", " ", text or "")
    return re.sub(r"\s+", " ", html.unescape(text)).strip()


def _region_rank(location: str, region: str) -> int:
    """Lower sorts first: region match (0) < remote/worldwide (1) < everything else (2)."""
    lowered = (location or "").lower()
    region_keywords = {
        "canada": ["canada", "toronto", "vancouver", "montreal", "ontario"],
        "us": ["usa", "united states", "u.s", "new york", "san francisco", "remote (us"],
        "europe": ["europe", "london", "berlin", "amsterdam", "germany", "uk", "eu "],
        "middle east": ["dubai", "uae", "saudi", "riyadh", "qatar", "middle east"],
    }
    for keyword in region_keywords.get(region, []):
        if keyword in lowered:
            return 0
    if any(k in lowered for k in ["remote", "worldwide", "anywhere"]):
        return 1
    return 2
