"""Dataclasses for roborev review data."""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class ReviewJob:
    """A single roborev review job from `roborev list --json`."""

    id: str
    git_ref: str = ""
    branch: str = ""
    agent: str = ""
    status: str = ""
    verdict: str = ""  # "pass", "fail", or ""
    addressed: bool = False
    commit_subject: str = ""

    @classmethod
    def from_dict(cls, data: dict) -> ReviewJob:
        return cls(
            id=data.get("id", ""),
            git_ref=data.get("git_ref", ""),
            branch=data.get("branch", ""),
            agent=data.get("agent", ""),
            status=data.get("status", ""),
            verdict=data.get("verdict", ""),
            addressed=data.get("addressed", False),
            commit_subject=data.get("commit_subject", ""),
        )


@dataclass
class ReviewDetail:
    """Detailed review from `roborev show --json --job <id>`."""

    id: str
    job_id: str = ""
    agent: str = ""
    output: str = ""
    addressed: bool = False
    job: ReviewJob | None = field(default=None)

    @classmethod
    def from_dict(cls, data: dict) -> ReviewDetail:
        job_data = data.get("job")
        job = ReviewJob.from_dict(job_data) if job_data else None
        return cls(
            id=data.get("id", ""),
            job_id=data.get("job_id", ""),
            agent=data.get("agent", ""),
            output=data.get("output", ""),
            addressed=data.get("addressed", False),
            job=job,
        )
