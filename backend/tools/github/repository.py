from __future__ import annotations

from typing import Any
from agent.trace import add_trace

class RepositoryTool:
    """
    获取 GitHub Repository 基础信息

    返回：
    - full_name
    - description
    - language
    - stars
    - forks
    - topics
    - license
    - created_at
    - updated_at
    """

    client: Any


    def get_repository(
        self,
        owner: str,
        repo: str
    ) -> dict[str, Any]:

        response = self.client.get(
            f"/repos/{owner}/{repo}"
        )

        data = response.json()

        license_info = data.get("license")

        result = {
            "full_name": data.get("full_name"),
            "description": data.get("description"),
            "language": data.get("language"),
            "stars": data.get("stargazers_count", 0),
            "forks": data.get("forks_count", 0),
            "topics": data.get("topics", []),
            "license": (
                license_info.get("name")
                if license_info
                else None
            ),
            "created_at": data.get("created_at"),
            "updated_at": data.get("updated_at"),
        }

        add_trace(
        tool_name="get_repository",
        tool_input={
            "owner": owner,
            "repo": repo
        },
        tool_output=result
    )

        return result