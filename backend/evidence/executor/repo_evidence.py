from __future__ import annotations

from schemas.entity import ResolvedEntity
from evidence import EvidenceBuilder
from sources.github.client import GitHubAPI

# from planner.evidence_planner import EvidencePlanner


class RepositoryEvidenceService:
    def __init__(self):
        self.github = GitHubAPI()
        self.builder = EvidenceBuilder()
        # self.planner = EvidencePlanner()

    def collect(
        self,
        entity: ResolvedEntity | str | None = None
    ):
        if isinstance(entity, str):
            raise ValueError("Entity-based collection expects a ResolvedEntity")

        if entity is None:
            raise ValueError("Entity is required")

        # plan = self.planner.plan(entity, include_reddit=include_reddit)
        github_source = self._get_source(entity, "github")

        repository = None
        readme = None
        releases = None
        issues = None
        pull_requests = None
        commit_activity = None
        planning = None
        discussions = None

        if github_source:
            owner, repo = self._split_github_identifier(github_source.identifier)
            repository = self.github.get_repository(owner, repo)
            readme = self.github.get_readme(owner, repo)
            releases = self.github.get_releases(owner, repo)
            issues = self.github.get_issues(owner=owner, repo=repo)
            pull_requests = self.github.get_pull_requests(owner=owner, repo=repo)
            commit_activity = self.github.get_commit_activity(owner, repo)
            planning = self.github.get_planning_signals(owner, repo)
            discussions = self.github.get_discussion_signals(owner, repo)


        evidence = self.builder.build(
            repository=repository,
            readme=readme,
            releases=releases,
            issues=issues,
            pull_requests=pull_requests,
            commit_activity=commit_activity,
            planning=planning,
            discussions=discussions,
        )

        return evidence

    @staticmethod
    def _get_source(entity: ResolvedEntity, source_name: str):
        for source in entity.sources:
            if source.source == source_name:
                return source
        return None

    @staticmethod
    def _split_github_identifier(identifier: str) -> tuple[str, str]:
        if "/" not in identifier:
            raise ValueError(f"Invalid GitHub identifier: {identifier}")
        return identifier.split("/", 1)
