from __future__ import annotations

from pydantic import BaseModel, Field


# =========================
# GitHub Raw Evidence Models
# =========================


class RepositoryInfo(BaseModel):
    """
    Repository 基础信息
    """

    full_name: str | None = None

    description: str | None = None

    language: str | None = None

    stars: int = 0

    forks: int = 0

    topics: list[str] = Field(
        default_factory=list
    )

    license: str | None = None

    created_at: str | None = None

    updated_at: str | None = None



class ReleaseInfo(BaseModel):
    """
    Release 信息
    """

    tag_name: str | None = None

    name: str | None = None

    published_at: str | None = None

    body: str | None = None



class IssueInfo(BaseModel):

    title: str | None = None

    state: str | None = None

    created_at: str | None = None

    comments: int = 0



class PullRequestInfo(BaseModel):

    title: str | None = None

    state: str | None = None

    created_at: str | None = None

    merged: bool = False



# class ContributorInfo(BaseModel):

#     login: str | None = None

#     contributions: int = 0



# =========================
# GitHub Evidence
# =========================


class GitHubEvidence(BaseModel):
    """
    GitHub 数据证据层

    不包含分析结果
    只保存事实
    """


    repository: RepositoryInfo | None = None


    readme: str | None = None


    releases: list[ReleaseInfo] = Field(
        default_factory=list
    )


    issues: list[IssueInfo] = Field(
        default_factory=list
    )


    pull_requests: list[PullRequestInfo] = Field(
        default_factory=list
    )


    # contributors: list[ContributorInfo] = Field(
    #     default_factory=list
    # )



# =========================
# Future Data Sources
# =========================


class RedditEvidence(BaseModel):
    """
    Reddit 社区信息
    """

    posts: list[str] = Field(
        default_factory=list
    )


    sentiment: str | None = None



class HuggingFaceEvidence(BaseModel):

    downloads: int = 0

    likes: int = 0



# =========================
# Unified Evidence
# =========================


class IntelligenceEvidence(BaseModel):
    """
    AI Open Source Intelligence 总证据层

    所有分析服务共享
    """

    github: GitHubEvidence | None = None


    reddit: RedditEvidence | None = None


    huggingface: HuggingFaceEvidence | None = None