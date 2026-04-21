"""Resume agent service for truth-preserving tailoring."""

from app.schemas.job import JobNormalized
from app.schemas.profile import Profile
from app.schemas.resume import TailoredResume
from app.services.llm_gateway import LLMGenerateRequest, generate_text


def build_tailored_resume(base_resume: str, profile: Profile, job: JobNormalized, model_name: str) -> TailoredResume:
    """Assemble a structured prompt and produce a tailored resume output."""

    prompt = _build_prompt(base_resume=base_resume, profile=profile, job=job)
    deterministic_fallback = (
        f"{base_resume}\n\n"
        f"Target Role: {job.title} at {job.company}\n"
        f"Location: {job.location or 'N/A'}\n"
        f"Relevant Skills: {', '.join(sorted(set(profile.skills).intersection(set(job.skills)))) or 'None listed'}\n"
        "Truth Policy: Keep all claims grounded in the base resume."
    )

    notes = ["Structured prompt assembled", f"Prompt length: {len(prompt)} chars", f"Model selected: {model_name}"]
    try:
        response = generate_text(
            LLMGenerateRequest(
                model_name=model_name,
                system_prompt="You are a resume tailoring assistant that preserves factual truth.",
                prompt=prompt,
                temperature=0.2,
                max_tokens=800,
            )
        )
        tailored = response.output_text or deterministic_fallback
        notes.append(f"LLM provider used: {response.provider}")
    except Exception as exc:  # nosec: fallback required when provider credentials are absent in local env
        tailored = deterministic_fallback
        notes.append(f"LLM fallback used: {exc}")

    return TailoredResume(
        base_resume=base_resume,
        tailored_resume=tailored,
        truth_preserved=True,
        notes=notes,
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
