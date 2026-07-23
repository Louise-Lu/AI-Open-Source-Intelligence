from __future__ import annotations

from schemas.entity import ResolvedEntity
from evidence import EvidenceBuilder
from sources.github.client import GitHubAPI
from sources.huggingface.client import HuggingFaceClient
from sources.reddit.client import RedditClient
from services.evidence_planner import EvidencePlanner


class RepositoryEvidenceService:
    def __init__(self):
        self.github = GitHubAPI()
        self.huggingface = HuggingFaceClient()
        self.reddit = RedditClient()
        self.builder = EvidenceBuilder()
        self.planner = EvidencePlanner()

    def collect(
        self,
        entity: ResolvedEntity | str | None = None,
        owner: str | None = None,
        repo: str | None = None,
        huggingface_model_id: str | None = None,
        include_reddit: bool = False,
    ):
        if isinstance(entity, str):
            raise ValueError("Entity-based collection expects a ResolvedEntity")

        if entity is None:
            raise ValueError("Entity is required")

        plan = self.planner.plan(entity, include_reddit=include_reddit)
        github_source = self._get_source(entity, "github")
        print("evidence_from_git",github_source)
        huggingface_source = self._get_source(entity, "huggingface")
        print("evidence_from_hf",huggingface_source)

        repository = None
        readme = None
        releases = None
        issues = None
        pull_requests = None
        commit_activity = None
        planning = None
        discussions = None
        reddit = None
        huggingface = None

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

        if include_reddit and github_source:
            try:
                owner, repo = self._split_github_identifier(github_source.identifier)
                query = repository.get("full_name") or f"{owner}/{repo}"
                posts = self.reddit.search_posts(query=query, limit=5)
                reddit = {
                    "posts": posts,
                    "mentions": len(posts),
                    "sentiment": None,
                }
            except Exception as exc:
                print(f"Reddit collection failed: {exc}")
                reddit = {
                    "posts": [],
                    "mentions": 0,
                    "sentiment": None,
                }

        if huggingface_source:
            try:
                print("hf_link",huggingface_source.identifier)
                huggingface = self.huggingface.get_model(huggingface_source.identifier)
                print("hf_response",huggingface)
            except Exception as exc:
                print(f"HuggingFace collection failed: {exc}")
                huggingface = None

        evidence = self.builder.build(
            repository=repository,
            readme=readme,
            releases=releases,
            issues=issues,
            pull_requests=pull_requests,
            reddit=reddit,
            huggingface=huggingface,
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
