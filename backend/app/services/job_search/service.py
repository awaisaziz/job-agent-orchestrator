"""Job search service.

Uses the JSearch API (RapidAPI) for live job data when ``JSEARCH_API_KEY`` is
configured. When no key is present the service falls back to a deterministic,
region-aware mock generator so the whole pipeline runs end-to-end out of the box
(demo mode). Add a JSearch key to ``.env`` to switch to real listings.
"""

from __future__ import annotations

from dataclasses import dataclass
import hashlib
import logging
import re
from urllib.parse import quote_plus

logger = logging.getLogger(__name__)


@dataclass(slots=True)
class SearchCandidate:
    source: str
    title: str
    company: str
    snippet: str
    description: str
    location: str
    apply_url: str
    source_url: str
    skills: list[str]
    metadata: dict[str, object]


def search_jobs(*, position: str, location: str | None) -> list[SearchCandidate]:
    """Search for jobs.

    Priority:
      1. JSearch API (Google for Jobs) when ``JSEARCH_API_KEY`` is configured.
      2. Real keyless **web search** across free public job boards (Remotive,
         Arbeitnow, RemoteOK) — works with no API key.
      3. Deterministic region-aware demo jobs (offline fallback only).
    """
    from app.core.config import settings

    if settings.jsearch_api_key:
        return _search_jobs_live(position=position, location=location)

    # No JSearch key → genuinely search the web for real jobs (no key required).
    try:
        from app.services.job_search.web_search_adapter import web_search_jobs

        web_results = web_search_jobs(position=position, location=location)
    except Exception:
        logger.exception("Web job search failed — falling back to demo jobs")
        web_results = []

    if web_results:
        return web_results

    logger.info("Web job search returned no results — using region-aware demo jobs")
    return generate_mock_jobs(position=position, location=location)


def _search_jobs_live(*, position: str, location: str | None) -> list[SearchCandidate]:
    """Search for real jobs using JSearch API with variant expansion."""
    from app.core.config import settings
    from app.services.job_search.jsearch_adapter import jsearch_search, parse_jsearch_results

    normalized_location = (location or "").strip()
    countries = [c.strip() for c in settings.job_search_country.split(",") if c.strip()]

    # Build primary search query
    query_parts = [position]
    if normalized_location:
        query_parts.append(f"in {normalized_location}")
    primary_query = " ".join(query_parts)

    # Generate search variant for broader results
    variants = _search_variants(position)
    variant_query = None
    if len(variants) > 1:
        alt_title = variants[1]
        alt_parts = [alt_title]
        if normalized_location:
            alt_parts.append(f"in {normalized_location}")
        variant_query = " ".join(alt_parts)

    all_raw: list[dict] = []

    # Primary search across all configured countries
    for country in countries:
        try:
            raw = jsearch_search(
                query=primary_query,
                country=country,
                num_pages=settings.job_search_num_pages,
                api_key=settings.jsearch_api_key,
                api_host=settings.jsearch_api_host,
            )
            all_raw.extend(raw)
            logger.info(
                "JSearch primary: query=%r country=%s results=%d",
                primary_query, country, len(raw),
            )
        except Exception:
            logger.exception("JSearch primary search failed for country=%s", country)

    # Variant search (uses 1 extra API call, broader coverage)
    if variant_query and len(all_raw) < 30:
        for country in countries[:1]:  # Only first country for variant to save quota
            try:
                raw = jsearch_search(
                    query=variant_query,
                    country=country,
                    num_pages=max(1, settings.job_search_num_pages - 1),
                    api_key=settings.jsearch_api_key,
                    api_host=settings.jsearch_api_host,
                )
                all_raw.extend(raw)
                logger.info(
                    "JSearch variant: query=%r country=%s results=%d",
                    variant_query, country, len(raw),
                )
            except Exception:
                logger.exception("JSearch variant search failed")

    # Parse and deduplicate
    candidates = parse_jsearch_results(all_raw)
    deduped = _deduplicate(candidates)
    logger.info(
        "Job search complete: position=%r location=%r raw=%d deduped=%d",
        position, normalized_location, len(candidates), len(deduped),
    )
    return deduped


def _deduplicate(candidates: list[SearchCandidate]) -> list[SearchCandidate]:
    """Deduplicate by company + title + apply_url hash."""
    seen: dict[str, SearchCandidate] = {}
    for candidate in candidates:
        key = _job_key(candidate.title, candidate.company, candidate.apply_url)
        if key not in seen:
            seen[key] = candidate
    return list(seen.values())


def _search_variants(position: str) -> list[str]:
    """Generate related title variants for broader search coverage."""
    normalized = _canonical_title(position)
    lowered = normalized.lower()
    variants = [normalized]

    if "backend" in lowered:
        variants.extend(["Platform Engineer", "API Engineer", "Software Engineer"])
    elif "frontend" in lowered:
        variants.extend(["UI Engineer", "React Developer", "Software Engineer"])
    elif "full stack" in lowered or "fullstack" in lowered:
        variants.extend(["Software Engineer", "Web Developer"])
    elif "data" in lowered:
        variants.extend(["Data Engineer", "Analytics Engineer", "Platform Engineer"])
    elif "ai" in lowered or "ml" in lowered or "machine learning" in lowered:
        variants.extend(["AI Engineer", "ML Engineer", "Platform Engineer"])
    elif "devops" in lowered or "sre" in lowered:
        variants.extend(["Platform Engineer", "Infrastructure Engineer", "Cloud Engineer"])
    elif "mobile" in lowered:
        variants.extend(["iOS Developer", "Android Developer", "Software Engineer"])
    else:
        variants.extend([f"{normalized} Engineer", "Software Engineer", "Platform Engineer"])

    # Deduplicate while preserving order
    seen: set[str] = set()
    ordered: list[str] = []
    for variant in variants:
        key = variant.lower()
        if key not in seen:
            seen.add(key)
            ordered.append(variant)
    return ordered


def _canonical_title(position: str) -> str:
    normalized = " ".join(part.capitalize() for part in position.split())
    return normalized or "Software Engineer"


def _job_key(title: str, company: str, apply_url: str) -> str:
    fingerprint = f"{title.lower()}::{company.lower()}::{apply_url.lower()}"
    return hashlib.sha256(fingerprint.encode("utf-8")).hexdigest()


def _slugify(value: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", value.lower()).strip("-") or "role"


# ── Demo mode: deterministic, region-aware mock job generator ─────────────────

# Each region maps to (cities, employers). Cities and employers are combined with
# the requested title + variants to produce realistic-looking demo listings.
_REGION_DATA: dict[str, tuple[list[str], list[str]]] = {
    "canada": (
        ["Toronto, ON", "Vancouver, BC", "Montreal, QC", "Ottawa, ON", "Remote (Canada)"],
        ["Shopify", "Wealthsimple", "Cohere", "Faire", "Clio", "Hootsuite", "Ada", "1Password"],
    ),
    "us": (
        ["San Francisco, CA", "New York, NY", "Seattle, WA", "Austin, TX", "Boston, MA", "Remote (US)"],
        ["Stripe", "Databricks", "Notion", "Cloudflare", "Plaid", "Airbnb", "Figma", "Ramp"],
    ),
    "europe": (
        ["London, UK", "Berlin, DE", "Amsterdam, NL", "Dublin, IE", "Paris, FR", "Remote (Europe)"],
        ["Revolut", "Spotify", "Adyen", "Wise", "Booking.com", "Datadog EU", "SAP", "Klarna"],
    ),
    "middle east": (
        ["Dubai, UAE", "Abu Dhabi, UAE", "Riyadh, SA", "Doha, QA", "Remote (Middle East)"],
        ["Careem", "Talabat", "Noon", "Tabby", "Property Finder", "Chalhoub Group", "Aramco Digital", "Kitopi"],
    ),
}

_SKILL_PROFILES: dict[str, list[str]] = {
    "backend": ["Python", "FastAPI", "PostgreSQL", "Docker", "AWS", "Kubernetes", "REST APIs"],
    "frontend": ["React", "TypeScript", "Next.js", "CSS", "Testing", "Accessibility"],
    "full stack": ["React", "TypeScript", "Node", "PostgreSQL", "Docker", "AWS"],
    "data": ["Python", "SQL", "Airflow", "Spark", "dbt", "Snowflake", "ETL"],
    "ai": ["Python", "PyTorch", "LLM", "LangChain", "RAG", "Machine Learning", "OpenAI"],
    "ml": ["Python", "PyTorch", "TensorFlow", "Machine Learning", "MLOps", "Kubernetes"],
    "devops": ["Kubernetes", "Docker", "Terraform", "AWS", "CI/CD", "Prometheus"],
    "mobile": ["Swift", "Kotlin", "React Native", "REST APIs", "CI/CD"],
    "product": ["Roadmapping", "Analytics", "SQL", "A/B Testing", "Stakeholder Management"],
    "design": ["Figma", "Prototyping", "Design Systems", "User Research", "Accessibility"],
}


def detect_region(location: str | None) -> str:
    """Map a free-text location to one of the supported demo regions."""
    text = (location or "").lower()
    if not text or "all" in text:
        return "us"
    if any(k in text for k in ["remote"]):
        # Remote without a region hint → default to US-centric remote roles.
        pass
    canada = ["canada", "toronto", "vancouver", "montreal", "ottawa", "ontario", " on", " bc", " qc"]
    europe = ["europe", "london", "berlin", "amsterdam", "dublin", "paris", "uk", "germany", "netherlands", "ireland", "france", "madrid", "spain"]
    middle_east = ["middle east", "dubai", "abu dhabi", "riyadh", "doha", "uae", "saudi", "qatar", "kuwait", "bahrain", "oman"]
    us = ["united states", "usa", "us", "new york", "san francisco", "seattle", "austin", "boston", "california", "texas"]
    for keyword in middle_east:
        if keyword in text:
            return "middle east"
    for keyword in europe:
        if keyword in text:
            return "europe"
    for keyword in canada:
        if keyword in text:
            return "canada"
    for keyword in us:
        if keyword in text:
            return "us"
    return "us"


def _skill_profile_for(position: str) -> list[str]:
    lowered = position.lower()
    for key, skills in _SKILL_PROFILES.items():
        if key in lowered:
            return skills
    return ["Communication", "Problem Solving", "Git", "Agile", "Collaboration"]


def generate_mock_jobs(*, position: str, location: str | None) -> list[SearchCandidate]:
    """Produce deterministic, realistic demo jobs for the given role and region.

    Used when no JSEARCH_API_KEY is configured so the full pipeline is demoable
    offline. Apply URLs point to real Google Jobs searches, so "Open listing"
    works and links are genuinely reachable.
    """
    canonical = _canonical_title(position)
    variants = _search_variants(position)[:3] or [canonical]
    region = detect_region(location)
    cities, employers = _REGION_DATA[region]
    base_skills = _skill_profile_for(position)
    sources = ["linkedin", "indeed", "company_site"]

    candidates: list[SearchCandidate] = []
    count = min(len(employers), 8)
    for index in range(count):
        title = variants[index % len(variants)]
        company = employers[index]
        city = cities[index % len(cities)]
        source = sources[index % len(sources)]
        # Rotate the skill emphasis a little per card for variety.
        skills = base_skills[: 4 + (index % 3)]
        seniority = ["Senior ", "", "Staff ", "", "Lead ", "", "Junior ", ""][index % 8]
        full_title = f"{seniority}{title}".strip()
        snippet = (
            f"{company} is hiring a {full_title} in {city}. "
            f"Work with {', '.join(skills[:3])} on production systems."
        )
        description = (
            f"{company} is looking for a {full_title} to join the team in {city}.\n\n"
            f"You will build and ship features using {', '.join(skills)}. "
            "This is a demo listing generated locally because no JSEARCH_API_KEY is set — "
            "add a key to .env to pull live postings.\n\n"
            f"Requirements: experience with {', '.join(skills[:3])}; strong collaboration and communication."
        )
        query = quote_plus(f"{company} {full_title} careers apply {city}")
        apply_url = f"https://www.google.com/search?q={query}&ibp=htl;jobs"
        source_url = f"https://www.google.com/search?q={query}"
        candidates.append(
            SearchCandidate(
                source=source,
                title=full_title,
                company=company,
                snippet=snippet,
                description=description,
                location=city,
                apply_url=apply_url,
                source_url=source_url,
                skills=skills,
                metadata={"provider": source, "mock": True, "region": region},
            )
        )
    logger.info("Generated %d demo jobs for position=%r region=%s", len(candidates), position, region)
    return candidates
