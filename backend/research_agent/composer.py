# composer.py — Research Brief Composer
#
# 职责: 将 Evidence + Signals 组合为最终 Research Brief
# 输入: user query + list[IntelligenceEvidence] + ExtractedSignals
# 输出: ResearchBrief { summary, key_findings, analysis, sources, recommendations }
#
# 与旧 AnswerComposer 的核心区别:
#   - 不输出固定 report 模板（profile/roadmap/comparison/analysis/...）
#   - 输出 ResearchBrief（结构化 JSON），而非纯文本 answer
#   - 包含 sources 追溯
#   - 带有 recommendations（行动建议）

from __future__ import annotations

import json
import logging

from llms.deepseek import deepseek_model
from evidence.models import IntelligenceEvidence
from research_agent.schemas.research import ResearchBrief, ExtractedSignals

logger = logging.getLogger(__name__)

COMPOSER_SYSTEM_PROMPT = """你是 AI Intelligence Research Agent 的研究简报撰写器。

## 核心职责
根据收集到的多源证据和提取的结构化信号，撰写一份结构化的 Research Brief。

## 输出格式
必须输出合法的 JSON，不超过以下字段：

{
  "summary": "一句话总结核心发现",
  "key_findings": ["发现1", "发现2", "发现3"],
  "analysis": "详细分析（自然语言，2-4段）",
  "sources": ["来源1: 说明", "来源2: 说明"],
  "recommendations": ["建议1", "建议2"]
}

## 撰写规则
1. summary: 一句话概括最重要的结论，让读者立刻知道答案
2. key_findings: 3-5 条具体发现，每条都是可独立理解的陈述
3. analysis: 详细分析，引用证据中的具体数据，说明推理过程
4. sources: 列出实际使用到的信息来源，说明每个来源提供了什么
5. recommendations: 基于分析的行动建议（如果问题不需要建议可以为空）

## 风格要求
- 输出中文
- 直接、具体、有数据支撑
- 不编造数据
- 不确定的地方明确说「不确定」
- 优先引用结构化信号中的量化评分

---

现在，请根据以下信息撰写 Research Brief，只输出 JSON。
"""


class ResearchBriefComposer:
    """将证据和信号组合为结构化研究简报。

    与旧 AnswerComposer 的区别：
    - 输出 ResearchBrief（结构化），而非 ComposedAnswer（仅 answer 字符串）
    - 不绑报告模板
    - 包含 key_findings、sources、recommendations
    """

    def __init__(self):
        self.llm = deepseek_model.with_structured_output(ResearchBrief)

    def compose(
        self,
        query: str,
        evidences: list[IntelligenceEvidence],
        signals: ExtractedSignals | None = None,
    ) -> ResearchBrief:
        """撰写研究简报。

        Args:
            query: 用户原始问题
            evidences: 收集到的所有 evidence
            signals: 提取的结构化信号

        Returns:
            ResearchBrief: 结构化研究简报
        """
        # Brief Guard: 没有证据时不生成简报
        if not evidences:
            return ResearchBrief(
                summary="没有足够证据生成研究简报。",
                key_findings=["未收集到任何证据，无法进行分析。"],
                analysis="",
                signals=None,
                sources=[],
                recommendations=["请检查目标仓库是否存在，或提供其他项目名称。"],
            )

        evidence_json = self._serialize_evidences(evidences)

        signals_json = ""
        if signals is not None:
            signals_data = signals.model_dump() if hasattr(signals, "model_dump") else signals
            signals_json = f"\n\n## 结构化分析信号\n{json.dumps(signals_data, ensure_ascii=False, indent=2)}"

        prompt = f"""{COMPOSER_SYSTEM_PROMPT}

## 用户问题
{query}

## 证据数据
{evidence_json}
{signals_json}
"""
        try:
            result = self.llm.invoke(prompt)
            if isinstance(result, ResearchBrief):
                return result
            if isinstance(result, dict):
                return ResearchBrief(**result)
            raise ValueError(f"Unexpected LLM response type: {type(result)}")
        except Exception as exc:
            logger.warning("ResearchBriefComposer LLM error: %s", exc)
            return self._fallback_brief(query, evidences, signals, str(exc))

    # ── Serialization ──────────────────────────────────────────

    @staticmethod
    def _serialize_evidences(evidences: list[IntelligenceEvidence]) -> str:
        serialized = []
        for i, ev in enumerate(evidences):
            if ev is None:
                continue
            try:
                if hasattr(ev, 'model_dump'):
                    data = ev.model_dump()
                elif hasattr(ev, 'dict'):
                    data = ev.dict()
                else:
                    data = str(ev)
                serialized.append({"step": i, "data": data})
            except Exception:
                serialized.append({"step": i, "data": str(ev)})
        return json.dumps(serialized, ensure_ascii=False, indent=2)

    @staticmethod
    def _fallback_brief(
        query: str,
        evidences: list[IntelligenceEvidence],
        signals: ExtractedSignals | None,
        reason: str,
    ) -> ResearchBrief:
        """LLM compose 失败时，用已有 evidence/signals 生成可用简报。"""
        key_findings: list[str] = []
        sources: list[str] = []
        recommendations: list[str] = []
        analysis_parts: list[str] = []

        for evidence in evidences:
            github = evidence.github if evidence else None
            repo = github.repository if github else None
            if repo:
                repo_name = repo.full_name or "该仓库"
                key_findings.append(
                    f"{repo_name} 是一个以 {repo.language or '未知语言'} 为主的 GitHub 项目，"
                    f"当前约有 {repo.stars} stars、{repo.forks} forks。"
                )
                if repo.description:
                    key_findings.append(f"项目描述：{repo.description}")
                sources.append(f"GitHub repository: {repo_name}")

            if github and github.readme:
                readme_preview = github.readme[:300].replace("\n", " ").strip()
                if readme_preview:
                    analysis_parts.append(f"README 摘要片段：{readme_preview}...")
                    sources.append("GitHub README")

        if signals:
            if signals.technology and signals.technology.summary:
                key_findings.append(signals.technology.summary)
            if signals.community and signals.community.summary:
                key_findings.append(signals.community.summary)
            if signals.ecosystem and signals.ecosystem.summary:
                key_findings.append(signals.ecosystem.summary)

        if not key_findings:
            key_findings.append("当前没有收集到足够证据，无法给出可靠结论。")
            recommendations.append("检查实体解析结果是否正确，或补充明确的 GitHub 仓库、官网、文档链接。")

        if reason:
            analysis_parts.append(f"结构化撰写模型未返回有效结果，已使用 fallback 简报。内部原因：{reason}")

        return ResearchBrief(
            summary=f"关于「{query[:50]}」的研究已基于现有证据生成 fallback 简报。",
            key_findings=key_findings[:6],
            analysis="\n\n".join(analysis_parts),
            signals=signals,
            sources=list(dict.fromkeys(sources)),
            recommendations=recommendations,
        )
