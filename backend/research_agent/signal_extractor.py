# analyzer.py — Research Signal Analyzer
#
# 职责: 从多源 IntelligenceEvidence 中提取结构化信号
# 输入: list[IntelligenceEvidence] + ExecutionPlan
#       ExecutionPlan { objective, user_goal, entities, focus, time_range, depth, source_scope, ... }
# 输出: ExtractedSignals { technology, community, ecosystem, risks }
#
# 与旧 SignalExtractor 的区别:
#   - Analyzer 可以根据 ExecutionPlan 选择分析维度，但不参与 Tool Selection
#   - 支持跨 step 的 evidence 综合分析
#   - 引入 cross-source correlation（跨源关联分析）

from __future__ import annotations

import json
from concurrent.futures import ThreadPoolExecutor, as_completed

from llms.deepseek import deepseek_structured_model
from evidence.models import IntelligenceEvidence
from research_agent.schemas.research import (
    ExecutionPlan,
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
        self.tech_llm = deepseek_structured_model.with_structured_output(TechnologySignal)
        self.community_llm = deepseek_structured_model.with_structured_output(CommunitySignal)
        self.ecosystem_llm = deepseek_structured_model.with_structured_output(EcosystemSignal_)
        self.risk_llm = deepseek_structured_model.with_structured_output(RiskSignal)

    def analyze(
        self,
        evidences: list[IntelligenceEvidence],
        plan: ExecutionPlan | None = None,
    ) -> ExtractedSignals:
        """从多份 evidence 中提取所有维度的信号。

        Args:
            evidences: 各 step 收集到的 evidence 列表
            plan: 执行计划（用于确定需要哪些维度的信号）

        Returns:
            ExtractedSignals: 各维度信号容器
        """
        # Evidence Guard: 没有证据时不生成信号
        if not evidences:
            return ExtractedSignals()

        # 合并所有 evidence 为统一 JSON
        merged_json = self._merge_evidences(evidences)
        context_text = self._context_text(plan)

        # 确定需要哪些维度
        needed_dimensions = self._needed_dimensions(plan)

        signals = ExtractedSignals()
        extractors = {
            "technology": self._extract_tech,
            "community": self._extract_community,
            "ecosystem": self._extract_ecosystem,
            "risk": self._extract_risks,
        }

        with ThreadPoolExecutor(max_workers=min(len(needed_dimensions), 4)) as executor:
            future_map = {
                executor.submit(extractors[dimension], merged_json, context_text): dimension
                for dimension in needed_dimensions
                if dimension in extractors
            }
            for future in as_completed(future_map):
                dimension = future_map[future]
                value = future.result()
                if dimension == "technology":
                    signals.technology = value
                elif dimension == "community":
                    signals.community = value
                elif dimension == "ecosystem":
                    signals.ecosystem = value
                elif dimension == "risk":
                    signals.risks = value

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
    def _context_text(plan: ExecutionPlan | None) -> str:
        if plan is None:
            return "无"
        if isinstance(plan, ExecutionPlan):
            return (
                f"研究目标: {plan.user_goal}\n"
                f"关注维度: {', '.join(plan.focus or []) or '未指定'}\n"
                f"时间范围: {plan.time_range}\n"
                f"深度: {plan.mode}\n"
                f"来源范围: {', '.join(plan.source_scope or []) or '未指定'}\n"

            )
        return "无"

    @staticmethod
    def _needed_dimensions(plan: ExecutionPlan | None) -> set[str]:
        """从 ExecutionPlan 推导需要哪些信号维度。"""
        if plan is None:
            return {"technology"}  # 默认至少提取技术维度

        if not isinstance(plan, ExecutionPlan):
            return {"technology"}

        # Context 驱动的分析：这里只决定 Analyzer 提取哪些维度，不参与 Tool Selection。
        # 如果用户明确只关心社区/情绪，就不要再额外提取技术维度，减少一次 LLM 调用。
        focus = set(plan.focus or [])
        if focus:
            dimensions = set()
            if focus & {"technology", "benchmark"}:
                dimensions.add("technology")
            if focus & {"community", "developer", "sentiment", "adoption", "recent_updates", "trend"}:
                dimensions.add("community")
            if focus & {"ecosystem", "market", "opportunity"}:
                dimensions.add("ecosystem")
            if focus & {"risk"}:
                dimensions.add("risk")
            if dimensions:
                return dimensions

        # 没有明确 focus 时，按 objective 推导默认维度。
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
        if plan.mode in ("standard", "deep"):
            dimensions.add("risk")

        return dimensions
