"""Answer Quality Evaluator v2 — 回答质量评估 (LLM-as-Judge).

评估维度:
- relevance (相关性, 权重 40%)
- completeness (完整性, 权重 30%)
- clarity (清晰度, 权重 20%)
- conciseness (简洁性, 权重 10%)

输出: 0-100 加权分
"""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field

from llms.deepseek import deepseek_structured_model

WEIGHT_RELEVANCE = 0.40
WEIGHT_COMPLETENESS = 0.30
WEIGHT_CLARITY = 0.20
WEIGHT_CONCISENESS = 0.10

ANSWER_EVAL_PROMPT = """你是一个开源项目分析 Agent 的回答质量评审员。

该 Agent 可以从 GitHub、社区（Reddit/Twitter/B站等）、Web 等多来源收集证据。

请根据用户问题、预期意图与最终回答，从以下维度打分（0–100 整数）：

1. relevance（相关性，权重 40%）
   - 回答是否直接回应了用户问题？

2. completeness（完整性，权重 30%）
   - 按预期意图，回答是否包含关键信息？

3. clarity（清晰度，权重 20%）
   - 回答是否结构清晰、易于理解？

4. conciseness（简洁性，权重 10%）
   - 是否避免不必要的重复与废话？

要求：
- 只输出结构化结果，不要额外解释
- feedback 用中文，简要说明主要优缺点

用户问题：
{question}

预期意图：
{expected_intents}

最终回答：
{answer}
"""


class AnswerQualityJudgement(BaseModel):
    relevance: int = Field(ge=0, le=100, description="相关性 0-100")
    completeness: int = Field(ge=0, le=100, description="完整性 0-100")
    clarity: int = Field(ge=0, le=100, description="清晰度 0-100")
    conciseness: int = Field(ge=0, le=100, description="简洁性 0-100")
    feedback: str = Field(default="", description="中文简要评语")


def _clamp_score(value: int | float) -> int:
    return max(0, min(100, int(round(value))))


def _get_expected_intents(case: dict[str, Any]) -> list[str]:
    """从 case 中提取预期意图。"""
    # v2 格式: expected_intent.objective + expected_intent.focus
    expected_intent = case.get("expected_intent") or {}
    if isinstance(expected_intent, dict):
        parts = []
        objective = expected_intent.get("objective", "")
        if objective:
            parts.append(objective)
        focus = expected_intent.get("focus") or []
        parts.extend(focus)
        if parts:
            return parts

    # 兼容旧格式
    if "expected_intents" in case:
        return list(case.get("expected_intents") or [])
    legacy = case.get("intent")
    if isinstance(legacy, str) and legacy:
        return [legacy]
    if isinstance(legacy, list):
        return list(legacy)
    return []


def _empty_result(feedback: str) -> dict[str, Any]:
    return {
        "layer": "answer_quality",
        "implemented": True,
        "score": 0,
        "details": {
            "relevance": 0,
            "completeness": 0,
            "clarity": 0,
            "conciseness": 0,
            "feedback": feedback,
        },
    }


def evaluate_answer_quality(
    case: dict[str, Any],
    answer: str,
) -> dict[str, Any]:
    """评估最终回答质量 (v2 接口)。

    Args:
        case: 评测用例 (使用 query / expected_intent 字段)
        answer: Agent 的最终回答文本

    Returns:
        评估结果 dict, score 范围 0-100
    """
    answer = answer or ""
    if not answer.strip():
        return _empty_result("回答为空，无法评分。")

    question = case.get("query") or ""
    expected_intents = _get_expected_intents(case)
    prompt = ANSWER_EVAL_PROMPT.format(
        question=question,
        expected_intents=", ".join(expected_intents) or "（未标注）",
        answer=answer,
    )

    try:
        llm = deepseek_structured_model.with_structured_output(AnswerQualityJudgement)
        judgement = llm.invoke(prompt)
    except Exception as exc:  # noqa: BLE001
        return {
            "layer": "answer_quality",
            "implemented": True,
            "score": None,
            "details": {
                "relevance": None,
                "completeness": None,
                "clarity": None,
                "conciseness": None,
                "feedback": f"回答质量评测失败：{type(exc).__name__}: {exc}",
            },
        }

    relevance = _clamp_score(judgement.relevance)
    completeness = _clamp_score(judgement.completeness)
    clarity = _clamp_score(judgement.clarity)
    conciseness = _clamp_score(judgement.conciseness)

    score = round(
        relevance * WEIGHT_RELEVANCE
        + completeness * WEIGHT_COMPLETENESS
        + clarity * WEIGHT_CLARITY
        + conciseness * WEIGHT_CONCISENESS
    )

    return {
        "layer": "answer_quality",
        "implemented": True,
        "score": score,
        "details": {
            "relevance": relevance,
            "completeness": completeness,
            "clarity": clarity,
            "conciseness": conciseness,
            "feedback": (judgement.feedback or "").strip(),
        },
    }
