"""Match agent wrapper."""

from dataclasses import dataclass, field

from app.schemas.job import JobNormalized
from app.schemas.match import MatchResult
from app.schemas.profile import Profile
from app.services.matching.service import score_match


@dataclass(slots=True)
class MatchAgentInput:
    profile: Profile
    jobs: list[JobNormalized]


@dataclass(slots=True)
class MatchAgentOutput:
    matches: list[MatchResult]
    logs: list[str] = field(default_factory=list)


def run_match_agent(payload: MatchAgentInput) -> MatchAgentOutput:
    logs = [f"match_agent:start jobs={len(payload.jobs)}"]
    matches = [score_match(payload.profile, job) for job in payload.jobs]
    matches.sort(key=lambda result: result.similarity, reverse=True)
    logs.append(f"match_agent:completed matches={len(matches)}")
    return MatchAgentOutput(matches=matches, logs=logs)
