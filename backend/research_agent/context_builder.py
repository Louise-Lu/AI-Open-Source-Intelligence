# context_builder.py — Research Context Assembler
#
# 职责: 根据 ResearchIntent + Entity 构建 ResearchContext
# 输入: ResearchIntent + list[ResolvedEntity]
# 输出: 
# ResearchContextBuilder 只做确定性组装，并用稳定规则生成 execution_plan。
# execution_plan 只描述来源范围、预算和停止条件，不生成具体工具步骤。

from __future__ import annotations

from research_agent.schemas.research import ExecutionPlan, ResearchContext, ResearchIntent
from shared_schemas.entity import ResolvedEntity


TOOLS_BY_SOURCE: dict[str, list[str]] = {
    "github": [
        "github_search",
        "github_project_profile",
        "github_project_health",
        "github_release_summary",
        "github_ecosystem",
    ],
    "huggingface": [
        "huggingface_search",
        "huggingface_model_profile",
    ],
    "community": [
        "community_search",
        "community_reader",
    ],
    "web": [
        "web_search",
        "webpage_reader",
    ],
    "youtube": [
        "youtube_search",
        "youtube_transcript",
        "podcast_transcript",
    ],
}


class ResearchContextBuilder:
    """根据 ResearchIntent + Entity 构建 ResearchContext。

    这里不再调用 LLM，只把 Intent、ResolvedEntity 和 ExecutionPlan 组装成运行上下文。
    """

    def build(
        self,
        intent: ResearchIntent,
        entities: list[ResolvedEntity],
    ) -> ResearchContext | None:
        """构建研究上下文。

        如果 entities 为空，返回 None，由调用方处理 need_user_input。
        """
        # Entity Guard: 没有解析到实体时不构建研究上下文
        if not entities:
            return None

        return self._build_context(intent, entities)

    def _build_context(
        self,
        intent: ResearchIntent,
        entities: list[ResolvedEntity],
    ) -> ResearchContext:
        """根据 intent 和实体确定性生成运行上下文。"""
        entity_names = [e.name for e in entities] or intent.entities
        entity_label = "、".join(entity_names or ["目标对象"])

        user_goals = {
            "trend_analysis": f"分析 {entity_label} 最近的发展趋势",
            "evaluation": f"评估 {entity_label} 的整体状况",
            "comparison": f"对比分析 {entity_label} 的差异和取舍",
            "technology_research": f"深入研究 {entity_label} 的技术原理和架构",
            "market_research": f"研究 {entity_label} 所在方向的市场机会",
            "information_lookup": f"了解 {entity_label} 是什么",
            "decision_support": f"为 {entity_label} 的选型提供决策支持",
        }

        if set(intent.focus or []) & {"community", "sentiment"}:
            user_goal = f"了解 {entity_label} 近期的社区评价和主要争议"
        else:
            user_goal = user_goals.get(intent.objective, user_goals["information_lookup"])

        research_context = ResearchContext(
            objective=intent.objective,
            user_goal=user_goal,
            entities=entity_names,
            focus=intent.focus,
            time_range=intent.time_range,
            depth=intent.depth,
        )
        research_context.execution_plan = self._build_execution_plan(intent, research_context)
        if research_context.execution_plan.mode == "quick":
            research_context.depth = "quick"
        return research_context

    @staticmethod
    def _build_execution_plan(
        intent: ResearchIntent,
        research_context: ResearchContext,
    ) -> ExecutionPlan:
        """根据 objective/focus/depth 生成通用执行控制计划。"""
        focus = set(research_context.focus or intent.focus or [])
        objective = research_context.objective or intent.objective
        time_range = research_context.time_range or intent.time_range
        depth = research_context.depth or intent.depth

        # 社区口碑/情绪类问题通常是快速判断，不需要完整研究报告。
        if focus & {"community", "sentiment"}:
            mode = "quick" if time_range in {"recent", "latest", "any"} else depth
            return ResearchContextBuilder._execution_plan(
                mode=mode if mode in {"quick", "standard", "deep"} else "quick",
                source_scope=["community", "web"],
                required_sources=["community", "web"],
                avoid_sources=["github"],
                max_tool_calls=6 if mode == "quick" else 8,
                max_discovery_per_source=1,
                max_reader_per_source=2,
                stop_when="required_sources_satisfied",
            )

        if objective == "comparison":
            return ResearchContextBuilder._execution_plan(
                mode="standard" if depth == "quick" else depth,
                source_scope=["github", "community", "web"],
                required_sources=["github", "community"],
                avoid_sources=[],
                max_tool_calls=8 if depth != "deep" else 12,
                max_discovery_per_source=1,
                max_reader_per_source=2,
                stop_when="required_sources_satisfied",
            )

        if focus & {"technology", "benchmark"} or objective in {"technology_research", "information_lookup"}:
            return ResearchContextBuilder._execution_plan(
                mode=depth,
                source_scope=["github", "web"],
                required_sources=["github"] if objective != "information_lookup" else ["web"],
                avoid_sources=[],
                max_tool_calls=4 if depth == "quick" else 8,
                max_discovery_per_source=1,
                max_reader_per_source=2,
                stop_when="required_sources_satisfied",
            )

        if objective in {"trend_analysis", "market_research"}:
            return ResearchContextBuilder._execution_plan(
                mode=depth,
                source_scope=["community", "web", "github"],
                required_sources=["community", "web"],
                avoid_sources=[],
                max_tool_calls=8 if depth != "deep" else 12,
                max_discovery_per_source=1,
                max_reader_per_source=2,
                stop_when="required_sources_satisfied",
            )

        return ResearchContextBuilder._execution_plan(
            mode=depth,
            source_scope=["web", "github"],
            required_sources=["web"],
            avoid_sources=[],
            max_tool_calls=4 if depth == "quick" else 6,
            max_discovery_per_source=1,
            max_reader_per_source=1,
            stop_when="required_sources_satisfied",
        )

    @staticmethod
    def _execution_plan(
        *,
        mode: str,
        source_scope: list[str],
        required_sources: list[str],
        avoid_sources: list[str],
        max_tool_calls: int,
        max_discovery_per_source: int,
        max_reader_per_source: int,
        stop_when: str,
    ) -> ExecutionPlan:
        """根据来源边界生成工具白/黑名单，避免 Agent 调用范围外工具。"""
        allowed_tools = _tools_for_sources(source_scope)
        blocked_tools = _tools_for_sources(avoid_sources)
        return ExecutionPlan(
            mode=mode,  # type: ignore[arg-type]
            source_scope=source_scope,
            required_sources=required_sources,
            avoid_sources=avoid_sources,
            allowed_tools=allowed_tools,
            blocked_tools=blocked_tools,
            max_tool_calls=max_tool_calls,
            max_discovery_per_source=max_discovery_per_source,
            max_reader_per_source=max_reader_per_source,
            stop_when=stop_when,
        )


def _tools_for_sources(sources: list[str]) -> list[str]:
    tools: list[str] = []
    for source in sources:
        tools.extend(TOOLS_BY_SOURCE.get(source, []))
    return list(dict.fromkeys(tools))
