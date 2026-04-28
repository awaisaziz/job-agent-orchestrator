"""Profile intake helpers for uploaded resume content."""

from __future__ import annotations

from dataclasses import dataclass
import re


_KNOWN_SKILLS = {
    "python",
    "fastapi",
    "sql",
    "postgresql",
    "docker",
    "kubernetes",
    "aws",
    "azure",
    "gcp",
    "react",
    "typescript",
    "javascript",
    "node",
    "java",
    "spring",
    "llm",
    "openai",
    "agentic ai",
    "machine learning",
    "airflow",
    "celery",
    "playwright",
    "selenium",
    "git",
}


@dataclass(slots=True)
class ParsedProfile:
    full_name: str
    skills: list[str]
    summary: str


def parse_resume_text(*, resume_text: str, email: str, full_name: str | None = None) -> ParsedProfile:
    """Extract a lightweight profile summary from uploaded resume text."""

    cleaned = "\n".join(line.strip() for line in resume_text.splitlines() if line.strip())
    inferred_name = full_name or _infer_name(cleaned, email)
    lowered = cleaned.lower()
    skills = sorted({skill.title() if " " not in skill else skill for skill in _KNOWN_SKILLS if skill in lowered})
    summary_bits = [f"{inferred_name} profile parsed from uploaded resume."]
    if skills:
        summary_bits.append(f"Detected skills: {', '.join(skills[:10])}.")
    else:
        summary_bits.append("No known skills detected from the current parser dictionary.")
    return ParsedProfile(full_name=inferred_name, skills=skills, summary=" ".join(summary_bits))


def _infer_name(cleaned_resume: str, email: str) -> str:
    first_line = cleaned_resume.splitlines()[0].strip() if cleaned_resume else ""
    if first_line and "@" not in first_line and len(first_line.split()) <= 4:
        return re.sub(r"\s+", " ", first_line)

    local_part = email.split("@", 1)[0].replace(".", " ").replace("_", " ").replace("-", " ")
    guess = " ".join(part.capitalize() for part in local_part.split() if part)
    return guess or "Candidate"
