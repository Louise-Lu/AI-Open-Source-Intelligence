from __future__ import annotations

from dataclasses import dataclass, field

from schemas.entity import ResolvedEntity


@dataclass
class EvidencePlan:
    required_tools: list[str] = field(default_factory=list)


class EvidencePlanner:
    def plan(self, entity: ResolvedEntity, include_reddit: bool = False) -> EvidencePlan:
        tools: list[str] = []
        source_names = {source.source for source in entity.sources}

        if "github" in source_names:
            tools.extend([
                "github_repository",
                "github_readme",
                "github_release",
                "github_issue",
                "github_pull_request",
                "github_commit_activity",
                "github_planning",
                "github_discussion",
            ])

        if "huggingface" in source_names:
            tools.append("huggingface_model")

        if include_reddit:
            tools.append("reddit_search")

        return EvidencePlan(required_tools=tools)
