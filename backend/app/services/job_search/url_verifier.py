"""URL verification service for job apply links.

Validates that each apply_url is reachable, follows redirects,
and classifies whether the page requires login.
"""

from __future__ import annotations

import logging
import re
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

logger = logging.getLogger(__name__)

# Known ATS portal patterns that require login
_LOGIN_REQUIRED_PATTERNS = [
    r"greenhouse\.io/",
    r"lever\.co/",
    r"workday\.com/",
    r"icims\.com/",
    r"myworkdayjobs\.com/",
    r"taleo\.net/",
    r"smartrecruiters\.com/",
    r"ashbyhq\.com/",
    r"breezy\.hr/",
]

# Patterns that suggest a simple/direct application
_DIRECT_APPLY_PATTERNS = [
    r"mailto:",
    r"email.*resume",
    r"send.*resume",
    r"apply.*email",
]


class URLVerificationResult:
    __slots__ = ("url", "status", "final_url", "http_code", "page_type", "error")

    def __init__(
        self,
        url: str,
        status: str = "unknown",
        final_url: str | None = None,
        http_code: int | None = None,
        page_type: str = "unknown",
        error: str | None = None,
    ) -> None:
        self.url = url
        self.status = status  # verified, redirect, dead, requires_login, timeout
        self.final_url = final_url or url
        self.http_code = http_code
        self.page_type = page_type  # direct, ats_portal, company_site, unknown
        self.error = error


def verify_url(url: str, timeout: float = 5.0) -> URLVerificationResult:
    """Verify a single URL by sending a HEAD request (falls back to GET)."""

    if not url or not url.startswith("http"):
        return URLVerificationResult(url=url, status="dead", error="Invalid URL")

    # Check URL patterns first (no network needed)
    page_type = _classify_url_pattern(url)
    if page_type == "ats_portal":
        return URLVerificationResult(
            url=url, status="requires_login", page_type="ats_portal",
            error="Known ATS portal — likely requires login",
        )

    try:
        # Try HEAD first (cheaper)
        request = Request(url=url, method="HEAD")
        request.add_header("User-Agent", "Mozilla/5.0 (compatible; JobAgent/1.0)")
        with urlopen(request, timeout=timeout) as response:
            final_url = response.url
            status = "redirect" if final_url != url else "verified"
            return URLVerificationResult(
                url=url, status=status, final_url=final_url,
                http_code=response.status, page_type=page_type,
            )
    except HTTPError as exc:
        if exc.code == 405:
            # HEAD not allowed, try GET
            return _verify_with_get(url, timeout, page_type)
        if exc.code in {401, 403}:
            return URLVerificationResult(
                url=url, status="requires_login", http_code=exc.code,
                page_type=page_type, error=f"HTTP {exc.code}",
            )
        return URLVerificationResult(
            url=url, status="dead", http_code=exc.code,
            page_type=page_type, error=f"HTTP {exc.code}",
        )
    except URLError as exc:
        return URLVerificationResult(
            url=url, status="dead", page_type=page_type,
            error=f"Network error: {exc.reason}",
        )
    except TimeoutError:
        return URLVerificationResult(
            url=url, status="timeout", page_type=page_type,
            error="Connection timed out",
        )
    except Exception as exc:
        return URLVerificationResult(
            url=url, status="dead", page_type=page_type,
            error=str(exc)[:200],
        )


def _verify_with_get(url: str, timeout: float, page_type: str) -> URLVerificationResult:
    """Fallback to GET when HEAD is not allowed."""
    try:
        request = Request(url=url, method="GET")
        request.add_header("User-Agent", "Mozilla/5.0 (compatible; JobAgent/1.0)")
        with urlopen(request, timeout=timeout) as response:
            final_url = response.url
            status = "redirect" if final_url != url else "verified"
            return URLVerificationResult(
                url=url, status=status, final_url=final_url,
                http_code=response.status, page_type=page_type,
            )
    except HTTPError as exc:
        if exc.code in {401, 403}:
            return URLVerificationResult(
                url=url, status="requires_login", http_code=exc.code,
                page_type=page_type, error=f"HTTP {exc.code}",
            )
        return URLVerificationResult(
            url=url, status="dead", http_code=exc.code,
            page_type=page_type, error=f"HTTP {exc.code}",
        )
    except Exception as exc:
        return URLVerificationResult(
            url=url, status="dead", page_type=page_type,
            error=str(exc)[:200],
        )


def verify_urls(urls: list[str], timeout: float = 5.0) -> dict[str, URLVerificationResult]:
    """Verify multiple URLs. Returns a map of url → result."""
    results: dict[str, URLVerificationResult] = {}
    for url in urls:
        results[url] = verify_url(url, timeout=timeout)
    return results


def _classify_url_pattern(url: str) -> str:
    """Classify a URL by pattern matching — no network request needed."""
    lowered = url.lower()
    for pattern in _LOGIN_REQUIRED_PATTERNS:
        if re.search(pattern, lowered):
            return "ats_portal"
    for pattern in _DIRECT_APPLY_PATTERNS:
        if re.search(pattern, lowered):
            return "direct"
    return "company_site"
