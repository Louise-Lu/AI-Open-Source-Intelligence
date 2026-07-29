# Research schemas 
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
    - 纯粹表达「用户想做什么 + 什么信息维度 + 关注什么时间 + 多深」
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
            "developer",
            "official",
            "technology",
            "ecosystem",
            "adoption",
            "sentiment",
            "trend",
            "benchmark",
            "market",
            "opportunity",
            "risk",
            "recent_updates",
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


class ResearchContext(BaseModel):
    """
    提供给 ReAct Agent 的研究上下文。
    描述"用户真正想解决的问题"，而不是告诉 Agent 怎么做。
    """

    # ===== 来自 Intent =====

    objective: str = Field(
        description="研究目标，例如 evaluation、trend_analysis"
    )

    entities: list[str] = Field(
        default_factory=list,
        description="标准化后的研究对象"
    )

    focus: list[str] = Field(
        default_factory=list,
        description="用户关注的信息维度，例如 community、market、technology"
    )

    time_range: str = Field(
        default="any",
        description="时间范围，例如 recent、past_year、any"
    )

    depth: str = Field(
        default="standard",
        description="研究深度：quick / standard / deep"
    )

    # ===== Context Builder 生成 =====

    user_goal: str = Field(
        description="一句话描述用户真正想解决的问题"
    )

    research_brief: str = Field(
        description="给 Agent 的研究说明，解释研究重点和背景"
    )

    success_criteria: list[str] = Field(
        default_factory=list,
        description="什么情况下认为研究已经完成"
    )

    constraints: list[str] = Field(
        default_factory=list,
        description="研究限制，例如不要编造数据、优先官方来源"
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
