"""Resume agent service for truth-preserving tailoring."""

from app.schemas.job import JobNormalized
from app.schemas.profile import Profile
from app.schemas.resume import TailoredResume


def build_tailored_resume(base_resume: str, profile: Profile, job: JobNormalized) -> TailoredResume:
    """Assemble a structured prompt and produce deterministic demo-tailored resume."""

    prompt = _build_prompt(base_resume=base_resume, profile=profile, job=job)
    tailored = (
        f"{base_resume}\n\n"
        f"Target Role: {job.title} at {job.company}\n"
        f"Location: {job.location or 'N/A'}\n"
        f"Relevant Skills: {', '.join(sorted(set(profile.skills).intersection(set(job.skills)))) or 'None listed'}\n"
        "Truth Policy: Keep all claims grounded in the base resume."
    )
    return TailoredResume(
        base_resume=base_resume,
        tailored_resume=tailored,
        truth_preserved=True,
        notes=["Structured prompt assembled", f"Prompt length: {len(prompt)} chars"],
    )


def _build_prompt(base_resume: str, profile: Profile, job: JobNormalized) -> str:
    return "\n".join(
        [
            "SYSTEM: You are a resume tailoring assistant.",
            "RULE: Preserve factual truth from base resume; do not invent achievements.",
            f"CANDIDATE: {profile.full_name} ({profile.email})",
            f"TARGET_JOB: {job.title} | {job.company} | {job.location or 'N/A'}",
            f"JOB_SKILLS: {', '.join(job.skills)}",
            f"BASE_RESUME:\n{base_resume}",
        ]
    )
