from __future__ import annotations

from typing import Any
import base64
from agent.trace import add_trace


class PlanningTool:
    """
    获取仓库未来规划相关信号

    返回：
    - roadmap_text: str | None
    - milestones: list[dict]   # title, due_on, progress_percent
    - enhancement_issues: list[str]
    """

    client: Any

    def get_planning_signals(
        self,
        owner: str,
        repo: str
    ) -> dict[str, Any]:
        # 1. 尝试获取 ROADMAP.md
        roadmap_text = None
        try:
            resp = self.client.get(
                f"/repos/{owner}/{repo}/contents/ROADMAP.md"
            )
            if resp.status_code == 200:
                content = resp.json().get("content")
                if content:
                    # 移除换行符后解码
                    roadmap_text = base64.b64decode(
                        content.replace("\n", "")
                    ).decode("utf-8")
        except Exception:
            roadmap_text = None

        # 2. 获取开放里程碑
        milestones = []
        try:
            resp = self.client.get(
                f"/repos/{owner}/{repo}/milestones",
                params={"state": "open", "per_page": 5},
            )
            if resp.status_code == 200:
                for m in resp.json():
                    open_issues = m.get("open_issues", 0)
                    closed_issues = m.get("closed_issues", 0)
                    total = open_issues + closed_issues
                    progress = round(closed_issues / total * 100, 1) if total > 0 else 0
                    milestones.append(
                        {
                            "title": m.get("title"),
                            "due_on": m.get("due_on"),
                            "progress_percent": progress,
                        }
                    )
        except Exception:
            pass

        # 3. 获取带 enhancement / proposal / planned 标签的 issue 标题
        enhancement_issues = []
        try:
            resp = self.client.get(
                f"/repos/{owner}/{repo}/issues",
                params={
                    "labels": "enhancement,proposal,planned",
                    "state": "open",
                    "per_page": 10,
                },
            )
            if resp.status_code == 200:
                for issue in resp.json():
                    # 排除 PR
                    if "pull_request" not in issue:
                        enhancement_issues.append(issue.get("title", ""))
        except Exception:
            pass

        result = {
            "roadmap_text": roadmap_text,
            "milestones": milestones,
            "enhancement_issues": enhancement_issues,
        }

        add_trace(
            tool_name="get_planning_signals",
            tool_input={
                "owner": owner,
                "repo": repo,
            },
            tool_output=result,
        )

        return result