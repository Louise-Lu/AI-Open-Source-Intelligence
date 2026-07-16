from __future__ import annotations


from typing import Any


from .models import (

    IntelligenceEvidence,

    GitHubEvidence,

    RepositoryInfo,

    ReleaseInfo,

    IssueInfo,

    PullRequestInfo,

    # ContributorInfo,

)



class EvidenceBuilder:
    """
    Raw Data
        |
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

        # contributors: list[dict[str,Any]] | None = None,


    ) -> IntelligenceEvidence:



        github = GitHubEvidence(


            repository=
                self._build_repository(repository),


            readme=readme,


            releases=
                self._build_releases(releases),


            issues=
                self._build_issues(issues),


            pull_requests=
                self._build_pull_requests(
                    pull_requests
                ),


            # contributors=
            #     self._build_contributors(
            #         contributors
            #     )

        )


        return IntelligenceEvidence(

            github=github

        )



    # =====================
    # Repository
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



    # =====================
    # Release
    # =====================


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



    # =====================
    # Issue
    # =====================


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



    # =====================
    # PR
    # =====================


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



    # =====================
    # Contributor
    # =====================


    # def _build_contributors(
    #     self,
    #     contributors
    # ) -> list[ContributorInfo]:


    #     return [

    #         ContributorInfo(

    #             login=c.get(
    #                 "login"
    #             ),

    #             contributions=c.get(
    #                 "contributions",
    #                 0
    #             )

    #         )

    #         for c in contributors or []

    #     ]

# from __future__ import annotations

# from typing import Any

# from .models import (
#     GitHubEvidence,
#     IssueInfo,
#     PullRequestInfo,
#     ReleaseInfo,
#     RepositoryInfo,
# )
# # Builder 只负责：① 调 Tool ② 清洗 ③ 聚合 ④ 给 llm
# # 数据整理 
# class EvidenceBuilder:
#     """Aggregate and normalize GitHub tool outputs into structured evidence."""
#     # 接收 仓的 各种源信息 -> 返回 实例化的一个对象：固定格式的佐证github的证据信息
#     def build(
#         self,
#         repository: dict[str, Any] | None,
#         readme: str | None,
#         releases: list[dict[str, Any]] | None = None,
#         issues: list[dict[str, Any]] | None = None,
#         pull_requests: list[dict[str, Any]] | None = None,
#     ) -> GitHubEvidence:
#         """Convert raw GitHub payloads into a unified evidence object."""
#         return GitHubEvidence(
#             repository=self._build_repository(repository),
#             readme=readme,
#             releases=[self._build_release(release) for release in releases or []],
#             issues=[self._build_issue(issue) for issue in issues or []],
#             pull_requests=[
#                 self._build_pull_request(pull_request)
#                 for pull_request in pull_requests or []
#             ],
#         )

#     def _build_repository(
#         self,
#         repository: dict[str, Any] | None
#     ) -> RepositoryInfo | None:

#         if not repository:
#             return None

#         return RepositoryInfo(

#             full_name=repository.get("full_name"),

#             description=repository.get("description"),

#             language=repository.get("language"),

#             stars=int(repository.get("stars") or 0),

#             forks=int(repository.get("forks") or 0),

#             topics=repository.get("topics", []),

#             license=repository.get("license"),

#             created_at=repository.get("created_at"),

#             updated_at=repository.get("updated_at"),
#         )


#     def _build_release(
#         self,
#         release: dict[str, Any]
#     ) -> ReleaseInfo:

#         return ReleaseInfo(

#             tag_name=release.get("tag_name"),

#             name=release.get("name"),

#             published_at=release.get("published_at"),

#             body=release.get("body"),
#     )

#     def _build_issue(
#         self,
#         issue: dict[str, Any]
#     ) -> IssueInfo:

#         labels=[]

#         for label in issue.get("labels", []):
#             if isinstance(label, dict):
#                 labels.append(
#                     label.get("name")
#                 )


#         return IssueInfo(
#             title=issue.get("title"),
#             state=issue.get("state"),
#             created_at=issue.get("created_at"),
#             comments=int(issue.get("comments") or 0),
#             labels=labels
#     )

#     def _build_pull_request(
#     self,
#     pull_request: dict[str, Any]
#     ) -> PullRequestInfo:

#         return PullRequestInfo(

#             title=pull_request.get("title"),

#             state=pull_request.get("state"),

#             created_at=pull_request.get("created_at"),

#             merged=pull_request.get("merged", False)

#         )


# #   GitHub API JSON
# #         |
# #         v
# #   EvidenceBuilder
# #         |
# #         v
# # Pydantic Evidence Model
# #         |
# #         v
# #        LLM


