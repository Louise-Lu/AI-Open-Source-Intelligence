from __future__ import annotations

from typing import Any


class RepositoryTool:
    """Repository metadata helper 元数据 
    名称 所有者 描述 星级 分支 语言 主题 许可证 主页 创建时间 更新时间."""

    client: Any

    def get_repository(self, owner: str, repo: str) -> dict[str, Any]:
        # 仓库元数据是用户界面（UI）所使用的主要摘要视图
        response = self.client.get(f"/repos/{owner}/{repo}")
        return response.json()

