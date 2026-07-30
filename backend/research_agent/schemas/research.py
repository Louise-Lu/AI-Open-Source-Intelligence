# Research schemas 
#
# ResearchIntent:
#   objective: information_lookup | evaluation | comparison | trend_analysis
#              | technology_research | market_research | decision_support
#              | greeting | small_talk | help
#   entities:  研究涉及的实体
#   focus:     用户真正关心的信息维度
#   depth:     quick | standard | deep
#
# time_range 和 platform_hint 由正则从 raw_query 提取，不经过 LLM。

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
    """用户研究意图 — LLM 只负责理解，不负责推断执行策略。

    4 个字段：
    - objective: 用户想做什么（分类）
    - entities: 研究对象是谁（提取）
    - focus: 用户关心什么维度（语义理解）
    - depth: 需要多深（判断）

    time_range 和 platform_hint 由正则从 raw_query 提取，不经过 LLM。
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


class StopConditions(BaseModel):
    """停止条件 — 同时满足时 Agent 必须停止搜索。"""

    min_sources: int = Field(
        default=1,
        description="至少需要覆盖的不同证据来源数",
    )
    min_evidence_items: int = Field(
        default=2,
        description="至少需要收集的证据条目数",
    )


class ExecutionPlan(BaseModel):
    """统一执行计划：合并了研究上下文和执行控制。

    包含：
    - 来自 Intent 的研究目标信息（objective, entities, focus）
    - ContextBuilder 生成的执行参数（user_goal, mode, source_scope, …）
    - 预算和停止条件（max_tool_calls, stop_conditions 等）

    avoid_sources 用于主动排除明显无关的来源。
    community_platforms 由用户显式指定或根据 entity_origin 推断。
    """

    # ===== 来自 Intent =====
    objective: str = Field(
        default="information_lookup",
        description="研究目标，例如 evaluation、trend_analysis",
    )
    entities: list[str] = Field(
        default_factory=list,
        description="标准化后的研究对象",
    )
    focus: list[str] = Field(
        default_factory=list,
        description="用户关注的信息维度，例如 community、market、technology",
    )
    time_range: str = Field(
        default="any",
        description="时间范围，例如 recent、past_year、any",
    )

    # ===== ContextBuilder 生成 =====
    user_goal: str = Field(
        default="",
        description="一句话描述用户真正想解决的问题",
    )
    mode: Literal["quick", "standard", "deep"] = Field(
        default="standard",
        description="执行深度，决定工具预算大小",
    )
    source_scope: list[str] = Field(
        default_factory=list,
        description="允许使用的数据源，例如 community/web/github",
    )
    avoid_sources: list[str] = Field(
        default_factory=list,
        description="本任务应避免使用的数据源（仅用于明显无关来源）",
    )
    required_evidence: list[str] = Field(
        default_factory=list,
        description="达到停止条件必须覆盖的证据来源类型",
    )
    community_platforms: list[str] = Field(
        default_factory=list,
        description="社区搜索目标平台，由用户显式指定或根据 entity_origin 推断",
    )

    # ===== 预算 =====
    max_tool_calls: int = Field(
        default=8,
        description="本次研究最多允许的工具调用次数",
    )
    max_discovery_per_source: int = Field(
        default=2,
        description="每个来源最多允许的 Discovery 调用次数（含空结果）",
    )
    max_empty_retry_per_source: int = Field(
        default=1,
        description="每个来源 Discovery 返回空结果后允许重试的次数",
    )
    max_reader_per_source: int = Field(
        default=2,
        description="每个来源最多允许的 Evidence Reader 调用次数",
    )
    max_evidence_items: int = Field(
        default=10,
        description="本次研究最多收集的证据条目总数上限",
    )
    min_evidence_items: int = Field(
        default=2,
        description="停止前至少需要收集的证据条目数",
    )

    # ===== 停止条件 =====
    stop_conditions: StopConditions = Field(
        default_factory=StopConditions,
        description="结构化停止条件：min_sources + min_evidence_items 同时满足时停止",
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
