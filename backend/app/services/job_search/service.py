"""Real job search service using JSearch API with variant expansion.

Replaces the previous mock/deterministic adapters with live API data.
Falls back to a clear error if JSEARCH_API_KEY is not configured.
"""

from __future__ import annotations

from dataclasses import dataclass
import hashlib
import logging
import re

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
    """Search for real jobs using JSearch API with variant expansion.

    Raises RuntimeError if JSEARCH_API_KEY is not configured.
    """
    from app.core.config import settings
    from app.services.job_search.jsearch_adapter import jsearch_search, parse_jsearch_results

    if not settings.jsearch_api_key:
        raise RuntimeError(
            "JSEARCH_API_KEY is required for job search. "
            "Sign up for a free key at https://rapidapi.com/letscrape-6bRBa3QguO5/api/jsearch"
        )

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
