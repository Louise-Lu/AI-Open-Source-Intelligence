from __future__ import annotations

from typing import Any

class IssueTool:

    """
    获取 GitHub Issue 信息

    用于：
    - 社区反馈
    - 项目维护情况
    """


    client: Any


    def get_issues(
        self,
        owner:str,
        repo:str
    ) -> dict[str,Any]:


        response = self.client.get(
            f"/repos/{owner}/{repo}/issues"
        )


        issues=response.json()


        formatted=[]


        for issue in issues[:5]:

            # GitHub API 会把 PR 也返回
            # 排除 pull request

            if "pull_request" in issue:
                continue


            formatted.append(
                {
                    "title":
                        issue.get("title"),

                    "state":
                        issue.get("state"),

                    "created_at":
                        issue.get("created_at"),

                    "comments":
                        issue.get("comments")
                }
            )


        open_count=len(
            [
                i for i in issues
                if i.get("state")=="open"
                and "pull_request" not in i
            ]
        )


        return {

            "open_issue_count":
                open_count,


            "recent_issues":
                formatted

        }