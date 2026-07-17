from __future__ import annotations

from typing import Any
from datetime import datetime, timedelta, timezone
from agent.trace import add_trace


class CommitActivityTool:
    """
    获取仓库提交活跃度

    返回：
    - commits_last_30_days: int
    - commits_last_90_days: int
    - active_contributors_count: int (90天内去重)
    """

    client: Any

    def get_commit_activity(
        self,
        owner: str,
        repo: str,
    ) -> dict[str, Any]:
        """
        一次拉取近 90 天的所有提交，然后分别统计 30 天和 90 天。
        """
        now = datetime.now(timezone.utc)
        since_90d = (now - timedelta(days=90)).isoformat()
        until = now.isoformat()

        all_commits = []
        page = 1
        per_page = 100

        while True:
            response = self.client.get(
                f"/repos/{owner}/{repo}/commits",
                params={
                    "since": since_90d,
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

        # 统计 90 天总提交数
        commits_90d = len(all_commits)

        # 统计 30 天提交数：筛选 committer date 在近 30 天内的
        cutoff_30d = now - timedelta(days=30)
        commits_30d = 0
        contributors = set()

        for commit in all_commits:
            # 提取作者
            author = commit.get("author")
            if author and author.get("login"):
                contributors.add(author["login"])
            else:
                # 回退到 commit.committer.name
                committer = commit.get("commit", {}).get("committer", {}).get("name")
                if committer:
                    contributors.add(committer)

            # 判断是否在 30 天内
            commit_date_str = commit.get("commit", {}).get("committer", {}).get("date")
            if commit_date_str:
                commit_date = datetime.fromisoformat(commit_date_str.replace("Z", "+00:00"))
                if commit_date >= cutoff_30d:
                    commits_30d += 1

        result = {
            "commits_last_30_days": commits_30d,
            "commits_last_90_days": commits_90d,
            "active_contributors_count": len(contributors),
        }

        add_trace(
            tool_name="get_commit_activity",
            tool_input={
                "owner": owner,
                "repo": repo,
                "since_90d": since_90d,
                "until": until,
            },
            tool_output=result,
        )

        return result