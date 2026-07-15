from __future__ import annotations

from typing import Any
from agent.trace import add_trace

class ReleaseTool:
    """
    获取 GitHub Release 信息

    返回：
    - 最新版本
    - 最近版本列表
    """

    client: Any


    def get_releases(
        self,
        owner: str,
        repo: str
    ) -> list[dict[str, Any]]:


        response = self.client.get(
            f"/repos/{owner}/{repo}/releases"
        )


        releases = response.json()


        formatted = []

        for release in releases[:5]:

            formatted.append(
                {
                    "tag_name": release.get("tag_name"),
                    "name": release.get("name"),
                    "published_at": release.get("published_at"),
                    "body": release.get("body"),
                }
            )

        add_trace(
                "get_releases",
                {
                "owner":owner,
                "repo":repo
                },
                formatted
            )
        
        return formatted