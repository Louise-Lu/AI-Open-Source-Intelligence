# GitHub 返回的 预处理后的 data -> Structured Evidence: 类型 IntelligenceEvidence

from __future__ import annotations

from typing import Any

from .models import (
    IntelligenceEvidence,
    GitHubEvidence,
    RedditEvidence,
    HuggingFaceEvidence,
    RepositoryInfo,
    ReleaseInfo,
    IssueInfo,
    PullRequestInfo,
    CommitActivity,
    PlanningSignal,
    DiscussionSignal,
    # ContributorInfo,
)

# 将原始数据（字典/列表）转换为 Pydantic 模型（如 GitHubEvidence、HuggingFaceEvidence）。
# 参数 GitHub 返回的 预处理后的 data : repository releases 等等... 
# return 结构化的evidence: 类型 IntelligenceEvidence

class EvidenceBuilder:
    """
    Raw Data
        |
        v
    Structured Evidence

    负责:
    
    1. 调整字段
    2. 清洗数据
    3. 类型转换
    4. 聚合
    """

    def build(
        self,
        repository: dict[str,Any] | None,
        readme: str | None,
        releases: dict[str,Any] | list[dict[str,Any]] | None = None,
        issues: dict[str,Any] | list[dict[str,Any]] | None = None,
        pull_requests: dict[str,Any] | list[dict[str,Any]] | None = None,
        commit_activity: dict[str, Any] | None = None,
        planning: dict[str, Any] | None = None,
        discussions: dict[str, Any] | None = None,

        huggingface: dict[str, Any] | None = None,
        reddit: dict[str, Any] | list[str] | None = None,   # 保留 reddit

    ) -> IntelligenceEvidence:

        github = GitHubEvidence(
            repository=self._build_repository(repository),
            readme=readme,
            releases=self._build_releases(releases),
            issues=self._build_issues(issues),
            pull_requests=self._build_pull_requests(pull_requests),

            commit_activity=self._build_commit_activity(commit_activity),
            planning=self._build_planning(planning),
            discussions=self._build_discussions(discussions),
        )
        huggingface_evidence = self._build_huggingface_evidence(huggingface)
        # reddit_evidence = self._build_reddit(reddit)  # 如果你有 _build_reddit 方法

        return IntelligenceEvidence(
            github=github,
            huggingface=huggingface_evidence,
        )

    def _build_huggingface_evidence(
        self,
        raw: dict[str, Any] | None,
    ) -> HuggingFaceEvidence | None:
        if not raw:
            return None

        return HuggingFaceEvidence(
            downloads=int(raw.get("downloads", 0) or 0),
            likes=int(raw.get("likes", 0) or 0),
            pipeline_tag=raw.get("pipeline_tag"),
            tags=[str(tag) for tag in raw.get("tags", []) or []],
            last_modified=raw.get("lastModified") or raw.get("last_modified"),
        )

    # def _build_reddit(self, reddit: dict[str, Any] | list[str] | None) -> RedditEvidence | None:
    #     if reddit is None:
    #         return None

    #     if isinstance(reddit, dict):
    #         posts = reddit.get("posts", [])
    #         sentiment = reddit.get("sentiment")
    #         mentions = int(reddit.get("mentions", len(posts)) or 0)
    #     else:
    #         posts = reddit
    #         sentiment = None
    #         mentions = len(posts)

    #     return RedditEvidence(
    #         posts=[str(post) for post in posts or []],
    #         sentiment=sentiment,
    #         mentions=mentions,
    #     )

    # =====================
    # GITHUB
    # =====================

    def _build_repository(
        self,
        data:dict[str,Any] | None
    ) -> RepositoryInfo | None:
        if not data:
            return None
        license_info=data.get(
            "license"
        )
        return RepositoryInfo(
            full_name=data.get(
                "full_name"
            ),
            description=data.get(
                "description"
            ),
            language=data.get(
                "language"
            ),
            stars=int(
                data.get(
                    "stars",
                    data.get(
                        "stargazers_count",
                        0
                    )
                )
                or 0
            ),
            forks=int(
                data.get(
                    "forks",
                    data.get(
                        "forks_count",
                        0
                    )
                )
                or 0
            ),
            topics=data.get(
                "topics",
                []
            ),


            license=
                license_info.get(
                    "name"
                )
                if isinstance(
                    license_info,
                    dict
                )
                else license_info,


            created_at=data.get(
                "created_at"
            ),


            updated_at=data.get(
                "updated_at"
            )

        )

    def _build_releases(
        self,
        releases
    ) -> list[ReleaseInfo]:


        if isinstance(
            releases,
            dict
        ):

            releases = (
                releases
                .get(
                    "recent_releases",
                    []
                )
            )


        return [

            ReleaseInfo(

                tag_name=r.get(
                    "tag_name"
                ),

                name=r.get(
                    "name"
                ),

                published_at=r.get(
                    "published_at"
                ),

                body=r.get(
                    "body"
                )

            )

            for r in releases or []

        ]

    def _build_issues(
        self,
        issues
    ) -> list[IssueInfo]:


        if isinstance(
            issues,
            dict
        ):

            issues=issues.get(
                "recent_issues",
                []
            )


        return [

            IssueInfo(

                title=i.get(
                    "title"
                ),

                state=i.get(
                    "state"
                ),

                created_at=i.get(
                    "created_at"
                ),

                comments=int(
                    i.get(
                        "comments",
                        0
                    )
                    or 0
                )

            )

            for i in issues or []

        ]

    def _build_pull_requests(
        self,
        prs
    ) -> list[PullRequestInfo]:


        if isinstance(
            prs,
            dict
        ):

            prs=prs.get(
                "recent_pull_requests",
                []
            )


        return [

            PullRequestInfo(

                title=p.get(
                    "title"
                ),

                state=p.get(
                    "state"
                ),

                created_at=p.get(
                    "created_at"
                ),

                merged=p.get(
                    "merged",
                    False
                )

            )

            for p in prs or []

        ]

    def _build_commit_activity(self, data: dict[str, Any] | None) -> CommitActivity | None:
        if not data:
            return None
        return CommitActivity(
            commits_last_30_days=data.get("commits_last_30_days", 0),
            commits_last_90_days=data.get("commits_last_90_days", 0),
            active_contributors_count=data.get("active_contributors_count", 0),
        )

    def _build_planning(self, data: dict[str, Any] | None) -> PlanningSignal | None:
        if not data:
            return None
        return PlanningSignal(
            roadmap_text=data.get("roadmap_text"),
            milestones=data.get("milestones", []),
            enhancement_issues=data.get("enhancement_issues", []),
        )

    def _build_discussions(self, data: dict[str, Any] | None) -> DiscussionSignal | None:
        if not data:
            return None
        hot_topics_raw = data.get("hot_topics", [])
        # 将 [{"title": ..., "has_official_answer": bool, "maintainer_involved": bool}] 
        # 转为简单的摘要字符串列表，方便 LLM 消费
        hot_topics_str = []
        for topic in hot_topics_raw:
            title = topic.get("title", "")
            tags = []
            if topic.get("has_official_answer"):
                tags.append("官方回答")
            if topic.get("maintainer_involved"):
                tags.append("维护者参与")
            tag_str = f"[{', '.join(tags)}]" if tags else ""
            hot_topics_str.append(f"{title} {tag_str}".strip())
        return DiscussionSignal(hot_topics=hot_topics_str)

