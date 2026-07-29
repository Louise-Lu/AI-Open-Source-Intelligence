# analyzer.py — Research Signal Analyzer
#
# 职责: 从多源 IntelligenceEvidence 中提取结构化信号
# 输入: list[IntelligenceEvidence] + ResearchContext
#       ResearchContext { objective, user_goal, entities, focus, time_range, depth,
#                       research_brief, success_criteria, constraints }
# 输出: ExtractedSignals { technology, community, ecosystem, risks }
#
# 与旧 SignalExtractor 的区别:
#   - Analyzer 可以根据 ResearchContext 选择分析维度，但不参与 Tool Selection
#   - 支持跨 step 的 evidence 综合分析
#   - 引入 cross-source correlation（跨源关联分析）

from __future__ import annotations

import json

from llms.deepseek import deepseek_model
from evidence.models import IntelligenceEvidence
from research_agent.schemas.research import (
    ResearchContext,
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
        research_context: ResearchContext | None = None,
    ) -> ExtractedSignals:
        """从多份 evidence 中提取所有维度的信号。

        Args:
            evidences: 各 step 收集到的 evidence 列表
            research_context: 上下文（用于确定需要哪些维度的信号）

        Returns:
            ExtractedSignals: 各维度信号容器
        """
        # Evidence Guard: 没有证据时不生成信号
        if not evidences:
            return ExtractedSignals()

        # 合并所有 evidence 为统一 JSON
        merged_json = self._merge_evidences(evidences)
        context_text = self._context_text(research_context)

        # 确定需要哪些维度
        needed_dimensions = self._needed_dimensions(research_context)

        signals = ExtractedSignals()

        if "technology" in needed_dimensions:
            signals.technology = self._extract_tech(merged_json, context_text)

        if "community" in needed_dimensions:
            signals.community = self._extract_community(merged_json, context_text)

        if "ecosystem" in needed_dimensions:
            signals.ecosystem = self._extract_ecosystem(merged_json, context_text)

        if "risk" in needed_dimensions:
            signals.risks = self._extract_risks(merged_json, context_text)

        return signals

    # ── Dimension Extraction ───────────────────────────────────

    def _extract_tech(self, evidence_json: str, context_text: str) -> TechnologySignal | None:
        try:
            prompt = f"{TECH_EXTRACTION_PROMPT}\n\n## 研究上下文\n{context_text}\n\n## 证据数据\n{evidence_json}"
            return self.tech_llm.invoke(prompt)
        except Exception as exc:
            print("Technology signal extraction failed: %s", exc)
            return None

    def _extract_community(self, evidence_json: str, context_text: str) -> CommunitySignal | None:
        try:
            prompt = f"{COMMUNITY_EXTRACTION_PROMPT}\n\n## 研究上下文\n{context_text}\n\n## 证据数据\n{evidence_json}"
            return self.community_llm.invoke(prompt)
        except Exception as exc :
            print("Community signal extraction failed: %s", exc)
            return None

    def _extract_ecosystem(self, evidence_json: str, context_text: str) -> EcosystemSignal_ | None:
        try:
            prompt = f"{ECOSYSTEM_EXTRACTION_PROMPT}\n\n## 研究上下文\n{context_text}\n\n## 证据数据\n{evidence_json}"
            return self.ecosystem_llm.invoke(prompt)
        except Exception as exc:
            print("Ecosystem signal extraction failed: %s", exc)
            return None

    def _extract_risks(self, evidence_json: str, context_text: str) -> RiskSignal | None:
        try:
            prompt = f"{RISK_EXTRACTION_PROMPT}\n\n## 研究上下文\n{context_text}\n\n## 证据数据\n{evidence_json}"
            return self.risk_llm.invoke(prompt)
        except Exception as exc:
            print("Risk signal extraction failed: %s", exc)
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
    def _context_text(research_context: ResearchContext | None) -> str:
        if research_context is None:
            return "无"
        if isinstance(research_context, ResearchContext):
            criteria = "\n".join(f"- {c}" for c in research_context.success_criteria)
            constraints = "\n".join(f"- {c}" for c in research_context.constraints)
            return (
                f"研究目标: {research_context.user_goal}\n"
                f"研究说明: {research_context.research_brief or '无'}\n"
                f"完成标准:\n{criteria or '- 无'}\n"
                f"约束:\n{constraints or '- 无'}\n"
                f"深度: {research_context.depth}"
            )
        return "无"

    @staticmethod
    def _needed_dimensions(research_context: ResearchContext | None) -> set[str]:
        """从 ResearchContext 推导需要哪些信号维度。"""
        if research_context is None:
            return {"technology"}  # 默认至少提取技术维度

        if not isinstance(research_context, ResearchContext):
            return {"technology"}

        # Context 驱动的分析：这里只决定 Analyzer 提取哪些维度，不参与 Tool Selection
        dimensions = set()
        obj = research_context.objective

        # 所有研究类型默认提取技术维度
        dimensions.add("technology")

        # 涉及社区/评估/趋势时提取社区维度
        if obj in ("evaluation", "comparison", "trend_analysis", "market_research"):
            dimensions.add("community")

        # 涉及对比/生态/市场时提取生态维度
        if obj in ("comparison", "trend_analysis", "market_research", "decision_support"):
            dimensions.add("ecosystem")

        # standard/deep 深度添加风险维度
        if research_context.depth in ("standard", "deep"):
            dimensions.add("risk")

        return dimensions
