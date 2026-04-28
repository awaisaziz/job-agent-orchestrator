"""Page classifier — determines whether a job apply URL is automatable.

Uses Playwright to load the page and classify it as:
  - email_apply: page contains mailto: link or "email your resume" text
  - simple_form: page has a form with file upload and no login fields
  - ats_portal: URL matches known ATS patterns (Greenhouse, Lever, etc.)
  - login_required: page has password input, OAuth buttons, or "sign in" text
  - captcha_detected: page has reCAPTCHA, hCaptcha, or Cloudflare challenge
  - unknown: could not determine
"""

from __future__ import annotations

import logging
import re
from dataclasses import dataclass, field
from pathlib import Path

logger = logging.getLogger(__name__)

# Known ATS portal URL patterns
_ATS_PATTERNS = [
    r"greenhouse\.io", r"lever\.co", r"workday\.com", r"myworkdayjobs\.com",
    r"icims\.com", r"taleo\.net", r"smartrecruiters\.com", r"ashbyhq\.com",
    r"breezy\.hr", r"jobvite\.com", r"ultipro\.com",
]

# Login indicators in page content
_LOGIN_INDICATORS = [
    "sign in", "log in", "login", "create an account", "register to apply",
    "password", "forgot password", "sign up to apply",
]

# CAPTCHA indicators
_CAPTCHA_INDICATORS = [
    "recaptcha", "hcaptcha", "cf-turnstile", "captcha", "challenge-platform",
    "cloudflare", "just a moment",
]

# Email apply indicators
_EMAIL_APPLY_INDICATORS = [
    "mailto:", "email your resume", "send your resume", "email us your",
    "apply via email", "send cv to", "submit your resume to",
]

# Simple form indicators
_FORM_INDICATORS = [
    'type="file"', "upload resume", "upload cv", "attach resume",
    "drop your resume", "choose file",
]


@dataclass(slots=True)
class ClassificationResult:
    url: str
    page_type: str  # email_apply, simple_form, ats_portal, login_required, captcha_detected, unknown
    confidence: float  # 0.0 to 1.0
    hr_email: str | None = None  # extracted email for email_apply pages
    screenshot_path: str | None = None
    details: list[str] = field(default_factory=list)


def classify_url_pattern(url: str) -> ClassificationResult | None:
    """Quick classification based on URL pattern alone (no network)."""
    lowered = url.lower()
    for pattern in _ATS_PATTERNS:
        if re.search(pattern, lowered):
            return ClassificationResult(
                url=url, page_type="ats_portal", confidence=0.9,
                details=[f"URL matches known ATS pattern: {pattern}"],
            )
    return None


def classify_page(url: str, screenshots_dir: str | None = None) -> ClassificationResult:
    """Load a page with Playwright and classify it for auto-apply feasibility.

    Falls back to URL-pattern-only classification if Playwright is not available.
    """
    # Quick URL pattern check first
    pattern_result = classify_url_pattern(url)
    if pattern_result and pattern_result.confidence >= 0.9:
        return pattern_result

    try:
        return _classify_with_playwright(url, screenshots_dir)
    except ImportError:
        logger.warning("Playwright not installed — using URL-pattern-only classification")
        return ClassificationResult(
            url=url, page_type="unknown", confidence=0.3,
            details=["Playwright not installed, cannot inspect page content"],
        )
    except Exception as exc:
        logger.exception("Page classification failed for %s", url)
        return ClassificationResult(
            url=url, page_type="unknown", confidence=0.1,
            details=[f"Classification error: {exc}"],
        )


def _classify_with_playwright(url: str, screenshots_dir: str | None) -> ClassificationResult:
    """Use Playwright to load page and inspect content."""
    from playwright.sync_api import sync_playwright

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        context = browser.new_context(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
        )
        page = context.new_page()

        try:
            page.goto(url, timeout=15000, wait_until="domcontentloaded")
            page.wait_for_timeout(2000)  # Let JS render
        except Exception as exc:
            browser.close()
            return ClassificationResult(
                url=url, page_type="unknown", confidence=0.2,
                details=[f"Failed to load page: {exc}"],
            )

        content = page.content().lower()
        page_text = page.inner_text("body").lower() if page.query_selector("body") else ""

        # Take screenshot for audit
        screenshot_path = None
        if screenshots_dir:
            Path(screenshots_dir).mkdir(parents=True, exist_ok=True)
            slug = re.sub(r"[^a-z0-9]+", "-", url.lower())[:80]
            screenshot_path = str(Path(screenshots_dir) / f"classify-{slug}.png")
            try:
                page.screenshot(path=screenshot_path, full_page=False)
            except Exception:
                screenshot_path = None

        result = _analyze_page_content(url, content, page_text, screenshot_path)

        # Try to extract HR email if it's an email_apply page
        if result.page_type == "email_apply":
            emails = re.findall(r"[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}", content)
            # Filter out common non-HR emails
            hr_emails = [e for e in emails if not any(x in e.lower() for x in ["noreply", "no-reply", "support", "info@"])]
            if hr_emails:
                result.hr_email = hr_emails[0]
                result.details.append(f"Extracted HR email: {hr_emails[0]}")

        browser.close()
        return result


def _analyze_page_content(
    url: str, content: str, page_text: str, screenshot_path: str | None
) -> ClassificationResult:
    """Analyze loaded page content to classify page type."""
    details: list[str] = []

    # Check for CAPTCHA (highest priority — blocks everything)
    for indicator in _CAPTCHA_INDICATORS:
        if indicator in content:
            details.append(f"CAPTCHA detected: {indicator}")
            return ClassificationResult(
                url=url, page_type="captcha_detected", confidence=0.85,
                screenshot_path=screenshot_path, details=details,
            )

    # Check for login requirements
    login_signals = sum(1 for ind in _LOGIN_INDICATORS if ind in page_text)
    has_password_field = 'type="password"' in content or "type='password'" in content
    if has_password_field or login_signals >= 2:
        details.append(f"Login signals found: {login_signals}, password_field={has_password_field}")
        return ClassificationResult(
            url=url, page_type="login_required", confidence=0.8,
            screenshot_path=screenshot_path, details=details,
        )

    # Check for email apply
    email_signals = sum(1 for ind in _EMAIL_APPLY_INDICATORS if ind in content or ind in page_text)
    if email_signals >= 1:
        details.append(f"Email apply signals: {email_signals}")
        return ClassificationResult(
            url=url, page_type="email_apply", confidence=0.7,
            screenshot_path=screenshot_path, details=details,
        )

    # Check for simple form
    form_signals = sum(1 for ind in _FORM_INDICATORS if ind in content)
    has_form = "<form" in content
    if has_form and form_signals >= 1:
        details.append(f"Form detected with upload signals: {form_signals}")
        return ClassificationResult(
            url=url, page_type="simple_form", confidence=0.6,
            screenshot_path=screenshot_path, details=details,
        )

    # Fallback: ATS pattern check on final URL
    pattern_result = classify_url_pattern(url)
    if pattern_result:
        return pattern_result

    details.append("No clear classification signals found")
    return ClassificationResult(
        url=url, page_type="unknown", confidence=0.2,
        screenshot_path=screenshot_path, details=details,
    )
