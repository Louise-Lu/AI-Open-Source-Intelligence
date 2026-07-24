from __future__ import annotations

from typing import Any

# 字段	示例值	用途
# dependencies	['openai', 'pydantic', 'chromadb', ...]	分析项目技术栈和集成方向
# dependents_count	0	下游依赖量（API 已废弃，可忽略）
# awesome_list_mentions	False	社区认可度信号
# competitors	['AutoGPT', 'MetaGPT']	竞品分析

class EcosystemSignalTool:
    """
    获取项目的生态信号

    返回：
    - dependencies: list[str]       # 直接依赖的包名（从 SBOM 解析）
    - dependents_count: int         # 下游依赖数量（暂不可用，返回 0）
    - awesome_list_mentions: bool   # 是否被 awesome 列表收录（基于 topics 判断）
    - competitors: list[str]        # 直接竞品列表
    """

    client: Any
    competitor_map: dict[str, list[str]]

    def __init__(self, client: Any, competitor_map: dict[str, list[str]] | None = None):
        self.client = client
        self.competitor_map = competitor_map or {}

    def get_ecosystem_signals(self, owner: str, repo: str) -> dict[str, Any]:
        """
        获取 owner/repo 的生态信号
        """
        dependencies_set: set[str] = set()
        dependents_count: int = 0
        awesome_list_mentions: bool = False
        competitors: list[str] = []

        # 1. SBOM 解析 - 提取 PyPI 依赖
        try:
            sbom_resp = self.client.get(
                f"/repos/{owner}/{repo}/dependency-graph/sbom",
                headers={"Accept": "application/vnd.github.spdx+json"},
            )
            if sbom_resp.status_code == 200:
                sbom_data = sbom_resp.json()
                sbom = sbom_data.get("sbom", sbom_data)
                
                packages = sbom.get("packages", [])
                for pkg in packages:
                    name = pkg.get("name", "")
                    
                    # 跳过空名和 SPDX 引用
                    if not name or name.startswith("SPDXRef-"):
                        continue
                    
                    # 跳过 GitHub Actions（路径格式如 actions/checkout）
                    if "/" in name:
                        continue
                    
                    # 去掉版本号
                    if "@" in name:
                        name = name.split("@")[0]
                    
                    clean_name = name.strip().lower()
                    if clean_name:
                        dependencies_set.add(clean_name)
        except Exception:
            pass

        # 2. dependents
        try:
            deps_resp = self.client.get(
                f"/repos/{owner}/{repo}/dependency-graph/dependents",
                headers={"Accept": "application/vnd.github.hawkgirl-preview+json"},
            )
            if deps_resp.status_code == 200:
                data = deps_resp.json()
                dependents_count = data.get("total_count", 0)
        except Exception:
            pass

        # 3. awesome
        try:
            repo_info = self.client.get(f"/repos/{owner}/{repo}")
            if repo_info.status_code == 200:
                topics = repo_info.json().get("topics", [])
                if any("awesome" in topic.lower() for topic in topics):
                    awesome_list_mentions = True
        except Exception:
            pass

        # 4. 竞品
        full_name = f"{owner}/{repo}"
        competitors = self.competitor_map.get(full_name, [])

        return {
            "dependencies": sorted(list(dependencies_set)),
            "dependents_count": dependents_count,
            "awesome_list_mentions": awesome_list_mentions,
            "competitors": competitors,
        }