from __future__ import annotations

from typing import Any

from .models import (
    GitHubEvidence,
    IssueInfo,
    PullRequestInfo,
    ReleaseInfo,
    RepositoryInfo,
)
# Builder 只负责：① 调 Tool ② 清洗 ③ 聚合 ④ 给 Agent 
# 数据整理 
class EvidenceBuilder:
    """Aggregate and normalize GitHub tool outputs into structured evidence."""
    # 接收 仓的 各种源信息 -> 返回 实例化的一个对象：固定格式的佐证github的证据信息
    def build(
        self,
        repository: dict[str, Any] | None,
        readme: str | None,
        releases: list[dict[str, Any]] | None = None,
        issues: list[dict[str, Any]] | None = None,
        pull_requests: list[dict[str, Any]] | None = None,
    ) -> GitHubEvidence:
        """Convert raw GitHub payloads into a unified evidence object."""
        return GitHubEvidence(
            repository=self._build_repository(repository),
            readme=readme,
            releases=[self._build_release(release) for release in releases or []],
            issues=[self._build_issue(issue) for issue in issues or []],
            pull_requests=[
                self._build_pull_request(pull_request)
                for pull_request in pull_requests or []
            ],
        )

    def _build_repository(
        self, repository: dict[str, Any] | None
    ) -> RepositoryInfo | None:
        if not repository:
            return None

        license_info = repository.get("license")
        topics = self._normalize_topics(repository.get("topics"))

        return RepositoryInfo(
            full_name=repository.get("full_name"),
            description=repository.get("description"),
            language=repository.get("language"),
            stars=int(repository.get("stargazers_count") or 0),
            forks=int(repository.get("forks_count") or 0),
            topics=topics,
            license=license_info.get("name") if isinstance(license_info, dict) else None,
        )

    def _build_release(self, release: dict[str, Any]) -> ReleaseInfo:
        return ReleaseInfo(
            tag_name=release.get("tag_name"),
            published_at=release.get("published_at"),
            body=release.get("body"),
        )

    def _build_issue(self, issue: dict[str, Any]) -> IssueInfo:
        return IssueInfo(
            title=issue.get("title"),
            state=issue.get("state"),
            created_at=issue.get("created_at"),
            comments=int(issue.get("comments") or 0),
        )

    def _build_pull_request(self, pull_request: dict[str, Any]) -> PullRequestInfo:
        return PullRequestInfo(
            title=pull_request.get("title"),
            state=pull_request.get("state"),
            created_at=pull_request.get("created_at"),
        )

    def _normalize_topics(self, topics: Any) -> list[str]:
        if isinstance(topics, list):
            return [topic for topic in topics if isinstance(topic, str)]
        return []
