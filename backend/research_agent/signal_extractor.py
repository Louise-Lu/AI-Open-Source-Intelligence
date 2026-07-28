# analyzer.py — Research Signal Analyzer
#
# 职责: 从多源 IntelligenceEvidence 中提取结构化信号
# 输入: list[IntelligenceEvidence] + ResearchGoal
#       ResearchGoal { objective, user_goal, entities, context, depth,
#                      success_criteria, constraints }
# 输出: ExtractedSignals { technology, community, ecosystem, risks }
#
# 与旧 SignalExtractor 的区别:
#   - 不再按 depth 决定提取哪些维度（由 Planner 的 data_sources 决定）
#   - 支持跨 step 的 evidence 综合分析
#   - 引入 cross-source correlation（跨源关联分析）

from __future__ import annotations

import json
import logging

from llms.deepseek import deepseek_model
from evidence.models import IntelligenceEvidence
from research_agent.schemas.research import (
    ResearchGoal,
    ExtractedSignals,
    TechnologySignal,
    CommunitySignal,
    EcosystemSignal_,
    RiskSignal,
)
from research_agent.prompts.extraction import (
    TECH_EXTRACTION_PROMPT,
    COMMUNITY_EXTRACTION_PROMPT,
    ECOSYSTEM_EXTRACTION_PROMPT,
    RISK_EXTRACTION_PROMPT,
)

logger = logging.getLogger(__name__)


class ResearchAgentAnalyzer:
    """从多源证据中提取结构化信号。
    """

    def __init__(self):
        self.tech_llm = deepseek_model.with_structured_output(TechnologySignal)
        self.community_llm = deepseek_model.with_structured_output(CommunitySignal)
        self.ecosystem_llm = deepseek_model.with_structured_output(EcosystemSignal_)
        self.risk_llm = deepseek_model.with_structured_output(RiskSignal)

    def analyze(
        self,
        evidences: list[IntelligenceEvidence],
        goal: ResearchGoal | None = None,
    ) -> ExtractedSignals:
        """从多份 evidence 中提取所有维度的信号。

        Args:
            evidences: 各 step 收集到的 evidence 列表
            goal: 研究计划（用于确定需要哪些维度的信号）

        Returns:
            ExtractedSignals: 各维度信号容器
        """
        # Evidence Guard: 没有证据时不生成信号
        if not evidences:
            return ExtractedSignals()

        # 合并所有 evidence 为统一 JSON
        merged_json = self._merge_evidences(evidences)
        plan_context = self._plan_context(goal)

        # 确定需要哪些维度
        needed_dimensions = self._needed_dimensions(goal)

        signals = ExtractedSignals()

        if "technology" in needed_dimensions:
            signals.technology = self._extract_tech(merged_json, plan_context)

        if "community" in needed_dimensions:
            signals.community = self._extract_community(merged_json, plan_context)

        if "ecosystem" in needed_dimensions:
            signals.ecosystem = self._extract_ecosystem(merged_json, plan_context)

        if "risk" in needed_dimensions:
            signals.risks = self._extract_risks(merged_json, plan_context)

        return signals

    # ── Dimension Extraction ───────────────────────────────────

    def _extract_tech(self, evidence_json: str, plan_context: str) -> TechnologySignal | None:
        try:
            prompt = f"{TECH_EXTRACTION_PROMPT}\n\n## 研究计划\n{plan_context}\n\n## 证据数据\n{evidence_json}"
            return self.tech_llm.invoke(prompt)
        except Exception as exc:
            logger.warning("Technology signal extraction failed: %s", exc)
            return None

    def _extract_community(self, evidence_json: str, plan_context: str) -> CommunitySignal | None:
        try:
            prompt = f"{COMMUNITY_EXTRACTION_PROMPT}\n\n## 研究计划\n{plan_context}\n\n## 证据数据\n{evidence_json}"
            return self.community_llm.invoke(prompt)
        except Exception as exc:
            logger.warning("Community signal extraction failed: %s", exc)
            return None

    def _extract_ecosystem(self, evidence_json: str, plan_context: str) -> EcosystemSignal_ | None:
        try:
            prompt = f"{ECOSYSTEM_EXTRACTION_PROMPT}\n\n## 研究计划\n{plan_context}\n\n## 证据数据\n{evidence_json}"
            return self.ecosystem_llm.invoke(prompt)
        except Exception as exc:
            logger.warning("Ecosystem signal extraction failed: %s", exc)
            return None

    def _extract_risks(self, evidence_json: str, plan_context: str) -> RiskSignal | None:
        try:
            prompt = f"{RISK_EXTRACTION_PROMPT}\n\n## 研究计划\n{plan_context}\n\n## 证据数据\n{evidence_json}"
            return self.risk_llm.invoke(prompt)
        except Exception as exc:
            logger.warning("Risk signal extraction failed: %s", exc)
            return None

    # ── Helpers ────────────────────────────────────────────────

    @staticmethod
    def _merge_evidences(evidences: list[IntelligenceEvidence]) -> str:
        """合并多份 evidence 为单一 JSON 字符串。"""
        merged = []
        for i, ev in enumerate(evidences):
            if ev:
                merged.append({
                    "step_index": i,
                    "data": json.loads(ev.model_dump_json()) if hasattr(ev, 'model_dump_json') else ev,
                })
        return json.dumps(merged, ensure_ascii=False, indent=2) if merged else "{}"

    @staticmethod
    def _plan_context(plan: ResearchGoal | None) -> str:
        if plan is None:
            return "无"
        if isinstance(plan, ResearchGoal):
            criteria = "\n".join(f"- {c}" for c in plan.success_criteria)
            constraints = "\n".join(f"- {c}" for c in plan.constraints)
            return (
                f"研究目标: {plan.user_goal}\n"
                f"背景: {plan.context or '无'}\n"
                f"完成标准:\n{criteria or '- 无'}\n"
                f"约束:\n{constraints or '- 无'}\n"
                f"深度: {plan.depth}"
            )
        steps_summary = [
            f"- 步骤{i}: {s.question} [数据源: {', '.join(s.data_sources)}, 工具: {', '.join(s.tools)}]"
            for i, s in enumerate(plan.steps)
        ]
        return "\n".join(steps_summary) if steps_summary else "无"

    @staticmethod
    def _needed_dimensions(plan: ResearchGoal | None) -> set[str]:
        """从 ResearchGoal 推导需要哪些信号维度。"""
        if plan is None:
            return {"technology"}  # 默认至少提取技术维度

        if isinstance(plan, ResearchGoal):
            # Goal 驱动模式：根据 objective 和 entities 推导维度
            dimensions = set()
            obj = plan.objective

            # 所有研究类型默认提取技术维度
            dimensions.add("technology")

            # 涉及社区/评估/趋势时提取社区维度
            if obj in ("evaluation", "comparison", "trend_analysis", "market_research"):
                dimensions.add("community")

            # 涉及对比/生态/市场时提取生态维度
            if obj in ("comparison", "trend_analysis", "market_research", "decision_support"):
                dimensions.add("ecosystem")

            # standard/deep 深度添加风险维度
            if plan.depth in ("standard", "deep"):
                dimensions.add("risk")

        return dimensions 
