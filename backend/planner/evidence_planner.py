# 根据 Report 类型 + Entity Source实体来源，生成需要的工具列表（EvidencePlan）。

from __future__ import annotations

from dataclasses import dataclass, field
from schemas.entity import ResolvedEntity


@dataclass
class EvidencePlan:
    required_tools: list[str] = field(default_factory=list)
    
class EvidencePlanner:
    """
    根据 Report 类型 + Entity Source
    决定需要收集哪些 Evidence。

    不负责：
    - 判断用户意图
    - 解析实体
    - 调用工具

    只负责：
    Report -> Tools
    """

    REPORT_TOOL_MAP = {

        # 项目基本信息
        "profile": [
            "github_repository",
            "github_readme",
            "huggingface_model",
        ],


        # 项目健康度
        "health": [
            "github_issue",
            "github_pull_request",
            "github_release",
            "github_commit_activity",
        ],


        # 技术路线预测
        "roadmap": [
            "github_release",
            "github_pull_request",
            "github_commit_activity",
            "github_issue",
        ],


        # 最近版本变化
        "release_diff": [
            "github_release",
            "github_pull_request",
            "github_commit_activity",
        ],


        # 项目比较
        "comparison": [
            "github_repository",
            "github_readme",
            "github_release",
            "huggingface_model",
        ],


        # 推荐
        "recommendation": [
            "github_repository",
            "github_readme",
            "github_release",
            "github_issue",
            "github_pull_request",
            "huggingface_model",
        ],


        # 市场趋势（未来）
        "trend_report": [
            "github_trending",
            "huggingface_trending",
            "reddit_search",
        ]
    }

# - profile
# - project_health
# - analysis 少了
# - roadmap
# - comparison
# - recommendation
# - release_diff
# trend_report多

    def plan(
        self,
        entities: list[ResolvedEntity],   # 改为接受列表
        reports: list[str],
        include_reddit: bool = False,
    ) -> EvidencePlan:
        if not entities:
            # 没有实体时，返回空计划（或根据需求抛出异常）
            return EvidencePlan(required_tools=[])

        # 1. 根据 report 获取所有潜在需要的工具
        tools: set[str] = set()
        for report in reports:
            required = self.REPORT_TOOL_MAP.get(report, [])
            tools.update(required)

        # 2. 收集所有实体的来源类型（并集）
        available_sources = set()
        for entity in entities:
            for src in entity.sources:
                available_sources.add(src.source)

        # 3. 根据可用来源过滤工具
        final_tools = []
        for tool in tools:
            if tool.startswith("github") and "github" in available_sources:
                final_tools.append(tool)
            elif tool.startswith("huggingface") and "huggingface" in available_sources:
                final_tools.append(tool)
            elif tool.startswith("reddit") and include_reddit:
                final_tools.append(tool)
            else:
                # 对其他未知工具，默认保留（或根据需求处理）
                final_tools.append(tool)

        return EvidencePlan(required_tools=sorted(final_tools))