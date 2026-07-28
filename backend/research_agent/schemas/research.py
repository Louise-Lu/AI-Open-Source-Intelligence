# Research schemas — AI Intelligence Research Agent
#
# 从 Workflow 升级为 Agent
# 核心理念：不输出固定 report 类型，Router 只理解用户研究目标
#
# ResearchIntent:
#   objective: information_lookup | evaluation | comparison | trend_analysis
#              | technology_research | market_research | decision_support
#              | greeting | small_talk | help
#   entities:  研究涉及的实体
#   focus:     用户真正关心的信息维度
#   time_range: latest | recent | historical | any
#   depth:     quick | standard | deep

from __future__ import annotations

from enum import Enum
from typing import Any, Literal

from pydantic import BaseModel, Field


# ═══════════════════════════════════════════════════════════════
# Research Intent — Router 的输出，不绑定任何 report 类型
# ═══════════════════════════════════════════════════════════════


class ResearchObjective(str, Enum):
    """研究目标类型 — Router 只负责理解用户想做什么"""

    # 研究类（需要进入 Research Pipeline）
    information_lookup = "information_lookup"    # 了解一个对象：X 是什么
    evaluation = "evaluation"                    # 评价一个项目：X 怎么样
    comparison = "comparison"                    # 两个或多个对象比较
    trend_analysis = "trend_analysis"            # 趋势分析：最近 X 有什么趋势？
    technology_research = "technology_research"  # 技术研究：某项技术的原理/架构
    market_research = "market_research"          # 市场研究：某个方向的机会
    decision_support = "decision_support"        # 推荐/选型/决策支持

    # 非研究类（chat only，不走 Research Pipeline）
    greeting = "greeting"                        # 问候：hello / hi / 你好
    small_talk = "small_talk"                    # 闲聊
    help = "help"                                # 求助/使用说明


class ResearchIntent(BaseModel):
    """深度理解用户的研究意图。

    与旧版的区别：
    - 不包含 information_needs（那是 Planner 的工作，不是 Router 的）
    - 不包含 sub_questions（那是 Planner 的工作，不是 Router 的）
    - 不包含 audience（由 Planner 根据 objective 推导）
    - objective 是枚举，不是自由文本 goal
    - 纯粹表达「用户想做什么 + 在什么上下文 + 关注什么时间 + 多深」
    """

    objective: Literal[
        "information_lookup",
        "evaluation",
        "comparison",
        "trend_analysis",
        "technology_research",
        "market_research",
        "decision_support",
        "greeting",
        "small_talk",
        "help",
    ] = Field(
        description="用户的研究目标类型"
    )
    entities: list[str] = Field(
        default_factory=list,
        description="用户明确或隐含提到的研究实体名称",
    )
    focus: list[
        Literal[
            "community",
            "release",
            "technology",
            "ecosystem",
            "activity",
            "performance",
            "architecture",
            "adoption",
            "sentiment",
            "risk",
            "opportunity",
            "market",
            "pricing",
            "benchmark",
            "documentation",
        ]
    ] = Field(
        default_factory=list,
        description="用户真正关心的信息维度，可多选，不代表任务",
    )
    time_range: Literal[
        "latest",
        "recent",
        "historical",
        "future",
        "any",
    ] = Field(
        default="any",
        description="时间范围: latest (最新), recent (最近几个月), historical (历史), future (未来), any (不限)",
    )
    depth: Literal[
        "quick",
        "standard",
        "deep",
    ] = Field(
        default="standard",
        description="研究深度: quick (快速概览), standard (标准分析), deep (深度研究)",
    )
    raw_query: str = Field(
        default="",
        description="用户原始查询文本（透传，供下游参考）",
    )


class ResearchGoal(BaseModel):
    """Planner 输出 — Goal 驱动的研究目标。

    与旧版的核心区别：
    - 删除 research_questions：不再把 Goal 拆成固定问题，Agent 自主探索
    - 删除 suggested_sources：Agent 自主决定使用哪些数据源
    - 新增 user_goal / context / success_criteria / constraints：
      告诉 Agent "要完成什么"而非"按什么步骤做"
    """

    objective: str = Field(
        description="研究目标类型，来自 IntentRouter，例如 evaluation / comparison / trend_analysis"
    )
    user_goal: str = Field(
        description="一句自然语言描述用户的研究目标，例如 '分析 AI Agent 最近的发展趋势'"
    )
    entities: list[str] = Field(
        default_factory=list,
        description="研究涉及的实体名称列表",
    )
    context: str = Field(
        default="",
        description="一句背景信息，例如 '用户希望了解近期 AI Agent 技术的发展方向'",
    )
    depth: Literal["quick", "standard", "deep"] = Field(
        default="standard",
        description="研究深度: quick (快速概览), standard (标准分析), deep (深度研究)",
    )
    success_criteria: list[str] = Field(
        default_factory=list,
        description="完成标准列表，告诉 Agent 什么时候算完成，例如 ['识别近期主要技术方向', '找到代表性项目']",
    )
    constraints: list[str] = Field(
        default_factory=list,
        description="研究约束，例如 ['优先官方来源', '不要猜测', '多个来源交叉验证']",
    )
    status: str = Field(
        default="ready",
        description="目标状态: ready | need_user_input | insufficient_information",
    )
    message: str = Field(
        default="",
        description="当 status != ready 时，向用户展示的解释信息",
    )


# ═══════════════════════════════════════════════════════════════
# Signal Extraction — Analyzer 的输出
# ═══════════════════════════════════════════════════════════════


class TechnologySignal(BaseModel):
    """技术维度信号"""

    maturity_score: float = Field(default=0.0, ge=0.0, le=1.0)
    activity_score: float = Field(default=0.0, ge=0.0, le=1.0)
    tech_stack: list[str] = Field(default_factory=list)
    stability: str = Field(default="unknown")
    summary: str = Field(default="")
    evidence_refs: list[str] = Field(default_factory=list)


class CommunitySignal(BaseModel):
    """社区维度信号"""

    health_score: float = Field(default=0.0, ge=0.0, le=1.0)
    responsiveness: str = Field(default="unknown")
    contributor_diversity: str = Field(default="unknown")
    community_size: str = Field(default="unknown")
    sentiment: str = Field(default="neutral")
    summary: str = Field(default="")
    evidence_refs: list[str] = Field(default_factory=list)


class EcosystemSignal_(BaseModel):
    """生态维度信号"""

    market_position: str = Field(default="unknown")
    dependency_risk: str = Field(default="low")
    competitor_landscape: list[dict[str, str]] = Field(default_factory=list)
    trending_direction: str = Field(default="stable")
    summary: str = Field(default="")
    evidence_refs: list[str] = Field(default_factory=list)


class RiskSignal(BaseModel):
    """风险维度信号"""

    items: list[dict[str, Any]] = Field(default_factory=list)
    overall_risk_level: str = Field(default="low")
    breaking_change_risk: str = Field(default="none")
    maintenance_risk: str = Field(default="low")
    license_risk: str = Field(default="low")
    summary: str = Field(default="")
    evidence_refs: list[str] = Field(default_factory=list)


class ExtractedSignals(BaseModel):
    """从多源证据中提取的结构化信号"""

    technology: TechnologySignal | None = None
    community: CommunitySignal | None = None
    ecosystem: EcosystemSignal_ | None = None
    risks: RiskSignal | None = None

    @property
    def has_any_signal(self) -> bool:
        return any([self.technology, self.community, self.ecosystem, self.risks])


# ═══════════════════════════════════════════════════════════════
# Research Brief — Composer 的最终输出
# ═══════════════════════════════════════════════════════════════


class ResearchBrief(BaseModel):
    """最终研究简报 — Agent 输出的完整研究成果"""

    summary: str = Field(description="一句话总结核心发现")
    key_findings: list[str] = Field(default_factory=list, description="关键发现列表")
    analysis: str = Field(default="", description="详细分析")
    signals: ExtractedSignals | None = Field(default=None, description="结构化信号")
    sources: list[str] = Field(default_factory=list, description="信息来源列表")
    recommendations: list[str] = Field(default_factory=list, description="行动建议")
