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
        owner: str,
        repo: str
    ) -> list[dict[str, Any]]:


        response = self.client.get(
            f"/repos/{owner}/{repo}/issues"
        )


        issues = response.json()


        formatted = []


        for issue in issues:

            # GitHub issues API 会返回 PR
            # 排除 PR

            if "pull_request" in issue:
                continue


            formatted.append(
                {
                    "title": issue.get("title"),

                    "state": issue.get("state"),

                    "created_at": issue.get("created_at"),

                    "comments": int(
                        issue.get("comments") or 0
                    )
                }
            )


            if len(formatted) >= 5:
                break


        return formatted