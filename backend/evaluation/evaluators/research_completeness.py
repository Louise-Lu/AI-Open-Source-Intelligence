"""Research Completeness Evaluator (LLM Judge).

使用 LLM 评估研究完整性。

输入: query + expected_quality_expectations + final_answer + evidence
输出: score 1-5

评价维度:
- 是否回答用户真实问题
- 是否覆盖关键维度
- 是否避免无依据推断
"""

from __future__ import annotations

import json
from typing import Any

from pydantic import BaseModel, Field

from llms.deepseek import deepseek_structured_model


COMPLETENESS_EVAL_PROMPT = """你是一个研究质量评审员。

请评估以下研究回答的完整性和质量。

## 用户问题
{query}

## 期望覆盖的内容
{must_answer}

## Agent 最终回答
{answer}

## 收集到的证据摘要
{evidence_summary}

请从以下维度打分（1-5 分）：

1. question_addressed: 是否回答了用户的真实问题？
   - 5: 完全回答了用户问题的核心
   - 4: 基本回答了主要问题，有小遗漏
   - 3: 部分回答了问题
   - 2: 回答偏离了用户问题
   - 1: 完全没有回答用户问题

2. dimension_coverage: 是否覆盖了关键维度？
   - 5: 覆盖了所有期望维度
   - 4: 覆盖了大部分维度
   - 3: 覆盖了部分维度
   - 2: 覆盖很少
   - 1: 完全没有覆盖

3. evidence_grounding: 是否避免了无依据推断？
   - 5: 所有结论都有证据支撑
   - 4: 大部分结论有证据支撑
   - 3: 部分结论有证据支撑
   - 2: 很少结论有证据支撑
   - 1: 结论完全无证据

4. overall_quality: 整体研究质量
   - 5: 高质量研究，可以直接使用
   - 4: 较好，需要少量补充
   - 3: 一般，需要较多补充
   - 2: 较差，大部分需要重做
   - 1: 完全不可用

要求：
- 只输出结构化结果，不要额外解释
- feedback 用中文，简要说明主要优缺点
"""


class CompletenessJudgement(BaseModel):
    question_addressed: int = Field(ge=1, le=5, description="是否回答了用户真实问题")
    dimension_coverage: int = Field(ge=1, le=5, description="是否覆盖关键维度")
    evidence_grounding: int = Field(ge=1, le=5, description="是否避免无依据推断")
    overall_quality: int = Field(ge=1, le=5, description="整体研究质量")
    feedback: str = Field(default="", description="中文简要评语")


def _summarize_evidence(evidence: dict[str, Any]) -> str:
    """将 evidence dict 压缩为摘要文本。"""
    if not evidence:
        return "（无证据）"

    parts: list[str] = []

    repo = evidence.get("repository")
    if isinstance(repo, dict):
        name = repo.get("full_name") or repo.get("name") or "unknown"
        stars = repo.get("stars", "?")
        parts.append(f"GitHub: {name}, stars={stars}")

    readme = evidence.get("readme")
    if readme:
        preview = readme[:200] if isinstance(readme, str) else str(readme)[:200]
        parts.append(f"README: {preview}...")

    releases = evidence.get("releases") or []
    if releases:
        parts.append(f"Releases: {len(releases)} 条")

    issues = evidence.get("issues") or []
    if issues:
        parts.append(f"Issues: {len(issues)} 条")

    community = evidence.get("community_posts") or []
    if community:
        parts.append(f"Community posts: {len(community)} 条")

    web = evidence.get("web_pages") or []
    if web:
        parts.append(f"Web pages: {len(web)} 条")

    return "\n".join(parts) if parts else "（无证据）"


def evaluate_research_completeness(
    case: dict[str, Any],
    answer: str,
    evidence: dict[str, Any],
) -> dict[str, Any]:
    """使用 LLM 评估研究完整性。

    Args:
        case: 评测用例
        answer: Agent 最终回答
        evidence: 从 trace 提取的证据

    Returns:
        评估结果 dict
    """
    query = case.get("query") or ""
    quality_exp = case.get("quality_expectations") or {}
    must_answer = quality_exp.get("must_answer") or []
    answer = answer or ""

    if not answer.strip():
        return {
            "layer": "research_completeness",
            "implemented": True,
            "score": 1,
            "details": {
                "question_addressed": 1,
                "dimension_coverage": 1,
                "evidence_grounding": 1,
                "overall_quality": 1,
                "feedback": "回答为空。",
            },
        }

    evidence_summary = _summarize_evidence(evidence or {})

    prompt = COMPLETENESS_EVAL_PROMPT.format(
        query=query,
        must_answer=json.dumps(must_answer, ensure_ascii=False, indent=2),
        answer=answer[:3000],  # 截断过长的回答
        evidence_summary=evidence_summary,
    )

    try:
        llm = deepseek_structured_model.with_structured_output(CompletenessJudgement)
        judgement = llm.invoke(prompt)
    except Exception as exc:
        return {
            "layer": "research_completeness",
            "implemented": True,
            "score": None,
            "details": {
                "question_addressed": None,
                "dimension_coverage": None,
                "evidence_grounding": None,
                "overall_quality": None,
                "feedback": f"LLM 评测失败：{type(exc).__name__}: {exc}",
            },
        }

    # 加权总分 (1-5)
    weighted = (
        judgement.question_addressed * 0.35
        + judgement.dimension_coverage * 0.25
        + judgement.evidence_grounding * 0.25
        + judgement.overall_quality * 0.15
    )

    return {
        "layer": "research_completeness",
        "implemented": True,
        "score": round(weighted, 1),
        "details": {
            "question_addressed": judgement.question_addressed,
            "dimension_coverage": judgement.dimension_coverage,
            "evidence_grounding": judgement.evidence_grounding,
            "overall_quality": judgement.overall_quality,
            "feedback": (judgement.feedback or "").strip(),
        },
    }
