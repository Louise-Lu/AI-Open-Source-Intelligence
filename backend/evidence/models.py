from __future__ import annotations

from pydantic import BaseModel, Field

# 创建Pydantic类 
# 定义数据格式type -> 数据验证功能
class RepositoryInfo(BaseModel):
    """Normalized GitHub repository metadata."""

    full_name: str | None = None
    description: str | None = None
    language: str | None = None
    stars: int = 0
    forks: int = 0
    topics: list[str] = Field(default_factory=list)
    license: str | None = None


class ReleaseInfo(BaseModel):
    """Normalized GitHub release metadata."""

    tag_name: str | None = None
    published_at: str | None = None
    body: str | None = None


class IssueInfo(BaseModel):
    """Normalized GitHub issue metadata."""

    title: str | None = None
    state: str | None = None
    created_at: str | None = None
    comments: int = 0


class PullRequestInfo(BaseModel):
    """Normalized GitHub pull request metadata."""

    title: str | None = None
    state: str | None = None
    created_at: str | None = None

# 来自github的证据支持
class GitHubEvidence(BaseModel):
    """由下游层处理的结构化证据包"""

    repository: RepositoryInfo | None = None
    readme: str | None = None
    releases: list[ReleaseInfo] = Field(default_factory=list)
    issues: list[IssueInfo] = Field(default_factory=list)
    pull_requests: list[PullRequestInfo] = Field(default_factory=list)
