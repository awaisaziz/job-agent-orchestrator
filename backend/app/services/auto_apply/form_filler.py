"""Playwright-based form filler for simple job application forms.

Only targets pages classified as 'simple_form' — pages with a visible
application form that includes a file upload input and no login wall.

Safety rules:
- Does NOT submit if CAPTCHA is detected
- Adds random delays between actions (1-3s) for human-like behavior
- Takes before/after screenshots for audit
- Logs every form interaction
"""

from __future__ import annotations

import logging
import random
import re
import time
from dataclasses import dataclass, field
from pathlib import Path

logger = logging.getLogger(__name__)


@dataclass(slots=True)
class FormFillResult:
    success: bool
    actions: list[str] = field(default_factory=list)
    screenshot_before: str | None = None
    screenshot_after: str | None = None
    error: str | None = None


# Common form field label patterns → profile field mapping
_FIELD_MAP = {
    "name": "full_name",
    "full name": "full_name",
    "first name": "first_name",
    "last name": "last_name",
    "email": "email",
    "e-mail": "email",
    "phone": "phone",
    "telephone": "phone",
    "mobile": "phone",
    "location": "location",
    "city": "location",
    "linkedin": "linkedin_url",
    "website": "website",
    "portfolio": "website",
    "cover letter": "cover_letter",
}


def fill_and_submit_form(
    *,
    url: str,
    profile: dict[str, str],
    resume_path: str | None = None,
    screenshots_dir: str | None = None,
) -> FormFillResult:
    """Load a simple application form page, fill fields, upload resume, and submit.

    Args:
        url: The apply page URL
        profile: Dict with keys like full_name, email, phone, location, etc.
        resume_path: Path to the tailored resume PDF
        screenshots_dir: Directory for audit screenshots
    """
    try:
        from playwright.sync_api import sync_playwright
    except ImportError:
        return FormFillResult(
            success=False, error="Playwright is not installed",
            actions=["form_filler:SKIPPED playwright not available"],
        )

    actions: list[str] = [f"form_filler:opening {url}"]

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        context = browser.new_context(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
        )
        page = context.new_page()

        try:
            page.goto(url, timeout=20000, wait_until="domcontentloaded")
            _human_delay()
            actions.append("form_filler:page loaded")
        except Exception as exc:
            browser.close()
            return FormFillResult(
                success=False, error=f"Failed to load: {exc}",
                actions=[*actions, f"form_filler:FAILED load error: {exc}"],
            )

        # Check for CAPTCHA before proceeding
        content = page.content().lower()
        captcha_indicators = ["recaptcha", "hcaptcha", "cf-turnstile", "captcha"]
        if any(ind in content for ind in captcha_indicators):
            browser.close()
            return FormFillResult(
                success=False, error="CAPTCHA detected — skipping",
                actions=[*actions, "form_filler:SKIPPED captcha detected"],
            )

        # Screenshot before
        screenshot_before = None
        if screenshots_dir:
            Path(screenshots_dir).mkdir(parents=True, exist_ok=True)
            slug = re.sub(r"[^a-z0-9]+", "-", url.lower())[:60]
            screenshot_before = str(Path(screenshots_dir) / f"form-before-{slug}.png")
            try:
                page.screenshot(path=screenshot_before, full_page=False)
                actions.append("form_filler:screenshot_before captured")
            except Exception:
                screenshot_before = None

        # Fill text fields
        filled_count = 0
        for label_pattern, profile_key in _FIELD_MAP.items():
            value = profile.get(profile_key, "")
            if not value:
                continue
            try:
                # Try by label first
                locator = page.get_by_label(label_pattern, exact=False)
                if locator.count() > 0:
                    locator.first.fill("")
                    _human_delay(0.5, 1.5)
                    locator.first.type(value, delay=random.randint(30, 80))
                    actions.append(f"form_filler:filled '{label_pattern}' via label")
                    filled_count += 1
                    continue
            except Exception:
                pass

            try:
                # Try by placeholder
                locator = page.get_by_placeholder(label_pattern, exact=False)
                if locator.count() > 0:
                    locator.first.fill("")
                    _human_delay(0.5, 1.5)
                    locator.first.type(value, delay=random.randint(30, 80))
                    actions.append(f"form_filler:filled '{label_pattern}' via placeholder")
                    filled_count += 1
                except Exception:
                    pass

        actions.append(f"form_filler:filled {filled_count} fields")

        # Upload resume
        if resume_path and Path(resume_path).exists():
            try:
                file_inputs = page.query_selector_all('input[type="file"]')
                if file_inputs:
                    file_inputs[0].set_input_files(resume_path)
                    _human_delay()
                    actions.append(f"form_filler:uploaded resume={Path(resume_path).name}")
                else:
                    actions.append("form_filler:no file input found")
            except Exception as exc:
                actions.append(f"form_filler:resume upload failed: {exc}")
        else:
            actions.append("form_filler:no resume file available")

        # Find and click submit button
        submitted = False
        submit_texts = ["submit", "apply", "send application", "submit application"]
        for text in submit_texts:
            try:
                button = page.get_by_role("button", name=text, exact=False)
                if button.count() > 0:
                    _human_delay(1.0, 2.0)
                    button.first.click()
                    _human_delay(2.0, 3.0)
                    actions.append(f"form_filler:clicked submit button='{text}'")
                    submitted = True
                    break
            except Exception:
                continue

        if not submitted:
            # Try generic submit
            try:
                submit_input = page.query_selector('input[type="submit"]')
                if submit_input:
                    _human_delay(1.0, 2.0)
                    submit_input.click()
                    _human_delay(2.0, 3.0)
                    actions.append("form_filler:clicked input[type=submit]")
                    submitted = True
                else:
                    actions.append("form_filler:no submit button found")
            except Exception as exc:
                actions.append(f"form_filler:submit failed: {exc}")

        # Screenshot after
        screenshot_after = None
        if screenshots_dir:
            screenshot_after = str(Path(screenshots_dir) / f"form-after-{slug}.png")
            try:
                page.screenshot(path=screenshot_after, full_page=False)
                actions.append("form_filler:screenshot_after captured")
            except Exception:
                screenshot_after = None

        browser.close()

        return FormFillResult(
            success=submitted and filled_count >= 2,
            actions=actions,
            screenshot_before=screenshot_before,
            screenshot_after=screenshot_after,
            error=None if submitted else "Could not submit form",
        )


def _human_delay(min_sec: float = 1.0, max_sec: float = 3.0) -> None:
    """Add random delay to simulate human behavior."""
    time.sleep(random.uniform(min_sec, max_sec))
