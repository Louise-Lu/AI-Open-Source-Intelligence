# execution_plan_builder.py — ExecutionPlan Builder
#
# 职责: 根据 ResearchIntent + ResolvedEntity 构建 ExecutionPlan
# 输入: ResearchIntent + list[ResolvedEntity]
# 输出: ExecutionPlan（统一上下文 + 执行控制）
#
# ExecutionPlanBuilder 只做确定性组装，用稳定规则生成执行计划。

from __future__ import annotations

from research_agent.intent import extract_platforms, extract_time_range
from research_agent.schemas.research import ExecutionPlan, ResearchIntent, StopConditions
from research_agent.schemas.entity import ResolvedEntity


class ExecutionPlanBuilder:
    """根据 ResearchIntent + ResolvedEntity 构建 ExecutionPlan。
    不调用 LLM, 只做确定性组装。
    """

    def build(
        self,
        intent: ResearchIntent,
        entities: list[ResolvedEntity],
    ) -> ExecutionPlan | None:
        """构建执行计划。entities 为空时返回 None。"""
        if not entities:
            return None

        entity_names = [e.name for e in entities] or intent.entities
        entity_label = "、".join(entity_names or ["目标对象"])

        # 正则提取（不经过 LLM）
        time_range = extract_time_range(intent.raw_query)
        platform_hint = extract_platforms(intent.raw_query)

        # 生成 user_goal
        user_goal = self._build_user_goal(intent, entity_label)

        # 根据 objective/focus/depth 生成执行参数
        params = self._build_params(intent, time_range, entities)

        # 用 entity_scope 调整 source_scope：
        # 1) 去掉实体实际不存在的平台（community 不受影响）
        # 2) 补回实体有但 _build_params 默认没给的平台（如 huggingface）
        entity_scopes = set()
        for e in entities:
            entity_scopes.update(e.entity_scope)
        if entity_scopes:
            current_scope = params.get("source_scope", [])
            # 过滤：去掉实体不存在的源（community 例外）
            filtered = [s for s in current_scope if s == "community" or s in entity_scopes]
            # 补回：实体有 huggingface 但默认 scope 没给的情况
            extra_sources = {"huggingface"}
            for s in extra_sources:
                if s in entity_scopes and s not in filtered:
                    filtered.append(s)
            params["source_scope"] = filtered

        # 社区平台推断：仅当 source_scope 包含 community 时才设置
        if "community" in params.get("source_scope", []):
            community_platforms = platform_hint or self._infer_community_platforms(entities)
            params["community_platforms"] = community_platforms

        return ExecutionPlan(
            # 来自 Intent
            objective=intent.objective,
            entities=entity_names,
            focus=intent.focus or [],
            time_range=time_range,
            # ContextBuilder 生成
            user_goal=user_goal,
            **params,
        )

    @staticmethod
    def _build_user_goal(intent: ResearchIntent, entity_label: str) -> str:
        """根据 intent 生成一句话任务描述。"""
        focus = set(intent.focus or [])
        objective = intent.objective

        # evaluation / trend_analysis 根据 focus 维度组合生成不同粒度的 goal
        if objective in {"evaluation", "trend_analysis"}:
            has_community = bool(focus & {"community", "sentiment"})
            has_tech = bool(focus & {"technology", "benchmark"})
            if has_community and has_tech:
                return f"全面了解 {entity_label} 的整体表现，包括社区评价和技术能力"
            if has_community:
                return f"了解 {entity_label} 近期的社区评价和主要争议"

        goals = {
            "trend_analysis": f"分析 {entity_label} 最近的发展趋势",
            "evaluation": f"评估 {entity_label} 的整体状况",
            "comparison": f"对比分析 {entity_label} 的差异和取舍",
            "technology_research": f"深入研究 {entity_label} 的技术原理和架构",
            "market_research": f"研究 {entity_label} 所在方向的市场机会",
            "information_lookup": f"了解 {entity_label} 的基本信息和数据",
            "decision_support": f"为 {entity_label} 的选型提供决策支持",
        }
        return goals.get(intent.objective, goals["information_lookup"])

    @staticmethod
    def _build_params(
        intent: ResearchIntent,
        time_range: str,
        entities: list[ResolvedEntity],
    ) -> dict:
        """根据 objective/focus/depth 生成执行参数。

        depth 是 Intent 层概念（用户想要多深），mode 是执行层概念（实际跑多深）。
        mode 以 intent.depth 为基准，可根据 time_range 等因素微调。

        每个分支返回 dict，包含 mode, source_scope, avoid_sources,
        required_evidence, max_tool_calls, stop_conditions 等。
        """
        focus = set(intent.focus or [])
        objective = intent.objective
        base_mode = intent.depth  # Intent 层的 depth 期望

        # ── information_lookup：优先 github + web，不关注社区口碑 ──
        if objective == "information_lookup":
            return {
                "mode": base_mode,
                "source_scope": ["github", "web"],
                "avoid_sources": [],
                "required_evidence": ["github"],
                "max_tool_calls": 6 if base_mode == "quick" else 8,
                "max_discovery_per_source": 2,
                "max_empty_retry_per_source": 1,
                "max_reader_per_source": 2,
                "max_evidence_items": 6,
                "min_evidence_items": 2,
                "stop_conditions": StopConditions(min_sources=1, min_evidence_items=2),
            }

        # ── 社区口碑/情绪类：仅 evaluation 或 trend_analysis 且关注 community/sentiment ──
        if objective in {"evaluation", "trend_analysis"} and focus & {"community", "sentiment"}:
            # 社区时效性查询：recent/latest/any 时降为 quick，避免过度搜索
            mode = "quick" if time_range in {"recent", "latest", "any"} else base_mode
            return {
                "mode": mode if mode in {"quick", "standard", "deep"} else "quick",
                "source_scope": ["community", "web", "github"],
                "avoid_sources": [],
                "required_evidence": ["community"],
                "max_tool_calls": 6 if mode == "quick" else 8,
                "max_discovery_per_source": 2,
                "max_empty_retry_per_source": 1,
                "max_reader_per_source": 2,
                "max_evidence_items": 8,
                "min_evidence_items": 3,
                "stop_conditions": StopConditions(min_sources=1, min_evidence_items=3),
            }

        # ── comparison：需要 github 数据 + community 对比 ──
        if objective == "comparison":
            mode = "standard" if base_mode == "quick" else base_mode
            return {
                "mode": mode,
                "source_scope": ["github", "community", "web"],
                "avoid_sources": [],
                "required_evidence": ["github"],
                "max_tool_calls": 8 if mode != "deep" else 12,
                "max_discovery_per_source": 2,
                "max_empty_retry_per_source": 1,
                "max_reader_per_source": 2,
                "max_evidence_items": 12,
                "min_evidence_items": 4,
                "stop_conditions": StopConditions(min_sources=2, min_evidence_items=4),
            }

        # ── technology_research / information_lookup：github + web ──
        if focus & {"technology", "benchmark"} or objective in {"technology_research", "information_lookup"}:
            return {
                "mode": base_mode,
                "source_scope": ["github", "web"],
                "avoid_sources": [],
                "required_evidence": ["github"] if objective != "information_lookup" else ["web"],
                "max_tool_calls": 6 if base_mode == "quick" else 8,
                "max_discovery_per_source": 2,
                "max_empty_retry_per_source": 1,
                "max_reader_per_source": 2,
                "max_evidence_items": 8,
                "min_evidence_items": 2,
                "stop_conditions": StopConditions(min_sources=1, min_evidence_items=2),
            }

        # ── trend_analysis / market_research：community + web + github ──
        if objective in {"trend_analysis", "market_research"}:
            return {
                "mode": base_mode,
                "source_scope": ["community", "web", "github"],
                "avoid_sources": [],
                "required_evidence": ["community", "web"],
                "max_tool_calls": 8 if base_mode != "deep" else 12,
                "max_discovery_per_source": 2,
                "max_empty_retry_per_source": 1,
                "max_reader_per_source": 2,
                "max_evidence_items": 12,
                "min_evidence_items": 4,
                "stop_conditions": StopConditions(min_sources=2, min_evidence_items=4),
            }

        # ── evaluation：偏社区口碑，community + github + web ──
        if objective == "evaluation":
            return {
                "mode": base_mode,
                "source_scope": ["community", "github", "web"],
                "avoid_sources": [],
                "required_evidence": ["community", "github"],
                "max_tool_calls": 6 if base_mode == "quick" else 8,
                "max_discovery_per_source": 2,
                "max_empty_retry_per_source": 1,
                "max_reader_per_source": 2,
                "max_evidence_items": 10,
                "min_evidence_items": 4,
                "stop_conditions": StopConditions(min_sources=2, min_evidence_items=4),
            }

        # ── decision_support：需要充分 github 数据支撑决策 ──
        if objective == "decision_support":
            return {
                "mode": base_mode,
                "source_scope": ["github", "community", "web"],
                "avoid_sources": [],
                "required_evidence": ["github"],
                "max_tool_calls": 8 if base_mode != "deep" else 12,
                "max_discovery_per_source": 2,
                "max_empty_retry_per_source": 1,
                "max_reader_per_source": 2,
                "max_evidence_items": 12,
                "min_evidence_items": 4,
                "stop_conditions": StopConditions(min_sources=2, min_evidence_items=4),
            }

        # ── default fallback ──
        return {
            "mode": base_mode,
            "source_scope": ["github", "web"],
            "avoid_sources": [],
            "required_evidence": ["github"],
            "max_tool_calls": 6,
            "max_discovery_per_source": 2,
            "max_empty_retry_per_source": 1,
            "max_reader_per_source": 2,
            "max_evidence_items": 8,
            "min_evidence_items": 2,
            "stop_conditions": StopConditions(min_sources=1, min_evidence_items=2),
        }

    @staticmethod
    def _infer_community_platforms(entities: list[ResolvedEntity]) -> list[str]:
        """根据 entity_origin 推断默认社区平台。

        - 全部中国项目 → bilibili, reddit（B站中文 AI 讨论更丰富）
        - 全部海外项目 → reddit, twitter
        - 混合或未知 → reddit, twitter（默认覆盖更广）
        """
        origins = {e.entity_origin for e in entities}
        if origins == {"chinese"}:
            return ["bilibili", "reddit"]
        return ["reddit", "twitter"]
