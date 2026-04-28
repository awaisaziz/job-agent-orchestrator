"""Application quality helper services."""

from app.schemas.pipeline import SkillGapReport


def calculate_ats_score(profile_skills: list[str], job_skills: list[str], similarity: float) -> float:
    """Heuristic ATS score in [0,100] using skill coverage and semantic similarity."""

    normalized_profile = {skill.lower() for skill in profile_skills}
    normalized_job = {skill.lower() for skill in job_skills}
    if not normalized_job:
        return round(max(0.0, min(100.0, similarity * 100.0)), 2)

    overlap = len(normalized_profile.intersection(normalized_job))
    coverage = overlap / len(normalized_job)
    blended = (coverage * 0.7) + (similarity * 0.3)
    return round(max(0.0, min(100.0, blended * 100.0)), 2)


def detect_skill_gaps(profile_skills: list[str], job_skills: list[str]) -> SkillGapReport:
    """Return profile/job overlap and uncovered required skills."""

    profile_lookup = {skill.lower(): skill for skill in profile_skills}
    matched = []
    missing = []
    for skill in job_skills:
        if skill.lower() in profile_lookup:
            matched.append(profile_lookup[skill.lower()])
        else:
            missing.append(skill)
    return SkillGapReport(matched_skills=sorted(set(matched)), missing_skills=sorted(set(missing)))
