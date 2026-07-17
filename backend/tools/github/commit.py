from __future__ import annotations

from typing import Any
from datetime import datetime, timedelta, timezone
from agent.trace import add_trace


class CommitActivityTool:
    """
    获取仓库提交活跃度
    若需要同时提供 30 天和 90 天，可在外层分别调用此方法两次，或扩展此方法

    返回：
    - commits_last_30_days: int
    - commits_last_90_days: int
    - active_contributors_count: int
    """

    client: Any

    def get_commit_activity(
        self,
        owner: str,
        repo: str,
        days: int = 30
    ) -> dict[str, Any]: ## {"a":xxx,...}
        """
        拉取指定天数内的提交，并统计活跃贡献者。
        默认 30 天。
        """
        now = datetime.now(timezone.utc)
        since = (now - timedelta(days=days)).isoformat()
        until = now.isoformat()

        all_commits = []
        page = 1
        per_page = 100

        # 分页抓取所有提交（GitHub 最多返回 1000 条，实际项目 30 天内一般不会超）
        while True:
            response = self.client.get(
                f"/repos/{owner}/{repo}/commits",
                params={
                    "since": since,
                    "until": until,
                    "per_page": per_page,
                    "page": page,
                },
            )
            data = response.json()
            if not data or not isinstance(data, list):
                break
            all_commits.extend(data)
            if len(data) < per_page:
                break
            page += 1

        # 统计提交次数
        commits_count = len(all_commits)

        # 去重统计活跃贡献者
        contributors = set()
        for commit in all_commits:
            author = commit.get("author")
            if author and author.get("login"):
                contributors.add(author["login"])
            else:
                # 有时候 commit.author 为 null，回退到 commit.commit.author.name
                committer = commit.get("commit", {}).get("author", {}).get("name")
                if committer:
                    contributors.add(committer)

        result = {
            "commits_last_30_days": commits_count if days == 30 else 0,
            "commits_last_90_days": commits_count if days == 90 else 0,
            "active_contributors_count": len(contributors),
        }

        add_trace(
            tool_name="get_commit_activity",
            tool_input={
                "owner": owner,
                "repo": repo,
                "days": days,
                "since": since,
                "until": until,
            },
            tool_output=result,
        )

        return result