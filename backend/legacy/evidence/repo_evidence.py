from __future__ import annotations

from types import SimpleNamespace

from shared_schemas.entity import ResolvedEntity
from evidence.builder import EvidenceBuilder
from sources.github.client import GitHubAPI


class RepositoryEvidenceService:
    def __init__(self):
        self.github = GitHubAPI()
        self.builder = EvidenceBuilder()

    def collect(
        self,
        entity: ResolvedEntity | str | None = None
    ):
        if isinstance(entity, str):
            raise ValueError("Entity-based collection expects a ResolvedEntity")

        if entity is None:
            raise ValueError("Entity is required")

        github_source = self._get_source(entity, "github")

        repository = None
        readme = None
        releases = None
        issues = None
        pull_requests = None
        commit_activity = None
        planning = None
        discussions = None
        ecosystem = None 

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
            ecosystem = self.github.get_ecosystem_signals(owner, repo)  # 新增

        evidence = self.builder.build(
            repository=repository,
            readme=readme,
            releases=releases,
            issues=issues,
            pull_requests=pull_requests,
            commit_activity=commit_activity,
            planning=planning,
            discussions=discussions,
            ecosystem=ecosystem,  
        )

        return evidence

    @staticmethod
    def _get_source(entity: ResolvedEntity, source_name: str):
        sources = getattr(entity, "sources", None)
        if sources:
            for source in sources:
                if source.source == source_name:
                    return source

        if source_name != "github":
            return None

        candidates = [
            getattr(entity, "official_name", None),
            getattr(entity, "name", None),
            *list(getattr(entity, "aliases", []) or []),
        ]
        for candidate in candidates:
            if isinstance(candidate, str) and "/" in candidate:
                return SimpleNamespace(source="github", identifier=candidate)
        return None

    @staticmethod
    def _split_github_identifier(identifier: str) -> tuple[str, str]:
        if "/" not in identifier:
            raise ValueError(f"Invalid GitHub identifier: {identifier}")
        return identifier.split("/", 1)
