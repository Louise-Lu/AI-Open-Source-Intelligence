from __future__ import annotations

from typing import Any
from agent.trace import add_trace

class PullRequestTool:

    """
    获取 GitHub Pull Request 信息

    用于：
    - 开发活跃度
    - 最近代码变化
    """


    client: Any


    def get_pull_requests(
        self,
        owner: str,
        repo: str
    ) -> list[dict[str, Any]]:


        response = self.client.get(
            f"/repos/{owner}/{repo}/pulls"
        )

        prs = response.json()

        formatted = []

        for pr in prs[:5]:

            formatted.append(
                {
                    "title": pr.get("title"),

                    "state": pr.get("state"),

                    "created_at": pr.get("created_at"),

                    "merged": pr.get("merged_at") is not None
                }
            )

        
        # add_trace(
        # "get_pull_requests",
        #         {
        #         "owner":owner,
        #         "repo":repo
        #         },
        #         formatted
        #     )
        
        return formatted