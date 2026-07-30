"""Layer 1 — Intent Accuracy evaluator.

检查 ResearchIntent 的 objective / focus / depth 是否与预期匹配。
注意: time_range 不在 ResearchIntent schema 中（由正则从 raw_query 提取），不参与评估。

输出: intent_accuracy (0-100)
"""

from __future__ import annotations

from typing import Any


def evaluate_intent(
    case: dict[str, Any],
    predicted_intent: dict[str, Any] | None,
) -> dict[str, Any]:
    """评估意图理解准确性。

    Args:
        case: 评测用例（含 expected_intent）
        predicted_intent: Agent 实际输出的 intent dict

    Returns:
        评估结果 dict
    """
    expected = case.get("expected_intent") or {}
    if predicted_intent is None:
        predicted_intent = {}

    checks: dict[str, dict[str, Any]] = {}

    # 1. objective 匹配（最重要，权重 50%）
    exp_obj = expected.get("objective", "")
    pred_obj = predicted_intent.get("objective", "")
    checks["objective"] = {
        "expected": exp_obj,
        "predicted": pred_obj,
        "match": exp_obj == pred_obj,
        "weight": 0.50,
    }

    # 2. focus 匹配（权重 35%）— 集合交集 / 集合并集
    exp_focus = set(expected.get("focus") or [])
    pred_focus = set(predicted_intent.get("focus") or [])
    if exp_focus:
        focus_overlap = len(exp_focus & pred_focus)
        focus_union = len(exp_focus | pred_focus)
        focus_score = focus_overlap / focus_union if focus_union else 1.0
    else:
        focus_score = 1.0
    checks["focus"] = {
        "expected": sorted(exp_focus),
        "predicted": sorted(pred_focus),
        "score": round(focus_score, 3),
        "weight": 0.35,
    }

    # 3. depth 匹配（权重 15%）
    exp_depth = expected.get("depth", "standard")
    pred_depth = predicted_intent.get("depth", "standard")
    if not exp_depth or exp_depth == "standard":
        depth_match = True  # 默认值不惩罚
    else:
        depth_match = exp_depth == pred_depth
    checks["depth"] = {
        "expected": exp_depth,
        "predicted": pred_depth,
        "match": depth_match,
        "weight": 0.15,
    }

    # 计算加权总分
    total_score = 0.0
    for key, check in checks.items():
        weight = check["weight"]
        if key == "focus":
            total_score += weight * check["score"] * 100.0
        else:
            total_score += weight * (100.0 if check["match"] else 0.0)

    return {
        "layer": "intent_accuracy",
        "implemented": True,
        "score": round(total_score),
        "details": {
            "checks": checks,
            "objective_match": checks["objective"]["match"],
            "focus_score": checks["focus"]["score"],
            "depth_match": checks["depth"]["match"],
        },
    }
